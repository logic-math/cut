# Description: 验证 cut workspace 目录下 script.json 和素材文件的完整性

import argparse
import json
import os
import sys
from pathlib import Path


def check_script(script_path: str) -> dict:
    """验证 script.json 结构和素材文件完整性"""
    errors = []
    warnings = []
    result = {}

    script_file = Path(script_path)
    if not script_file.exists():
        return {"pass": False, "errors": [f"script.json not found: {script_path}"], "warnings": []}

    try:
        script = json.loads(script_file.read_text())
    except json.JSONDecodeError as e:
        return {"pass": False, "errors": [f"Invalid JSON: {e}"], "warnings": []}

    # 检查顶层字段
    required_fields = ["title", "pipeline_state", "scenes"]
    for f in required_fields:
        if f not in script:
            errors.append(f"Missing required field: {f}")

    pipeline_state = script.get("pipeline_state", "unknown")
    scenes = script.get("scenes", [])
    result["pipeline_state"] = pipeline_state
    result["scene_count"] = len(scenes)
    result["total_duration"] = script.get("total_duration", 0)

    # 统计各类型
    visual_types = {}
    asset_ready = 0
    narration_ready = 0

    for scene in scenes:
        sid = scene.get("id", "?")
        visual = scene.get("visual", {})
        audio = scene.get("audio", {})

        vtype = visual.get("type", "unknown")
        visual_types[vtype] = visual_types.get(vtype, 0) + 1

        # 检查 asset_path
        asset_path = visual.get("asset_path")
        if asset_path:
            if Path(asset_path).exists():
                asset_ready += 1
            else:
                warnings.append(f"scene {sid}: asset_path not found: {asset_path}")
        elif pipeline_state in ("assets_reviewed", "composed"):
            warnings.append(f"scene {sid}: asset_path is null in state={pipeline_state}")

        # 检查 narration_path
        narration_path = audio.get("narration_path")
        if narration_path:
            if Path(narration_path).exists():
                narration_ready += 1
            else:
                warnings.append(f"scene {sid}: narration_path not found: {narration_path}")

    result["visual_types"] = visual_types
    result["asset_ready"] = asset_ready
    result["narration_ready"] = narration_ready

    # 检查最终视频（如果 composed）
    if pipeline_state == "composed":
        workspace_dir = script_file.parent
        output_dir = workspace_dir / "output"
        mp4_files = list(output_dir.glob("*.mp4")) if output_dir.exists() else []
        if mp4_files:
            result["output_video"] = str(mp4_files[0])
            result["output_size_mb"] = round(mp4_files[0].stat().st_size / 1024 / 1024, 2)
        else:
            warnings.append("pipeline_state=composed but no .mp4 found in output/")

    result["errors"] = errors
    result["warnings"] = warnings
    result["pass"] = len(errors) == 0

    return result


def run_test():
    """内置测试：创建临时 script.json 并验证"""
    import tempfile
    import shutil

    tmpdir = Path(tempfile.mkdtemp())
    try:
        script = {
            "title": "Test Video",
            "pipeline_state": "draft",
            "total_duration": 30,
            "scenes": [
                {
                    "id": "scene_01",
                    "duration": 10,
                    "narration": "Hello world",
                    "visual": {"type": "video", "asset_path": None, "keywords": ["test"]},
                    "audio": {"narration_path": None}
                }
            ]
        }
        script_path = tmpdir / "script.json"
        script_path.write_text(json.dumps(script))

        result = check_script(str(script_path))
        assert result["pass"], f"Expected pass, got errors: {result['errors']}"
        assert result["pipeline_state"] == "draft"
        assert result["scene_count"] == 1
        print(json.dumps({"pass": True, "result": "built-in test passed"}))
    finally:
        shutil.rmtree(tmpdir)


def main():
    parser = argparse.ArgumentParser(description="Validate cut pipeline script.json and assets")
    parser.add_argument("--script", help="Path to script.json")
    parser.add_argument("--test", action="store_true", help="Run built-in tests")
    args = parser.parse_args()

    if args.test:
        run_test()
        return

    if not args.script:
        parser.print_help()
        sys.exit(1)

    result = check_script(args.script)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not result["pass"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
