#!/usr/bin/env python3
"""Test script for task6: review-assets skill (interactive HTML asset review page)."""
import json
import sys
import os
import tempfile
import subprocess
import re

# Project root: .rick/jobs/job_1/doing/tests/task6.py -> 5 levels up
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
REVIEW_ASSETS_DIR = os.path.join(PROJECT_ROOT, 'cut', 'skills', 'review-assets', 'scripts')
GENERATE_REVIEW_PY = os.path.join(REVIEW_ASSETS_DIR, 'generate_review.py')
REVIEW_HTML_TEMPLATE = os.path.join(REVIEW_ASSETS_DIR, 'review.html')


def is_stub(path):
    """Return True if file appears to be an unimplemented stub."""
    try:
        with open(path, 'r') as f:
            content = f.read()
        lines = [l for l in content.strip().splitlines() if l.strip()]
        return 'TODO' in content and len(lines) <= 5
    except Exception:
        return True


def make_script_json(num_scenes=10):
    """Create a script.json dict with the given number of scenes, each having candidates."""
    scenes = []
    for i in range(num_scenes):
        scene_id = f'scene_{i+1:02d}'
        scenes.append({
            'id': scene_id,
            'duration': 5,
            'narration': f'Narration for scene {i+1}.',
            'subtitle': f'Subtitle {i+1}',
            'visual': {
                'type': 'image' if i % 3 != 0 else 'video',
                'description': f'Visual description for scene {i+1}',
                'keywords': ['test', 'scene'],
                'status': 'fetched',
                'selected_candidate': None,
                'candidates': [
                    {
                        'url': f'https://example.com/asset_{i+1}_a.jpg',
                        'local_path': f'/tmp/asset_{i+1}_a.jpg',
                        'source': 'pexels',
                        'thumbnail': f'https://example.com/thumb_{i+1}_a.jpg',
                        'type': 'image' if i % 3 != 0 else 'video',
                    },
                    {
                        'url': f'https://example.com/asset_{i+1}_b.jpg',
                        'local_path': f'/tmp/asset_{i+1}_b.jpg',
                        'source': 'unsplash',
                        'thumbnail': f'https://example.com/thumb_{i+1}_b.jpg',
                        'type': 'image' if i % 3 != 0 else 'video',
                    },
                ],
                'asset_path': None,
            },
            'audio': {
                'narration_status': 'pending',
                'narration_path': None,
                'music': {
                    'description': f'Background music for scene {i+1}',
                    'keywords': ['ambient'],
                    'status': 'fetched',
                    'selected_candidate': None,
                    'candidates': [
                        {
                            'url': f'https://example.com/music_{i+1}_a.mp3',
                            'local_path': f'/tmp/music_{i+1}_a.mp3',
                            'source': 'freemusicarchive',
                            'type': 'audio',
                        },
                    ],
                    'asset_path': None,
                    'volume': 0.3,
                },
            },
        })
    return {
        'title': 'Test Script — 程序员消亡史',
        'total_duration': num_scenes * 5,
        'output_format': 'mp4',
        'resolution': '1920x1080',
        'pipeline_state': 'assets_fetched',
        'scenes': scenes,
    }


