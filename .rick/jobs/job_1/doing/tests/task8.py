#!/usr/bin/env python3
import json
import sys
import os
import subprocess

def main():
    errors = []

    # Project root: .rick/jobs/job_1/doing/tests/task8.py -> project root (6 levels up)
    # tests/ -> doing/ -> job_1/ -> jobs/ -> .rick/ -> project_root/
    _f = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(_f)))
    )))

    print(f"[DEBUG] project_root = {project_root}", file=sys.stderr)

    # Test 1: check_env.py 存在且可运行
    check_env_path = os.path.join(project_root, "cut", "scripts", "check_env.py")
    if not os.path.exists(check_env_path):
        errors.append(f"check_env.py not found at {check_env_path}")
    else:
        try:
            result = subprocess.run(
                [sys.executable, check_env_path],
                capture_output=True, text=True, timeout=30
            )
            # check_env.py should exit 0 or 1 (not crash with exception)
            if result.returncode not in (0, 1):
                errors.append(
                    f"check_env.py exited with unexpected code {result.returncode}: {result.stderr[:200]}"
                )
        except subprocess.TimeoutExpired:
            errors.append("check_env.py timed out after 30s")
        except Exception as e:
            errors.append(f"Failed to run check_env.py: {str(e)}")

    # Test 2: examples/programmer_extinction.md 存在
    examples_script = os.path.join(project_root, "examples", "programmer_extinction.md")
    if not os.path.exists(examples_script):
        errors.append(f"examples/programmer_extinction.md not found at {examples_script}")
    else:
        try:
            with open(examples_script, "r", encoding="utf-8") as f:
                content = f.read()
            if len(content) < 500:
                errors.append(
                    f"examples/programmer_extinction.md too short ({len(content)} chars), expected >= 500"
                )
        except Exception as e:
            errors.append(f"Failed to read examples/programmer_extinction.md: {str(e)}")

    # Test 3: workspace/programmer_extinction/output/final.mp4 存在
    final_mp4 = os.path.join(
        project_root, "workspace", "programmer_extinction", "output", "final.mp4"
    )
    if not os.path.exists(final_mp4):
        errors.append(f"final.mp4 not found at {final_mp4}")
    else:
        # Test 4: ffprobe 验证视频时长 > 60s
        try:
            ffprobe_result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet",
                    "-print_format", "json",
                    "-show_format", "-show_streams",
                    final_mp4
                ],
                capture_output=True, text=True, timeout=30
            )
            if ffprobe_result.returncode != 0:
                errors.append(f"ffprobe failed on final.mp4: {ffprobe_result.stderr[:200]}")
            else:
                probe_data = json.loads(ffprobe_result.stdout)

                # 验证时长 > 60s
                duration = float(probe_data.get("format", {}).get("duration", 0))
                if duration <= 60:
                    errors.append(
                        f"final.mp4 duration {duration:.1f}s is not > 60s"
                    )

                # 验证包含音频流
                streams = probe_data.get("streams", [])
                has_audio = any(s.get("codec_type") == "audio" for s in streams)
                if not has_audio:
                    errors.append("final.mp4 does not contain an audio stream")

                # 验证视频流存在
                video_streams = [s for s in streams if s.get("codec_type") == "video"]
                if not video_streams:
                    errors.append("final.mp4 does not contain a video stream")
                else:
                    # 验证分辨率合理 (至少 720p 宽度)
                    width = video_streams[0].get("width", 0)
                    height = video_streams[0].get("height", 0)
                    if width < 1280 or height < 720:
                        errors.append(
                            f"final.mp4 resolution {width}x{height} is below expected minimum 1280x720"
                        )

        except subprocess.TimeoutExpired:
            errors.append("ffprobe timed out after 30s")
        except json.JSONDecodeError as e:
            errors.append(f"Failed to parse ffprobe output: {str(e)}")
        except FileNotFoundError:
            errors.append("ffprobe not found — please install ffmpeg")
        except Exception as e:
            errors.append(f"ffprobe check failed: {str(e)}")

    # Test 5: 验证 pipeline_state 中包含必要素材类型
    # script.json 应记录每个 scene 的 visual.type 和 narration 信息
    script_json = os.path.join(
        project_root, "workspace", "programmer_extinction", "script.json"
    )
    if not os.path.exists(script_json):
        errors.append(f"script.json not found at {script_json}")
    else:
        try:
            with open(script_json, "r", encoding="utf-8") as f:
                script_data = json.load(f)

            scenes = script_data.get("scenes", [])

            # 检查 pipeline_state 已完成
            pipeline_state = script_data.get("pipeline_state", "")
            if pipeline_state != "composed":
                errors.append(
                    f"pipeline_state is '{pipeline_state}', expected 'composed'"
                )

            # 收集所有 visual types 和 narration 状态
            visual_types = set()
            has_tts_narration = False
            has_fetched_video = False

            for scene in scenes:
                visual = scene.get("visual", {})
                v_type = visual.get("type", "")
                v_subtype = visual.get("subtype", "")
                v_status = visual.get("status", "")

                # 收集 visual type
                if v_type:
                    visual_types.add(v_type)
                if v_subtype:
                    visual_types.add(v_subtype)

                # 检查是否有搜索到的视频素材 (fetch + video type)
                if v_type == "video" and v_status in ("approved", "fetched", "ready"):
                    has_fetched_video = True
                if v_type == "video" and visual.get("asset_path"):
                    has_fetched_video = True
                if v_type == "video" and visual.get("selected_candidate"):
                    has_fetched_video = True

                # 检查 TTS 旁白
                audio = scene.get("audio", {})
                narration_status = audio.get("narration_status", "")
                narration_path = audio.get("narration_path", "")
                if narration_status in ("done", "ready", "approved") or narration_path:
                    has_tts_narration = True

            # 验证至少1段搜索到的视频素材
            if not has_fetched_video:
                errors.append(
                    "No fetched video asset found in script.json scenes "
                    "(need at least 1 scene with visual.type='video' and asset/candidate)"
                )

            # 验证至少1张 AI 生成图片 (type=image)
            has_ai_image = "image" in visual_types
            if not has_ai_image:
                errors.append(
                    "No AI-generated image found in script.json scenes "
                    "(need at least 1 scene with visual.type='image')"
                )

            # 验证至少1张 handraw_chart (SVG方案)
            has_handraw_chart = "handraw_chart" in visual_types
            if not has_handraw_chart:
                errors.append(
                    "No handraw_chart found in script.json scenes "
                    "(need at least 1 scene with visual.type='handraw_chart')"
                )

            # 验证至少1张 handraw_illustration (DALL-E方案)
            has_handraw_illustration = "handraw_illustration" in visual_types
            if not has_handraw_illustration:
                errors.append(
                    "No handraw_illustration found in script.json scenes "
                    "(need at least 1 scene with visual.type='handraw_illustration')"
                )

            # 验证 TTS 旁白音频
            if not has_tts_narration:
                errors.append(
                    "No TTS narration audio found in script.json scenes "
                    "(need at least 1 scene with narration_status='done' or narration_path set)"
                )

        except json.JSONDecodeError as e:
            errors.append(f"Failed to parse script.json: {str(e)}")
        except Exception as e:
            errors.append(f"Failed to check script.json: {str(e)}")

    # Test 6: cut/README.md 存在且内容充分（可用性验收）
    readme_path = os.path.join(project_root, "cut", "README.md")
    if not os.path.exists(readme_path):
        errors.append(f"cut/README.md not found at {readme_path}")
    else:
        try:
            with open(readme_path, "r", encoding="utf-8") as f:
                readme_content = f.read()

            # README 应足够详细（至少 500 字符）
            if len(readme_content) < 500:
                errors.append(
                    f"cut/README.md too short ({len(readme_content)} chars), "
                    "expected >= 500 for usable quick-start guide"
                )

            # README 应包含关键章节
            required_sections = [
                ("快速上手", "Quick Start or 快速上手 section"),
                ("check_env", "check_env.py reference"),
            ]
            for keyword, description in required_sections:
                if keyword.lower() not in readme_content.lower():
                    errors.append(f"cut/README.md missing {description} (keyword: '{keyword}')")

        except Exception as e:
            errors.append(f"Failed to read cut/README.md: {str(e)}")

    # Test 7: cut/SKILL.md 存在且包含完整使用教程
    skill_md_path = os.path.join(project_root, "cut", "SKILL.md")
    if not os.path.exists(skill_md_path):
        errors.append(f"cut/SKILL.md not found at {skill_md_path}")
    else:
        try:
            with open(skill_md_path, "r", encoding="utf-8") as f:
                skill_content = f.read()

            if len(skill_content) < 1000:
                errors.append(
                    f"cut/SKILL.md too short ({len(skill_content)} chars), "
                    "expected >= 1000 for complete usage documentation"
                )

            # SKILL.md 应包含所有 sub-skill 名称
            required_skills = [
                "draft-script", "fetch-assets", "gen-assets",
                "review-assets", "compose-video"
            ]
            for skill_name in required_skills:
                if skill_name not in skill_content:
                    errors.append(f"cut/SKILL.md missing reference to '{skill_name}'")

        except Exception as e:
            errors.append(f"Failed to read cut/SKILL.md: {str(e)}")

    # 构建结果 JSON
    result = {
        "pass": len(errors) == 0,
        "errors": errors
    }

    # 输出 JSON (CRITICAL: 只有这一行输出到 stdout)
    print(json.dumps(result))

    # 使用合适的退出码
    sys.exit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
