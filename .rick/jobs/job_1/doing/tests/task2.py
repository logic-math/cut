#!/usr/bin/env python3
import json
import sys
import os
import subprocess
import shutil
import tempfile
import re


def main():
    errors = []

    # Project root: tests/ -> doing/ -> job_1/ -> jobs/ -> .rick/ -> cut/
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..', '..', '..'))
    cut_dir = os.path.join(project_root, 'cut')
    draft_script = os.path.join(cut_dir, 'skills', 'draft-script', 'scripts', 'draft_script.py')
    schema_file = os.path.join(cut_dir, 'skills', 'draft-script', 'references', 'script_schema.json')

    print(f"project_root: {project_root}", file=sys.stderr)
    print(f"draft_script: {draft_script}", file=sys.stderr)

    # Sample lecture content: 《程序员消亡史》~500 chars
    SAMPLE_500 = """# 程序员消亡史

二〇三五年，最后一批程序员走出了硅谷的办公楼。

他们曾经是这个世界的造物主，用代码构建了互联网的每一块砖石。他们熬夜调试，用咖啡续命，用 bug 和 fix 书写着数字文明的史诗。

然而 AI 来了。起初，AI 只是写一些简单的函数；后来，它能独立完成整个模块；再后来，它开始设计系统架构。程序员们发现，自己的工作正在以指数级的速度被取代。

有人愤怒，有人绝望，有人转型做了 AI 训练师，有人回归农耕，有人成了哲学家。

最后一位程序员关上了笔记本，留下一行注释：

```
# 我们创造了自己的终结者
# 但也许，这才是进化的本来面目
```

数字文明继续运转，只是再也没有人类的手指敲击键盘的声音。
"""

    # Sample lecture content: >3000 chars for boundary test
    SAMPLE_3000 = SAMPLE_500 * 7  # ~3500 chars

    # Test 1: draft_script.py exists
    if not os.path.exists(draft_script):
        errors.append(f'draft_script.py does not exist at {draft_script}')

    # Test 2: script_schema.json exists and is valid JSON
    schema = None
    if not os.path.exists(schema_file):
        errors.append(f'script_schema.json does not exist at {schema_file}')
    else:
        try:
            with open(schema_file, 'r') as f:
                schema = json.load(f)
        except Exception as e:
            errors.append(f'script_schema.json is not valid JSON: {str(e)}')

    # Only proceed with run tests if the script exists
    if not os.path.exists(draft_script):
        result = {'pass': len(errors) == 0, 'errors': errors}
        print(json.dumps(result))
        sys.exit(0 if result['pass'] else 1)

    # Test 3: Run with 500-char sample, verify script.json and script_preview.md
    tmp_dir = tempfile.mkdtemp()
    try:
        sample_md = os.path.join(tmp_dir, 'sample.md')
        with open(sample_md, 'w', encoding='utf-8') as f:
            f.write(SAMPLE_500)

        print(f"Running draft_script.py with 500-char sample...", file=sys.stderr)
        result_run = subprocess.run(
            [sys.executable, draft_script, '--input', sample_md, '--project', 'test'],
            capture_output=True, text=True, cwd=tmp_dir
        )
        print(f"stdout: {result_run.stdout[:500]!r}", file=sys.stderr)
        print(f"stderr: {result_run.stderr[:500]!r}", file=sys.stderr)

        if result_run.returncode != 0:
            errors.append(
                f'draft_script.py exited with code {result_run.returncode}. '
                f'stderr: {result_run.stderr[:300]}'
            )
        else:
            # Find script.json in workspace
            workspace_dir = os.path.join(tmp_dir, 'workspace', 'test')
            script_json_path = None
            script_preview_path = None

            if os.path.isdir(workspace_dir):
                for ts_dir in os.listdir(workspace_dir):
                    ts_path = os.path.join(workspace_dir, ts_dir)
                    candidate_json = os.path.join(ts_path, 'script.json')
                    candidate_preview = os.path.join(ts_path, 'script_preview.md')
                    if os.path.exists(candidate_json):
                        script_json_path = candidate_json
                    if os.path.exists(candidate_preview):
                        script_preview_path = candidate_preview
            else:
                errors.append(f'workspace/test directory not created under {tmp_dir}')

            # Test 3a: script.json exists
            if script_json_path is None:
                errors.append('script.json not found in workspace/test/<timestamp>/')
            else:
                # Test 3b: script.json passes JSON Schema validation
                try:
                    with open(script_json_path, 'r', encoding='utf-8') as f:
                        script_data = json.load(f)

                    if schema is not None:
                        try:
                            import jsonschema
                            jsonschema.validate(instance=script_data, schema=schema)
                        except ImportError:
                            errors.append('jsonschema library not installed; cannot validate script.json')
                        except jsonschema.ValidationError as ve:
                            errors.append(f'script.json fails JSON Schema validation: {ve.message}')

                    # Test 3c: pipeline_state is "draft"
                    pipeline_state = script_data.get('pipeline_state')
                    if pipeline_state != 'draft':
                        errors.append(
                            f'script.json pipeline_state is {pipeline_state!r}, expected "draft"'
                        )

                    # Test 3d: all visual.keywords are English (no Chinese characters)
                    scenes = script_data.get('scenes', [])
                    if not scenes:
                        errors.append('script.json has no scenes')
                    else:
                        chinese_pattern = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf]')
                        for scene in scenes:
                            scene_id = scene.get('id', '?')
                            keywords = scene.get('visual', {}).get('keywords', [])
                            for kw in keywords:
                                if chinese_pattern.search(kw):
                                    errors.append(
                                        f'scene {scene_id}: visual.keyword {kw!r} contains Chinese characters'
                                    )

                except json.JSONDecodeError as e:
                    errors.append(f'script.json is not valid JSON: {str(e)}')
                except Exception as e:
                    errors.append(f'Failed to validate script.json: {str(e)}')

            # Test 3e: script_preview.md exists and contains required columns
            if script_preview_path is None:
                errors.append('script_preview.md not found in workspace/test/<timestamp>/')
            else:
                try:
                    with open(script_preview_path, 'r', encoding='utf-8') as f:
                        preview_content = f.read()

                    # Must contain a Markdown table (lines with |)
                    table_lines = [l for l in preview_content.splitlines() if '|' in l]
                    if len(table_lines) < 2:
                        errors.append('script_preview.md does not contain a Markdown table (need at least 2 lines with |)')
                    else:
                        # Check required columns exist in header
                        header = table_lines[0].lower()
                        required_columns = ['场景', 'type']
                        # Accept English alternatives
                        for col in ['scene', '场景编号', '场景']:
                            if col in header:
                                break
                        else:
                            errors.append('script_preview.md table header missing scene number column (场景/scene)')

                        if 'type' not in header and 'visual' not in header:
                            errors.append('script_preview.md table header missing visual.type column')

                        # Check for duration-related column
                        if '时长' not in header and 'duration' not in header:
                            errors.append('script_preview.md table header missing duration column (时长/duration)')

                        # Check for narration-related column
                        if '旁白' not in header and 'narration' not in header:
                            errors.append('script_preview.md table header missing narration column (旁白/narration)')

                        # Check for visual description column
                        if '画面' not in header and 'description' not in header and 'visual' not in header:
                            errors.append('script_preview.md table header missing visual description column (画面描述/description)')

                except Exception as e:
                    errors.append(f'Failed to read script_preview.md: {str(e)}')

    except Exception as e:
        errors.append(f'500-char sample test failed unexpectedly: {str(e)}')
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # Test 4: Boundary test with >3000 char input
    tmp_dir2 = tempfile.mkdtemp()
    try:
        long_md = os.path.join(tmp_dir2, 'long_sample.md')
        with open(long_md, 'w', encoding='utf-8') as f:
            f.write(SAMPLE_3000)

        print(f"Running draft_script.py with >3000-char sample...", file=sys.stderr)
        result_long = subprocess.run(
            [sys.executable, draft_script, '--input', long_md, '--project', 'test_long'],
            capture_output=True, text=True, cwd=tmp_dir2
        )
        print(f"long run returncode: {result_long.returncode}", file=sys.stderr)
        print(f"long run stderr: {result_long.stderr[:300]!r}", file=sys.stderr)

        if result_long.returncode != 0:
            errors.append(
                f'draft_script.py failed on >3000-char input (exit {result_long.returncode}). '
                f'stderr: {result_long.stderr[:300]}'
            )
        else:
            # Find script.json
            workspace_dir2 = os.path.join(tmp_dir2, 'workspace', 'test_long')
            long_script_path = None
            if os.path.isdir(workspace_dir2):
                for ts_dir in os.listdir(workspace_dir2):
                    candidate = os.path.join(workspace_dir2, ts_dir, 'script.json')
                    if os.path.exists(candidate):
                        long_script_path = candidate
                        break

            if long_script_path is None:
                errors.append('script.json not found after >3000-char input run')
            else:
                try:
                    with open(long_script_path, 'r', encoding='utf-8') as f:
                        long_data = json.load(f)

                    scenes = long_data.get('scenes', [])
                    num_scenes = len(scenes)
                    if num_scenes < 10 or num_scenes > 30:
                        errors.append(
                            f'Boundary test: expected 10-30 scenes for >3000-char input, got {num_scenes}'
                        )

                    total_duration = long_data.get('total_duration', 0)
                    if total_duration <= 0:
                        errors.append(
                            f'Boundary test: total_duration is {total_duration}, expected > 0'
                        )
                    # Rough sanity: ~100-300 seconds per 500 chars is reasonable for a video
                    # For ~3500 chars, expect at least 60s and at most 1800s
                    if total_duration < 60:
                        errors.append(
                            f'Boundary test: total_duration {total_duration}s seems too short for >3000-char input'
                        )
                    if total_duration > 1800:
                        errors.append(
                            f'Boundary test: total_duration {total_duration}s seems unreasonably long for >3000-char input'
                        )

                except Exception as e:
                    errors.append(f'Boundary test: failed to parse script.json: {str(e)}')

    except Exception as e:
        errors.append(f'Boundary test failed unexpectedly: {str(e)}')
    finally:
        shutil.rmtree(tmp_dir2, ignore_errors=True)

    result = {
        'pass': len(errors) == 0,
        'errors': errors
    }

    print(json.dumps(result))
    sys.exit(0 if result['pass'] else 1)


if __name__ == '__main__':
    main()
