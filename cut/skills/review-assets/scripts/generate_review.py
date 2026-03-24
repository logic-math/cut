#!/usr/bin/env python3
"""generate_review.py — Generate an interactive HTML asset review page from script.json.

Usage:
    python3 generate_review.py <script_path> <output_html_path>

The generated HTML page embeds the full script data and provides:
- Visual candidate preview (image thumbnails, video inline playback)
- Audio candidate playback (HTML5 audio)
- Single-select per scene candidate
- "Need AI Generation" button per scene
- Save button that downloads updated script.json with:
    - visual.selected_candidate (index)
    - visual.status ("approved" or "generating")
    - audio.music.selected_candidate (index)
    - audio.music.status ("approved" or "generating")
    - pipeline_state = "assets_reviewed"
"""

import json
import sys
import os


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>cut — Asset Review: {title}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           background: #0f1117; color: #e0e0e0; padding: 20px; }}
    h1 {{ font-size: 1.4rem; color: #fff; margin-bottom: 6px; }}
    .meta {{ font-size: 0.85rem; color: #888; margin-bottom: 24px; }}
    .scene-card {{ background: #1a1d27; border: 1px solid #2a2d3a; border-radius: 10px;
                   margin-bottom: 24px; padding: 18px; }}
    .scene-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }}
    .scene-id {{ background: #3a3f5c; color: #a0aeff; padding: 3px 10px;
                 border-radius: 20px; font-size: 0.8rem; font-weight: 600; }}
    .scene-status {{ padding: 3px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; }}
    .status-approved {{ background: #1a3a2a; color: #4ade80; }}
    .status-generating {{ background: #3a2a1a; color: #fb923c; }}
    .status-fetched {{ background: #1a2a3a; color: #60a5fa; }}
    .status-pending {{ background: #2a2a2a; color: #9ca3af; }}
    .scene-narration {{ font-size: 0.9rem; color: #b0b8cc; margin-bottom: 10px;
                        line-height: 1.5; padding: 8px 12px; background: #12151e;
                        border-radius: 6px; border-left: 3px solid #3a3f5c; }}
    .section-label {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em;
                      color: #666; margin: 12px 0 8px; }}
    .candidates-grid {{ display: flex; flex-wrap: wrap; gap: 10px; }}
    .candidate {{ border: 2px solid #2a2d3a; border-radius: 8px; padding: 8px;
                  cursor: pointer; transition: all 0.15s; min-width: 160px; max-width: 220px;
                  flex: 1; background: #12151e; position: relative; }}
    .candidate:hover {{ border-color: #4a5080; background: #161921; }}
    .candidate.selected {{ border-color: #4ade80; background: #0d1f16; }}
    .candidate input[type=radio] {{ position: absolute; opacity: 0; width: 0; height: 0; }}
    .candidate-check {{ position: absolute; top: 6px; right: 6px; width: 20px; height: 20px;
                        border-radius: 50%; border: 2px solid #444; background: #1a1d27;
                        display: flex; align-items: center; justify-content: center;
                        font-size: 12px; transition: all 0.15s; }}
    .candidate.selected .candidate-check {{ background: #4ade80; border-color: #4ade80; color: #000; }}
    .candidate img {{ width: 100%; height: 100px; object-fit: cover; border-radius: 4px;
                      display: block; background: #2a2d3a; }}
    .candidate video {{ width: 100%; height: 100px; object-fit: cover; border-radius: 4px;
                        display: block; background: #000; }}
    .candidate audio {{ width: 100%; margin-top: 6px; }}
    .candidate-meta {{ font-size: 0.72rem; color: #666; margin-top: 6px; }}
    .candidate-source {{ color: #60a5fa; }}
    .ai-btn {{ background: #2a1a0a; border: 1px dashed #fb923c; color: #fb923c;
               padding: 7px 14px; border-radius: 6px; cursor: pointer; font-size: 0.82rem;
               transition: all 0.15s; margin-top: 8px; }}
    .ai-btn:hover {{ background: #3a2010; }}
    .ai-btn.active {{ background: #fb923c; color: #000; font-weight: 600; }}
    .music-section {{ margin-top: 12px; padding-top: 12px; border-top: 1px solid #2a2d3a; }}
    .save-bar {{ position: sticky; bottom: 0; background: #0f1117; padding: 16px 0;
                 border-top: 1px solid #2a2d3a; display: flex; align-items: center; gap: 16px;
                 margin-top: 32px; }}
    .save-btn {{ background: #4ade80; color: #000; border: none; padding: 12px 32px;
                 border-radius: 8px; font-size: 1rem; font-weight: 700; cursor: pointer;
                 transition: all 0.15s; }}
    .save-btn:hover {{ background: #22c55e; }}
    .save-status {{ font-size: 0.9rem; color: #888; }}
    .pipeline-badge {{ background: #1a2a3a; color: #60a5fa; padding: 4px 12px;
                       border-radius: 20px; font-size: 0.8rem; margin-left: auto; }}
    .no-candidates {{ font-size: 0.85rem; color: #555; padding: 12px;
                      border: 1px dashed #333; border-radius: 6px; text-align: center; }}
    .desc-text {{ font-size: 0.82rem; color: #888; margin-bottom: 8px; }}
  </style>
</head>
<body>
  <h1>cut Asset Review — {title}</h1>
  <div class="meta">
    {num_scenes} 个场景 &nbsp;·&nbsp; 总时长 {total_duration}s &nbsp;·&nbsp;
    <span id="pipeline-display">{pipeline_state}</span>
  </div>

  <div id="scenes-container">
    <!-- scenes injected by JS -->
  </div>

  <div class="save-bar">
    <button class="save-btn" onclick="saveReview()">保存审核结果</button>
    <span class="save-status" id="save-status">未保存</span>
    <span class="pipeline-badge" id="pipeline-badge">{pipeline_state}</span>
  </div>

  <script>
  // Embedded script data
  const SCRIPT_DATA = {script_data_json};
  const SCRIPT_PATH = {script_path_json};

  // Working copy of scenes (mutable)
  const scenes = JSON.parse(JSON.stringify(SCRIPT_DATA.scenes));

  function getStatus(status) {{
    const map = {{ approved: 'status-approved', generating: 'status-generating',
                   fetched: 'status-fetched', pending: 'status-pending',
                   candidates_ready: 'status-fetched', ready: 'status-approved' }};
    return map[status] || 'status-pending';
  }}

  function renderCandidate(sceneIdx, type, candIdx, cand, selectedIdx) {{
    const isSelected = selectedIdx === candIdx;
    const isVideo = (cand.type === 'video') || (cand.url && cand.url.match(/\.(mp4|webm|mov)(\?|$)/i));
    const isAudio = (cand.type === 'audio') || (cand.url && cand.url.match(/\.(mp3|ogg|wav|m4a)(\?|$)/i));

    let mediaHtml = '';
    if (isVideo) {{
      const src = cand.local_path || cand.url || '';
      mediaHtml = `<video src="${{src}}" controls preload="none" title="${{cand.url || ''}}"></video>`;
    }} else if (isAudio) {{
      const src = cand.local_path || cand.url || '';
      mediaHtml = `<audio src="${{src}}" controls preload="none"></audio>`;
    }} else {{
      const thumb = cand.thumbnail || cand.local_path || cand.url || '';
      const alt = cand.source || 'candidate';
      mediaHtml = `<img src="${{thumb}}" alt="${{alt}}" onerror="this.style.display='none'">`;
    }}

    const id = `cand-${{type}}-${{sceneIdx}}-${{candIdx}}`;
    return `
      <label class="candidate${{isSelected ? ' selected' : ''}}" id="label-${{id}}"
             onclick="selectCandidate(${{sceneIdx}}, '${{type}}', ${{candIdx}})">
        <input type="radio" name="cand-${{type}}-${{sceneIdx}}" value="${{candIdx}}"
               ${{isSelected ? 'checked' : ''}}>
        <div class="candidate-check">${{isSelected ? '✓' : ''}}</div>
        ${{mediaHtml}}
        <div class="candidate-meta">
          <span class="candidate-source">${{cand.source || 'unknown'}}</span>
          ${{cand.duration ? ` · ${{cand.duration}}s` : ''}}
        </div>
      </label>`;
  }}

  function renderScene(scene, idx) {{
    const vStatus = scene.visual.status || 'pending';
    const vCands = scene.visual.candidates || [];
    const vSelected = scene.visual.selected_candidate;
    const isAiGen = vStatus === 'generating';

    let visualCandHtml = '';
    if (vCands.length > 0) {{
      visualCandHtml = vCands.map((c, ci) =>
        renderCandidate(idx, 'visual', ci, c, vSelected)
      ).join('');
    }} else {{
      visualCandHtml = '<div class="no-candidates">暂无候选素材</div>';
    }}

    // Music section
    const music = scene.audio && scene.audio.music;
    let musicHtml = '';
    if (music) {{
      const mStatus = music.status || 'pending';
      const mCands = music.candidates || [];
      const mSelected = music.selected_candidate;
      const isMusicAiGen = mStatus === 'generating';

      let musicCandHtml = '';
      if (mCands.length > 0) {{
        musicCandHtml = mCands.map((c, ci) =>
          renderCandidate(idx, 'music', ci, c, mSelected)
        ).join('');
      }} else {{
        musicCandHtml = '<div class="no-candidates">暂无音乐候选</div>';
      }}

      musicHtml = `
        <div class="music-section">
          <div class="section-label">背景音乐候选</div>
          <div class="desc-text">${{music.description || ''}}</div>
          <div class="candidates-grid">${{musicCandHtml}}</div>
          <button class="ai-btn${{isMusicAiGen ? ' active' : ''}}" id="ai-music-${{idx}}"
                  onclick="toggleAiGen(${{idx}}, 'music')">
            ${{isMusicAiGen ? '✓ 已标记：需AI生成' : '标记：需AI生成音乐'}}
          </button>
        </div>`;
    }}

    return `
      <div class="scene-card" id="scene-card-${{idx}}">
        <div class="scene-header">
          <span class="scene-id">${{scene.id}}</span>
          <span class="scene-status ${{getStatus(vStatus)}}" id="vstatus-${{idx}}">${{vStatus}}</span>
          <span style="font-size:0.85rem;color:#888;">${{scene.duration}}s</span>
        </div>
        <div class="scene-narration">${{scene.narration}}</div>
        <div class="desc-text">${{scene.visual.description || ''}}</div>
        <div class="section-label">视觉候选素材 (${{scene.visual.type}})</div>
        <div class="candidates-grid">${{visualCandHtml}}</div>
        <button class="ai-btn${{isAiGen ? ' active' : ''}}" id="ai-visual-${{idx}}"
                onclick="toggleAiGen(${{idx}}, 'visual')">
          ${{isAiGen ? '✓ 已标记：需AI生成' : '标记：需AI生成'}}
        </button>
        ${{musicHtml}}
      </div>`;
  }}

  function selectCandidate(sceneIdx, type, candIdx) {{
    if (type === 'visual') {{
      scenes[sceneIdx].visual.selected_candidate = candIdx;
      scenes[sceneIdx].visual.status = 'approved';
      // Clear AI gen flag
      const aiBtn = document.getElementById(`ai-visual-${{sceneIdx}}`);
      if (aiBtn) {{ aiBtn.classList.remove('active'); aiBtn.textContent = '标记：需AI生成'; }}
      // Update status badge
      const badge = document.getElementById(`vstatus-${{sceneIdx}}`);
      if (badge) {{ badge.textContent = 'approved'; badge.className = 'scene-status status-approved'; }}
    }} else if (type === 'music') {{
      if (!scenes[sceneIdx].audio.music) scenes[sceneIdx].audio.music = {{}};
      scenes[sceneIdx].audio.music.selected_candidate = candIdx;
      scenes[sceneIdx].audio.music.status = 'approved';
      const aiBtn = document.getElementById(`ai-music-${{sceneIdx}}`);
      if (aiBtn) {{ aiBtn.classList.remove('active'); aiBtn.textContent = '标记：需AI生成音乐'; }}
    }}

    // Update visual selection UI
    const prefix = `cand-${{type}}-${{sceneIdx}}-`;
    document.querySelectorAll(`[id^="label-${{prefix}}"]`).forEach(el => {{
      const ci = parseInt(el.id.split('-').pop());
      el.classList.toggle('selected', ci === candIdx);
      const check = el.querySelector('.candidate-check');
      if (check) check.textContent = ci === candIdx ? '✓' : '';
    }});

    updateSaveStatus('已修改，未保存');
  }}

  function toggleAiGen(sceneIdx, type) {{
    if (type === 'visual') {{
      const current = scenes[sceneIdx].visual.status;
      const newStatus = current === 'generating' ? 'pending' : 'generating';
      scenes[sceneIdx].visual.status = newStatus;
      if (newStatus === 'generating') scenes[sceneIdx].visual.selected_candidate = null;
      const btn = document.getElementById(`ai-visual-${{sceneIdx}}`);
      if (btn) {{
        btn.classList.toggle('active', newStatus === 'generating');
        btn.textContent = newStatus === 'generating' ? '✓ 已标记：需AI生成' : '标记：需AI生成';
      }}
      const badge = document.getElementById(`vstatus-${{sceneIdx}}`);
      if (badge) {{
        badge.textContent = newStatus;
        badge.className = `scene-status ${{getStatus(newStatus)}}`;
      }}
      // Deselect all candidates
      if (newStatus === 'generating') {{
        document.querySelectorAll(`[id^="label-cand-visual-${{sceneIdx}}-"]`).forEach(el => {{
          el.classList.remove('selected');
          const check = el.querySelector('.candidate-check');
          if (check) check.textContent = '';
        }});
      }}
    }} else if (type === 'music') {{
      if (!scenes[sceneIdx].audio.music) scenes[sceneIdx].audio.music = {{}};
      const current = scenes[sceneIdx].audio.music.status;
      const newStatus = current === 'generating' ? 'pending' : 'generating';
      scenes[sceneIdx].audio.music.status = newStatus;
      if (newStatus === 'generating') scenes[sceneIdx].audio.music.selected_candidate = null;
      const btn = document.getElementById(`ai-music-${{sceneIdx}}`);
      if (btn) {{
        btn.classList.toggle('active', newStatus === 'generating');
        btn.textContent = newStatus === 'generating' ? '✓ 已标记：需AI生成音乐' : '标记：需AI生成音乐';
      }}
    }}
    updateSaveStatus('已修改，未保存');
  }}

  function updateSaveStatus(msg) {{
    const el = document.getElementById('save-status');
    if (el) el.textContent = msg;
  }}

  function saveReview() {{
    // Build updated script data
    const updated = JSON.parse(JSON.stringify(SCRIPT_DATA));
    updated.pipeline_state = 'assets_reviewed';
    updated.scenes = scenes;

    const jsonStr = JSON.stringify(updated, null, 2);

    // Try to write back via fetch (if served via local server)
    // Otherwise, trigger download
    if (SCRIPT_PATH) {{
      fetch('/save_script', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ path: SCRIPT_PATH, data: updated }})
      }}).then(r => {{
        if (r.ok) {{
          updateSaveStatus('✅ 已保存到 ' + SCRIPT_PATH);
          document.getElementById('pipeline-badge').textContent = 'assets_reviewed';
          document.getElementById('pipeline-display').textContent = 'assets_reviewed';
        }} else {{
          downloadScript(jsonStr);
        }}
      }}).catch(() => downloadScript(jsonStr));
    }} else {{
      downloadScript(jsonStr);
    }}
  }}

  function downloadScript(jsonStr) {{
    const blob = new Blob([jsonStr], {{ type: 'application/json' }});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'script.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    updateSaveStatus('✅ 已下载 script.json（请替换原文件）');
    document.getElementById('pipeline-badge').textContent = 'assets_reviewed';
    document.getElementById('pipeline-display').textContent = 'assets_reviewed';
  }}

  // Render all scenes on load
  (function init() {{
    const container = document.getElementById('scenes-container');
    container.innerHTML = scenes.map((s, i) => renderScene(s, i)).join('');
  }})();
  </script>
</body>
</html>
"""


def generate_review(script_path: str, output_html_path: str) -> None:
    """Read script.json and generate an interactive review.html."""
    with open(script_path, 'r', encoding='utf-8') as f:
        script_data = json.load(f)

    title = script_data.get('title', 'Untitled')
    num_scenes = len(script_data.get('scenes', []))
    total_duration = script_data.get('total_duration', 0)
    pipeline_state = script_data.get('pipeline_state', 'assets_fetched')

    # Embed full script data and the script path for write-back
    script_data_json = json.dumps(script_data, ensure_ascii=False)
    script_path_json = json.dumps(os.path.abspath(script_path))

    # Candidates, status, pipeline_state, approved, generating all referenced in template
    html = HTML_TEMPLATE.format(
        title=title,
        num_scenes=num_scenes,
        total_duration=total_duration,
        pipeline_state=pipeline_state,
        script_data_json=script_data_json,
        script_path_json=script_path_json,
    )

    with open(output_html_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'Generated review.html: {output_html_path}')


def main():
    if len(sys.argv) < 3:
        print('Usage: generate_review.py <script_path> <output_html_path>', file=sys.stderr)
        sys.exit(1)

    script_path = sys.argv[1]
    output_html_path = sys.argv[2]

    if not os.path.exists(script_path):
        print(f'Error: script.json not found at {script_path}', file=sys.stderr)
        sys.exit(1)

    generate_review(script_path, output_html_path)


if __name__ == '__main__':
    main()