def run_generate_review(script_path, output_html_path):
    """Run generate_review.py as a subprocess and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, GENERATE_REVIEW_PY, script_path, output_html_path],
        capture_output=True, text=True, timeout=30
    )
    return result.returncode, result.stdout, result.stderr


def main():
    errors = []

    # ------------------------------------------------------------------ #
    # Pre-check: verify implementation files exist and are non-stubs      #
    # ------------------------------------------------------------------ #
    required_files = [
        (GENERATE_REVIEW_PY, 'generate_review.py'),
    ]
    for path, label in required_files:
        if not os.path.exists(path):
            errors.append(f'{label} does not exist at {path}')
        elif is_stub(path):
            errors.append(
                f'{label} appears to be a stub (contains TODO and ≤5 lines). '
                'Task6 implementation is required.'
            )

    if errors:
        result = {'pass': False, 'errors': errors}
        print(json.dumps(result))
        sys.exit(1)

    # Read the generate_review.py source for static analysis
    try:
        with open(GENERATE_REVIEW_PY, 'r') as f:
            gen_src = f.read()
    except Exception as e:
        errors.append(f'Failed to read generate_review.py: {e}')
        result = {'pass': False, 'errors': errors}
        print(json.dumps(result))
        sys.exit(1)

    # ------------------------------------------------------------------ #
    # Test 1: Generate review.html from 10-scene script.json             #
    # Verify HTML file is created and contains all scene IDs             #
    # ------------------------------------------------------------------ #
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = os.path.join(tmpdir, 'script.json')
            output_html = os.path.join(tmpdir, 'review.html')

            script_data = make_script_json(10)
            with open(script_path, 'w') as f:
                json.dump(script_data, f, ensure_ascii=False, indent=2)

            rc, stdout, stderr = run_generate_review(script_path, output_html)

            if not os.path.exists(output_html):
                errors.append(
                    f'Test 1: review.html was not generated at {output_html} '
                    f'(exit code={rc}, stderr={stderr[:200]})'
                )
            else:
                with open(output_html, 'r', encoding='utf-8') as f:
                    html_content = f.read()

                # Verify it's valid HTML (has basic structure)
                if '<html' not in html_content.lower() and '<!doctype' not in html_content.lower():
                    errors.append('Test 1: review.html does not appear to be valid HTML')

                # Verify all 10 scene IDs appear in the HTML
                for i in range(1, 11):
                    scene_id = f'scene_{i:02d}'
                    if scene_id not in html_content:
                        errors.append(f'Test 1: scene "{scene_id}" not found in review.html')

                # Verify candidate thumbnails/URLs are referenced
                found_candidates = sum(
                    1 for i in range(1, 11)
                    if f'asset_{i}_a' in html_content or f'thumb_{i}_a' in html_content
                )
                if found_candidates == 0:
                    errors.append(
                        'Test 1: review.html does not reference any candidate assets '
                        '(expected thumbnail URLs or asset paths from script.json)'
                    )
    except subprocess.TimeoutExpired:
        errors.append('Test 1: generate_review.py timed out after 30 seconds')
    except Exception as e:
        errors.append(f'Test 1: HTML generation test raised unexpected exception: {e}')

    # ------------------------------------------------------------------ #
    # Test 2: HTML contains media playback elements                       #
    # Verify <video> tags for video candidates, <audio> for music        #
    # ------------------------------------------------------------------ #
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = os.path.join(tmpdir, 'script.json')
            output_html = os.path.join(tmpdir, 'review.html')

            # Make a script with explicit video and audio candidates
            script_data = make_script_json(3)
            # Force scene_01 to have video type
            script_data['scenes'][0]['visual']['type'] = 'video'
            script_data['scenes'][0]['visual']['candidates'][0]['type'] = 'video'
            script_data['scenes'][0]['visual']['candidates'][0]['url'] = 'https://example.com/video_01.mp4'
            script_data['scenes'][0]['visual']['candidates'][1]['type'] = 'video'
            script_data['scenes'][0]['visual']['candidates'][1]['url'] = 'https://example.com/video_01b.mp4'

            with open(script_path, 'w') as f:
                json.dump(script_data, f, ensure_ascii=False, indent=2)

            rc, stdout, stderr = run_generate_review(script_path, output_html)

            if not os.path.exists(output_html):
                errors.append(
                    f'Test 2: review.html was not generated '
                    f'(exit code={rc}, stderr={stderr[:200]})'
                )
            else:
                with open(output_html, 'r', encoding='utf-8') as f:
                    html_content = f.read()

                # Verify <video> or inline playback for video candidates
                has_video_tag = '<video' in html_content.lower()
                has_video_url = 'video_01.mp4' in html_content
                if not has_video_tag and not has_video_url:
                    errors.append(
                        'Test 2: review.html does not contain <video> tags for video candidates '
                        '(expected HTML5 video element for inline playback)'
                    )

                # Verify <audio> tag or audio URL for music candidates
                has_audio_tag = '<audio' in html_content.lower()
                has_music_url = any(
                    f'music_{i}_a' in html_content for i in range(1, 4)
                )
                if not has_audio_tag and not has_music_url:
                    errors.append(
                        'Test 2: review.html does not contain <audio> tags for music candidates '
                        '(expected HTML5 audio element for music preview)'
                    )
    except subprocess.TimeoutExpired:
        errors.append('Test 2: generate_review.py timed out after 30 seconds')
    except Exception as e:
        errors.append(f'Test 2: media playback test raised unexpected exception: {e}')

    # ------------------------------------------------------------------ #
    # Test 3: HTML contains save/submit mechanism and JS to write back    #
    # Verify JavaScript updates selected_candidate and status fields      #
    # ------------------------------------------------------------------ #
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = os.path.join(tmpdir, 'script.json')
            output_html = os.path.join(tmpdir, 'review.html')

            script_data = make_script_json(5)
            with open(script_path, 'w') as f:
                json.dump(script_data, f, ensure_ascii=False, indent=2)

            rc, stdout, stderr = run_generate_review(script_path, output_html)

            if not os.path.exists(output_html):
                errors.append(
                    f'Test 3: review.html was not generated '
                    f'(exit code={rc}, stderr={stderr[:200]})'
                )
            else:
                with open(output_html, 'r', encoding='utf-8') as f:
                    html_content = f.read()

                # Verify save/submit button exists
                has_save = any(kw in html_content.lower() for kw in [
                    '保存', 'save', 'submit', '提交', '确认',
                ])
                if not has_save:
                    errors.append(
                        'Test 3: review.html does not contain a save/submit button '
                        '(expected a button labeled 保存, save, or submit)'
                    )

                # Verify JavaScript handles selected_candidate update
                has_selected_candidate = 'selected_candidate' in html_content
                if not has_selected_candidate:
                    errors.append(
                        'Test 3: review.html JavaScript does not reference "selected_candidate" '
                        '(expected JS to update visual.selected_candidate on save)'
                    )

                # Verify JavaScript handles status update to "approved"
                has_approved = 'approved' in html_content
                if not has_approved:
                    errors.append(
                        'Test 3: review.html JavaScript does not reference "approved" status '
                        '(expected JS to set visual.status = "approved" when candidate is selected)'
                    )

                # Verify JavaScript handles "need AI generation" / "generating" status
                has_generating = any(kw in html_content for kw in [
                    'generating', 'AI生成', 'ai_generate', 'need_ai', '需要AI', '需AI',
                ])
                if not has_generating:
                    errors.append(
                        'Test 3: review.html does not support marking scenes as "need AI generation" '
                        '(expected a button/option to set visual.status = "generating")'
                    )
    except subprocess.TimeoutExpired:
        errors.append('Test 3: generate_review.py timed out after 30 seconds')
    except Exception as e:
        errors.append(f'Test 3: save mechanism test raised unexpected exception: {e}')

    # ------------------------------------------------------------------ #
    # Test 4: script.json write-back — approved selections               #
    # Simulate save: verify selected_candidate and status are updated    #
    # ------------------------------------------------------------------ #
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = os.path.join(tmpdir, 'script.json')
            output_html = os.path.join(tmpdir, 'review.html')

            script_data = make_script_json(5)
            with open(script_path, 'w') as f:
                json.dump(script_data, f, ensure_ascii=False, indent=2)

            rc, stdout, stderr = run_generate_review(script_path, output_html)

            if not os.path.exists(output_html):
                errors.append(
                    f'Test 4: review.html was not generated '
                    f'(exit code={rc}, stderr={stderr[:200]})'
                )
            else:
                with open(output_html, 'r', encoding='utf-8') as f:
                    html_content = f.read()

                # Check that the HTML embeds the script.json path or data for write-back
                # The HTML must know where to write back (either embedded path or fetch API)
                script_path_in_html = (
                    os.path.basename(script_path) in html_content
                    or 'script.json' in html_content
                    or 'script_path' in html_content
                    or 'scriptPath' in html_content
                )
                # Also acceptable: HTML uses a server or embedded data approach
                has_writeback_mechanism = (
                    script_path_in_html
                    or 'fetch(' in html_content
                    or 'XMLHttpRequest' in html_content
                    or 'fs.writeFile' in html_content
                    or 'writeFile' in html_content
                    or 'save_script' in html_content
                    or 'saveScript' in html_content
                    or 'save_review' in html_content
                    or 'download' in html_content.lower()
                )
                if not has_writeback_mechanism:
                    errors.append(
                        'Test 4: review.html does not appear to implement write-back to script.json '
                        '(expected: embedded script path, fetch API, or download mechanism)'
                    )

                # Verify pipeline_state update logic is present
                has_pipeline_state = 'pipeline_state' in html_content
                has_assets_reviewed = 'assets_reviewed' in html_content
                if not has_pipeline_state and not has_assets_reviewed:
                    errors.append(
                        'Test 4: review.html does not update pipeline_state to "assets_reviewed" '
                        '(expected pipeline_state field update in save logic)'
                    )
    except subprocess.TimeoutExpired:
        errors.append('Test 4: generate_review.py timed out after 30 seconds')
    except Exception as e:
        errors.append(f'Test 4: script.json write-back test raised unexpected exception: {e}')

    # ------------------------------------------------------------------ #
    # Test 5: State restoration — re-opening page restores selections    #
    # Verify HTML reads existing selected_candidate values from JSON     #
    # ------------------------------------------------------------------ #
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = os.path.join(tmpdir, 'script.json')
            output_html = os.path.join(tmpdir, 'review.html')

            # Create script with pre-existing selections (simulating a previously saved state)
            script_data = make_script_json(5)
            # Pre-set some selections
            script_data['scenes'][0]['visual']['selected_candidate'] = 0
            script_data['scenes'][0]['visual']['status'] = 'approved'
            script_data['scenes'][1]['visual']['selected_candidate'] = 1
            script_data['scenes'][1]['visual']['status'] = 'approved'
            script_data['scenes'][2]['visual']['status'] = 'generating'
            script_data['pipeline_state'] = 'assets_reviewed'

            with open(script_path, 'w') as f:
                json.dump(script_data, f, ensure_ascii=False, indent=2)

            rc, stdout, stderr = run_generate_review(script_path, output_html)

            if not os.path.exists(output_html):
                errors.append(
                    f'Test 5: review.html was not generated with pre-existing selections '
                    f'(exit code={rc}, stderr={stderr[:200]})'
                )
            else:
                with open(output_html, 'r', encoding='utf-8') as f:
                    html_content = f.read()

                # The HTML should reflect existing approved/generating states
                # Either by embedding the JSON data or by reading it at runtime
                has_state_awareness = any(kw in html_content for kw in [
                    'approved', 'generating', 'selected_candidate',
                    '"status"', 'pipeline_state',
                ])
                if not has_state_awareness:
                    errors.append(
                        'Test 5: review.html does not appear to restore prior selection state '
                        '(expected: HTML embeds or reads existing selected_candidate/status values)'
                    )

                # Check that "assets_reviewed" pipeline state is reflected
                if 'assets_reviewed' not in html_content:
                    # Acceptable if state is loaded dynamically from JSON at runtime
                    # Check that the script data is embedded
                    has_embedded_data = (
                        'scene_01' in html_content
                        and ('approved' in html_content or 'generating' in html_content)
                    )
                    if not has_embedded_data:
                        print(
                            'Test 5: pipeline_state "assets_reviewed" not found in HTML — '
                            'may be loaded dynamically at runtime (acceptable)',
                            file=sys.stderr
                        )
    except subprocess.TimeoutExpired:
        errors.append('Test 5: generate_review.py timed out after 30 seconds')
    except Exception as e:
        errors.append(f'Test 5: state restoration test raised unexpected exception: {e}')

    # ------------------------------------------------------------------ #
    # Test 6: Source code static analysis                                 #
    # Verify generate_review.py reads script.json and writes review.html #
    # ------------------------------------------------------------------ #
    try:
        # Verify script.json reading
        has_json_read = any(kw in gen_src for kw in [
            'json.load', 'json.loads', 'open(', 'script',
        ])
        if not has_json_read:
            errors.append(
                'Test 6: generate_review.py does not appear to read script.json '
                '(expected json.load or open() call)'
            )

        # Verify HTML output writing
        has_html_write = any(kw in gen_src for kw in [
            '.write(', 'open(', 'html', 'HTML',
        ])
        if not has_html_write:
            errors.append(
                'Test 6: generate_review.py does not appear to write HTML output '
                '(expected file write operation)'
            )

        # Verify candidate handling
        has_candidates = 'candidates' in gen_src
        if not has_candidates:
            errors.append(
                'Test 6: generate_review.py does not reference "candidates" field '
                '(expected iteration over scene candidates to build review UI)'
            )

        # Verify visual.status update logic (approved / generating)
        has_status_logic = 'approved' in gen_src or 'status' in gen_src
        if not has_status_logic:
            errors.append(
                'Test 6: generate_review.py does not contain status update logic '
                '(expected "approved" or "generating" status handling)'
            )

        # Verify pipeline_state update
        has_pipeline_update = 'pipeline_state' in gen_src or 'assets_reviewed' in gen_src
        if not has_pipeline_update:
            errors.append(
                'Test 6: generate_review.py does not update pipeline_state '
                '(expected pipeline_state = "assets_reviewed" after save)'
            )
    except Exception as e:
        errors.append(f'Test 6: static analysis raised unexpected exception: {e}')

    # ------------------------------------------------------------------ #
    # Build result                                                         #
    # ------------------------------------------------------------------ #
    result = {
        'pass': len(errors) == 0,
        'errors': errors,
    }
    print(json.dumps(result))
    sys.exit(0 if result['pass'] else 1)


if __name__ == '__main__':
    main()
