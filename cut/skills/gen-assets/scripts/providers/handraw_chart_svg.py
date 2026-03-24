#!/usr/bin/env python3
"""handraw_chart_svg.py — Chart handraw provider: LLM → SVG (rough style) → PNG via cairosvg."""
import os
import re
import textwrap


# Fallback SVG template for when no LLM key is available
_FALLBACK_SVG_TEMPLATE = '''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="500" style="background:#fff">
  <title>{title}</title>
  <!-- Axes -->
  <line x1="80" y1="420" x2="720" y2="420" stroke="#333" stroke-width="2.5" stroke-linecap="round"/>
  <line x1="80" y1="420" x2="80" y2="60" stroke="#333" stroke-width="2.5" stroke-linecap="round"/>
  <!-- Y-axis label -->
  <text x="30" y="250" transform="rotate(-90,30,250)" font-family="Georgia,serif" font-size="14" fill="#444" text-anchor="middle">数量</text>
  <!-- X-axis label -->
  <text x="400" y="470" font-family="Georgia,serif" font-size="14" fill="#444" text-anchor="middle">年份</text>
  <!-- Title -->
  <text x="400" y="40" font-family="Georgia,serif" font-size="18" fill="#222" text-anchor="middle" font-weight="bold">{title}</text>
  <!-- Data line (hand-drawn style with slight roughness) -->
  <polyline
    points="130,180 210,210 290,250 370,295 450,340 530,370 610,390 690,405"
    fill="none" stroke="#2255aa" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"
    stroke-dasharray="0"/>
  <!-- Data points -->
  <circle cx="130" cy="180" r="5" fill="#2255aa"/>
  <circle cx="210" cy="210" r="5" fill="#2255aa"/>
  <circle cx="290" cy="250" r="5" fill="#2255aa"/>
  <circle cx="370" cy="295" r="5" fill="#2255aa"/>
  <circle cx="450" cy="340" r="5" fill="#2255aa"/>
  <circle cx="530" cy="370" r="5" fill="#2255aa"/>
  <circle cx="610" cy="390" r="5" fill="#2255aa"/>
  <circle cx="690" cy="405" r="5" fill="#2255aa"/>
  <!-- X tick labels -->
  <text x="130" y="440" font-family="Georgia,serif" font-size="12" fill="#555" text-anchor="middle">2017</text>
  <text x="210" y="440" font-family="Georgia,serif" font-size="12" fill="#555" text-anchor="middle">2018</text>
  <text x="290" y="440" font-family="Georgia,serif" font-size="12" fill="#555" text-anchor="middle">2019</text>
  <text x="370" y="440" font-family="Georgia,serif" font-size="12" fill="#555" text-anchor="middle">2020</text>
  <text x="450" y="440" font-family="Georgia,serif" font-size="12" fill="#555" text-anchor="middle">2021</text>
  <text x="530" y="440" font-family="Georgia,serif" font-size="12" fill="#555" text-anchor="middle">2022</text>
  <text x="610" y="440" font-family="Georgia,serif" font-size="12" fill="#555" text-anchor="middle">2023</text>
  <text x="690" y="440" font-family="Georgia,serif" font-size="12" fill="#555" text-anchor="middle">2024</text>
</svg>'''


def _generate_svg_with_llm(subject: str) -> str:
    """Call Claude/OpenAI to generate an SVG chart for the subject."""
    anthropic_key = os.environ.get('ANTHROPIC_API_KEY', '')
    openai_key = os.environ.get('OPENAI_API_KEY', '')

    system_prompt = textwrap.dedent("""\
        You are an SVG chart generator. Generate a clean, hand-drawn style SVG chart
        for the given subject. Requirements:
        - Pure SVG, no external dependencies, no JavaScript
        - Use rough/sketchy line style (slight irregularity, hand-drawn feel)
        - Include: title, labeled axes (x and y), data line/bars, data points
        - Use font-family: Georgia, serif for text
        - Width: 800, Height: 500, white background
        - Colors: dark strokes (#333), blue data lines (#2255aa)
        - Return ONLY the SVG XML, starting with <svg and ending with </svg>
        - No markdown code blocks, no explanation
    """)
    user_prompt = f'Generate an SVG chart for: {subject}'

    if anthropic_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            msg = client.messages.create(
                model='claude-3-5-haiku-20241022',
                max_tokens=2048,
                system=system_prompt,
                messages=[{'role': 'user', 'content': user_prompt}],
            )
            return msg.content[0].text.strip()
        except Exception:
            pass

    if openai_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            resp = client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt},
                ],
                max_tokens=2048,
            )
            return resp.choices[0].message.content.strip()
        except Exception:
            pass

    return None


def _extract_svg(text: str) -> str:
    """Extract SVG content from LLM response (handles code blocks)."""
    # Strip markdown code fences
    text = re.sub(r'```[a-z]*\n?', '', text)
    text = text.replace('```', '').strip()
    # Find <svg...>...</svg>
    match = re.search(r'<svg[\s\S]*?</svg>', text, re.IGNORECASE)
    if match:
        return match.group(0)
    return text


class HandrawChartSVGProvider:
    """Generates hand-drawn style charts via LLM → SVG → cairosvg → PNG."""

    def __init__(self, dpi: int = 150, **kwargs):
        self.dpi = dpi

    def generate(self, subject: str, output_path: str, **kwargs) -> str:
        """Generate a chart PNG from a subject description."""
        try:
            import cairosvg
        except ImportError:
            raise ImportError(
                'cairosvg not installed. Run: pip install cairosvg'
            )

        # Try LLM-generated SVG first
        svg_text = _generate_svg_with_llm(subject)
        if svg_text:
            svg_content = _extract_svg(svg_text)
        else:
            # Fallback: use built-in template
            svg_content = _FALLBACK_SVG_TEMPLATE.format(title=subject)

        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        cairosvg.svg2png(
            bytestring=svg_content.encode('utf-8'),
            write_to=output_path,
            dpi=self.dpi,
        )
        return output_path


# Module-level convenience function
def generate(subject: str, output_path: str, **kwargs) -> str:
    """Generate a chart PNG. Convenience wrapper for HandrawChartSVGProvider."""
    provider = HandrawChartSVGProvider(**kwargs)
    return provider.generate(subject, output_path)
