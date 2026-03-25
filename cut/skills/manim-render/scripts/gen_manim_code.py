#!/usr/bin/env python3
"""gen_manim_code.py — 将 script.json 转换为 Manim CE Python 代码。

由 Claude 直接生成每个场景的 Manim 动画代码（不调用外部 LLM API），
利用 script.json 中的 narration、visual.description、visual.type 等字段
生成对应的 Manim 场景类。

Usage:
    python3 gen_manim_code.py \
        --script path/to/script.json \
        --output path/to/output.py \
        --config path/to/cut-config.yaml
"""

import argparse
import json
import os
import sys
from pathlib import Path


def load_config(config_path: str) -> dict:
    try:
        import yaml
        with open(config_path) as f:
            return yaml.safe_load(f)
    except Exception:
        return {}


def get_manim_config(config: dict) -> dict:
    return config.get("manim", {
        "background_color": "#0D1117",
        "font": "STHeiti",
        "accent_color": "#58A6FF",
        "code_color": "#00FF41",
        "warn_color": "#F0883E",
    })


def get_tts_config(config: dict) -> dict:
    return config.get("tts", {"provider": "edge_tts", "voice": "zh-CN-YunxiNeural"})


def scene_class_name(scene_id: str) -> str:
    """scene_01 → Scene01"""
    parts = scene_id.split("_")
    return "".join(p.capitalize() for p in parts)


def escape_text(text: str) -> str:
    """Escape quotes for Python string literals."""
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def generate_scene_code(scene: dict, manim_cfg: dict, tts_cfg: dict, scene_idx: int, total: int) -> str:
    """Generate Manim Python code for a single scene."""
    sid = scene.get("id", f"scene_{scene_idx:02d}")
    class_name = scene_class_name(sid)
    narration = escape_text(scene.get("narration", ""))
    subtitle = escape_text(scene.get("subtitle", scene.get("narration", "")[:30]))
    visual = scene.get("visual", {})
    vtype = visual.get("type", "image")
    description = visual.get("description", "")

    bg = manim_cfg.get("background_color", "#0D1117")
    font = manim_cfg.get("font", "STHeiti")
    accent = manim_cfg.get("accent_color", "#58A6FF")
    code_color = manim_cfg.get("code_color", "#00FF41")
    warn_color = manim_cfg.get("warn_color", "#F0883E")

    tts_provider = tts_cfg.get("provider", "edge_tts")
    tts_voice = tts_cfg.get("voice", "zh-CN-YunxiNeural")

    # TTS service setup
    if tts_provider == "edge_tts":
        tts_import = "from manim_voiceover.services.edge import EdgeTTSService"
        tts_init = f'self.set_speech_service(EdgeTTSService(voice="{tts_voice}"))'
    elif tts_provider == "openai":
        openai_voice = tts_cfg.get("openai_voice", "alloy")
        tts_import = "from manim_voiceover.services.openai import OpenAITTSService"
        tts_init = f'self.set_speech_service(OpenAITTSService(voice="{openai_voice}"))'
    elif tts_provider == "gtts":
        tts_import = "from manim_voiceover.services.gtts import GTTSService"
        tts_init = 'self.set_speech_service(GTTSService(lang="zh-TW"))'
    else:
        tts_import = "from manim_voiceover.services.gtts import GTTSService"
        tts_init = 'self.set_speech_service(GTTSService(lang="zh-TW"))'

    # Generate visual body based on type
    visual_body = _generate_visual_body(
        vtype, description, scene, font, accent, code_color, warn_color
    )

    code = f'''
class {class_name}(VoiceoverScene):
    """场景 {scene_idx}/{total}: {subtitle[:40]}"""
    def construct(self):
        {tts_init}
        self.camera.background_color = "{bg}"

{visual_body}
        with self.voiceover(text="{narration}") as tracker:
            self.play(
                AnimationGroup(*self._get_animations(), lag_ratio=0.15),
                run_time=min(tracker.duration, {scene.get("duration", 10)} * 0.9)
            )
            self.wait(tracker.duration - min(tracker.duration, {scene.get("duration", 10)} * 0.9))

        self.wait(0.5)
        self.play(FadeOut(self._all_objects()), run_time=0.8)

    def _get_animations(self):
        return [anim for anim in self._anims if anim is not None]

    def _all_objects(self):
        return self._mobjects_group
'''
    return code


def _generate_visual_body(vtype: str, description: str, scene: dict,
                           font: str, accent: str, code_color: str, warn_color: str) -> str:
    """Generate the visual setup body for a scene based on its type."""
    subtitle = scene.get("subtitle", "")
    narration_preview = scene.get("narration", "")[:60]

    if vtype in ("handraw_chart",):
        return _gen_chart_body(description, subtitle, font, accent, code_color, warn_color)
    elif vtype in ("handraw_illustration",):
        return _gen_illustration_body(description, subtitle, font, accent)
    elif vtype == "video":
        return _gen_video_body(description, subtitle, font, accent, code_color)
    else:
        # image or default
        return _gen_text_body(subtitle, narration_preview, font, accent, code_color, warn_color)


def _gen_text_body(subtitle: str, narration: str, font: str, accent: str,
                   code_color: str, warn_color: str) -> str:
    """Default: title + subtitle text layout."""
    esc_subtitle = escape_text(subtitle)
    esc_narration = escape_text(narration)
    return f'''        # ── Text Layout ──
        title = Text("{esc_subtitle}", font="{font}", font_size=42, color="{accent}")
        title.move_to(UP * 0.5)

        body = Text(
            "{esc_narration}...",
            font="{font}", font_size=24, color=WHITE
        )
        body.next_to(title, DOWN, buff=0.5)
        body.width = min(body.width, 11)

        self._mobjects_group = VGroup(title, body)
        self._anims = [Write(title), FadeIn(body, shift=UP * 0.2)]
'''


