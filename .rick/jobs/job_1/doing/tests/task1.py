#!/usr/bin/env python3
import json
import sys
import os
import subprocess
import shutil
import time
import tempfile


def main():
    errors = []

    # Project root: tests/ -> doing/ -> job_1/ -> jobs/ -> .rick/ -> cut/
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..', '..', '..'))
    cut_dir = os.path.join(project_root, 'cut')

    print(f"project_root: {project_root}", file=sys.stderr)
    print(f"cut_dir: {cut_dir}", file=sys.stderr)

    check_env_script = os.path.join(cut_dir, 'scripts', 'check_env.py')

    # Test 1a: check_env.py FFmpeg behavior
    if not os.path.exists(check_env_script):
        errors.append(f'cut/scripts/check_env.py does not exist at {check_env_script}')
    else:
        try:
            result = subprocess.run(
                [sys.executable, check_env_script],
                capture_output=True, text=True
            )
            output = result.stdout + result.stderr
            ffmpeg_present = shutil.which('ffmpeg') is not None
            if ffmpeg_present:
                if '✓ FFmpeg OK' not in output and 'FFmpeg OK' not in output:
                    errors.append(
                        f'check_env.py: FFmpeg is installed but output missing "✓ FFmpeg OK". '
                        f'Output: {output!r}'
                    )
            else:
                if 'brew install ffmpeg' not in output:
                    errors.append(
                        f'check_env.py: FFmpeg not installed but output missing "brew install ffmpeg". '
                        f'Output: {output!r}'
                    )
        except Exception as e:
            errors.append(f'Failed to run check_env.py for FFmpeg check: {str(e)}')

        # Test 1b: check_env.py cairosvg behavior
        try:
            result = subprocess.run(
                [sys.executable, check_env_script],
                capture_output=True, text=True
            )
            output = result.stdout + result.stderr
            try:
                import cairosvg
                cairosvg_present = True
            except ImportError:
                cairosvg_present = False

            if not cairosvg_present:
                if 'pip install cairosvg' not in output:
                    errors.append(
                        f'check_env.py: cairosvg not installed but output missing "pip install cairosvg". '
                        f'Output: {output!r}'
                    )
        except Exception as e:
            errors.append(f'Failed to run check_env.py for cairosvg check: {str(e)}')

    # Test 2: cut/SKILL.md has valid YAML frontmatter with name and description
    skill_md = os.path.join(cut_dir, 'SKILL.md')
    if not os.path.exists(skill_md):
        errors.append(f'cut/SKILL.md does not exist at {skill_md}')
    else:
        try:
            with open(skill_md, 'r') as f:
                content = f.read()
            if not content.startswith('---'):
                errors.append('cut/SKILL.md does not start with YAML frontmatter (---)')
            else:
                parts = content.split('---', 2)
                if len(parts) < 3:
                    errors.append('cut/SKILL.md has invalid YAML frontmatter structure')
                else:
                    try:
                        import yaml
                        frontmatter = yaml.safe_load(parts[1])
                        if not isinstance(frontmatter, dict):
                            errors.append('cut/SKILL.md frontmatter is not a valid YAML mapping')
                        else:
                            if 'name' not in frontmatter:
                                errors.append('cut/SKILL.md frontmatter missing "name" field')
                            if 'description' not in frontmatter:
                                errors.append('cut/SKILL.md frontmatter missing "description" field')
                    except Exception as e:
                        errors.append(f'cut/SKILL.md frontmatter YAML parse error: {str(e)}')
        except Exception as e:
            errors.append(f'Failed to read cut/SKILL.md: {str(e)}')

    # Test 3: cut/cut-config.yaml parses cleanly and contains handraw section
    config_yaml = os.path.join(cut_dir, 'cut-config.yaml')
    if not os.path.exists(config_yaml):
        errors.append(f'cut/cut-config.yaml does not exist at {config_yaml}')
    else:
        try:
            import yaml
            with open(config_yaml, 'r') as f:
                config = yaml.safe_load(f)
            if config is None:
                errors.append('cut/cut-config.yaml is empty or null')
            elif not isinstance(config, dict):
                errors.append('cut/cut-config.yaml root is not a YAML mapping')
            elif 'handraw' not in config:
                errors.append('cut/cut-config.yaml missing "handraw" section')
        except Exception as e:
            errors.append(f'Failed to parse cut/cut-config.yaml: {str(e)}')

    # Test 4: Directory structure matches SPEC.md
    expected_files = [
        'SKILL.md',
        'cut-config.yaml',
        'scripts/check_env.py',
        'skills/draft-script/SKILL.md',
        'skills/draft-script/scripts/draft_script.py',
        'skills/draft-script/references/script_schema.json',
        'skills/fetch-assets/SKILL.md',
        'skills/fetch-assets/scripts/fetch_video.py',
        'skills/fetch-assets/scripts/fetch_image.py',
        'skills/fetch-assets/scripts/fetch_music.py',
        'skills/gen-assets/SKILL.md',
        'skills/gen-assets/scripts/gen_tts.py',
        'skills/gen-assets/scripts/gen_image.py',
        'skills/gen-assets/scripts/gen_video.py',
        'skills/gen-assets/scripts/gen_handraw.py',
        'skills/gen-assets/scripts/providers/tts_base.py',
        'skills/gen-assets/scripts/providers/tts_edge.py',
        'skills/gen-assets/scripts/providers/tts_openai.py',
        'skills/gen-assets/scripts/providers/tts_elevenlabs.py',
        'skills/gen-assets/scripts/providers/image_base.py',
        'skills/gen-assets/scripts/providers/image_dalle3.py',
        'skills/gen-assets/scripts/providers/image_sdiffusion.py',
        'skills/gen-assets/scripts/providers/video_base.py',
        'skills/gen-assets/scripts/providers/video_runway.py',
        'skills/gen-assets/scripts/providers/handraw_base.py',
        'skills/gen-assets/scripts/providers/handraw_chart_svg.py',
        'skills/gen-assets/scripts/providers/handraw_illus_dalle.py',
        'skills/review-assets/SKILL.md',
        'skills/review-assets/scripts/generate_review.py',
        'skills/review-assets/scripts/review.html',
        'skills/compose-video/SKILL.md',
        'skills/compose-video/scripts/compose.py',
    ]
    for rel_path in expected_files:
        full_path = os.path.join(cut_dir, rel_path)
        if not os.path.exists(full_path):
            errors.append(f'Expected file missing: cut/{rel_path}')

    # Test 5: Workspace creation — two runs produce two different timestamp subdirs
    if not os.path.exists(check_env_script):
        errors.append('Cannot test workspace creation: check_env.py missing')
    else:
        tmp_base = tempfile.mkdtemp()
        try:
            project_name = 'test_project'
            r1 = subprocess.run(
                [sys.executable, check_env_script,
                 '--workspace-base', tmp_base, '--project', project_name],
                capture_output=True, text=True
            )
            print(f"workspace run1 stdout: {r1.stdout!r}", file=sys.stderr)
            print(f"workspace run1 stderr: {r1.stderr!r}", file=sys.stderr)

            time.sleep(1.1)  # ensure different second-level timestamp

            r2 = subprocess.run(
                [sys.executable, check_env_script,
                 '--workspace-base', tmp_base, '--project', project_name],
                capture_output=True, text=True
            )
            print(f"workspace run2 stdout: {r2.stdout!r}", file=sys.stderr)

            project_dir = os.path.join(tmp_base, project_name)
            if not os.path.isdir(project_dir):
                errors.append(
                    f'Workspace project dir not created at {project_dir}. '
                    f'run1 output: {r1.stdout + r1.stderr!r}'
                )
            else:
                timestamp_dirs = [
                    d for d in os.listdir(project_dir)
                    if os.path.isdir(os.path.join(project_dir, d))
                ]
                print(f"timestamp dirs: {timestamp_dirs}", file=sys.stderr)
                if len(timestamp_dirs) < 2:
                    errors.append(
                        f'Workspace: expected 2 distinct timestamp subdirs under '
                        f'{project_dir}, found {len(timestamp_dirs)}: {timestamp_dirs}'
                    )
                else:
                    # Verify the two dirs are different
                    if timestamp_dirs[0] == timestamp_dirs[1]:
                        errors.append(
                            f'Workspace: two runs created the same timestamp dir: {timestamp_dirs[0]}'
                        )
        except Exception as e:
            errors.append(f'Workspace creation test failed: {str(e)}')
        finally:
            shutil.rmtree(tmp_base, ignore_errors=True)

    result = {
        'pass': len(errors) == 0,
        'errors': errors
    }

    print(json.dumps(result))
    sys.exit(0 if result['pass'] else 1)


if __name__ == '__main__':
    main()