def _gen_chart_body(description: str, subtitle: str, font: str,
                    accent: str, code_color: str, warn_color: str) -> str:
    """Chart scene: title + placeholder chart area."""
    esc_subtitle = escape_text(subtitle)
    esc_desc = escape_text(description[:80])
    return f'''        # ── Chart Layout ──
        title = Text("{esc_subtitle}", font="{font}", font_size=36, color=WHITE)
        title.to_edge(UP, buff=0.5)

        # Chart area — Claude will fill in actual chart objects here
        chart_rect = RoundedRectangle(
            width=10, height=5, corner_radius=0.2,
            fill_color="{accent}", fill_opacity=0.08,
            stroke_color="{accent}", stroke_width=1.5
        )
        chart_rect.move_to(DOWN * 0.3)

        chart_label = Text(
            "{esc_desc}",
            font="{font}", font_size=18, color=GRAY
        )
        chart_label.move_to(chart_rect)
        chart_label.width = min(chart_label.width, 9)

        self._mobjects_group = VGroup(title, chart_rect, chart_label)
        self._anims = [Write(title), Create(chart_rect), FadeIn(chart_label)]
'''


def _gen_illustration_body(description: str, subtitle: str, font: str, accent: str) -> str:
    """Illustration scene: title + description text."""
    esc_subtitle = escape_text(subtitle)
    esc_desc = escape_text(description[:80])
    return f'''        # ── Illustration Layout ──
        title = Text("{esc_subtitle}", font="{font}", font_size=36, color=WHITE)
        title.to_edge(UP, buff=0.5)

        desc = Text(
            "{esc_desc}",
            font="{font}", font_size=22, color=GRAY
        )
        desc.move_to(ORIGIN)
        desc.width = min(desc.width, 10)

        self._mobjects_group = VGroup(title, desc)
        self._anims = [Write(title), FadeIn(desc)]
'''


def _gen_video_body(description: str, subtitle: str, font: str,
                    accent: str, code_color: str) -> str:
    """Video scene: title + description."""
    esc_subtitle = escape_text(subtitle)
    esc_desc = escape_text(description[:80])
    return f'''        # ── Video/Image Background Layout ──
        title = Text("{esc_subtitle}", font="{font}", font_size=40, color="{accent}")
        title.to_edge(UP, buff=0.5)

        desc = Text(
            "{esc_desc}",
            font="{font}", font_size=22, color=WHITE
        )
        desc.move_to(ORIGIN)
        desc.width = min(desc.width, 10)

        self._mobjects_group = VGroup(title, desc)
        self._anims = [Write(title), FadeIn(desc, shift=UP * 0.2)]
'''


def generate_manim_file(script: dict, config: dict, output_path: str) -> None:
    """Generate complete Manim Python file from script.json."""
    manim_cfg = get_manim_config(config)
    tts_cfg = get_tts_config(config)
    scenes = script.get("scenes", [])
    title = script.get("title", "Video")

    tts_provider = tts_cfg.get("provider", "edge_tts")
    tts_voice = tts_cfg.get("voice", "zh-CN-YunxiNeural")

    if tts_provider == "edge_tts":
        tts_import_line = "from manim_voiceover.services.edge import EdgeTTSService"
    elif tts_provider == "openai":
        tts_import_line = "from manim_voiceover.services.openai import OpenAITTSService"
    else:
        tts_import_line = "from manim_voiceover.services.gtts import GTTSService"

    # Build scene class names list for __all__
    class_names = [scene_class_name(s.get("id", f"scene_{i:02d}")) for i, s in enumerate(scenes, 1)]

    header = f'''#!/usr/bin/env python3
"""
{title}
Auto-generated Manim CE code by cut skill.

Render all scenes:
    for scene in {class_names}; do
        ~/manim-env/bin/manim -qh {Path(output_path).name} $scene
    done

Render single scene (preview):
    ~/manim-env/bin/manim -ql {Path(output_path).name} {class_names[0] if class_names else "Scene01"}
"""

from manim import *
from manim_voiceover import VoiceoverScene
{tts_import_line}

# ── Scene list (for batch rendering) ──
SCENES = {class_names!r}
'''

    scene_codes = []
    for i, scene in enumerate(scenes, 1):
        scene_codes.append(generate_scene_code(scene, manim_cfg, tts_cfg, i, len(scenes)))

    full_code = header + "\n".join(scene_codes)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_code)

    print(f"Generated {len(scenes)} scene classes → {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate Manim code from script.json")
    parser.add_argument("--script", required=True, help="Path to script.json")
    parser.add_argument("--output", required=True, help="Output .py file path")
    parser.add_argument("--config", default="", help="Path to cut-config.yaml")
    args = parser.parse_args()

    with open(args.script, encoding="utf-8") as f:
        script = json.load(f)

    config = {}
    if args.config and os.path.exists(args.config):
        config = load_config(args.config)
    else:
        # Try to find config relative to skill dir
        skill_dir = Path(__file__).parent.parent.parent.parent
        config_path = skill_dir / "cut-config.yaml"
        if config_path.exists():
            config = load_config(str(config_path))

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    generate_manim_file(script, config, args.output)


if __name__ == "__main__":
    main()
