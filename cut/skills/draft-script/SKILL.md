---
name: draft-script
description: Convert a text lecture/script into a structured audio-visual script in JSON format, following the cut script schema.
trigger: Use when you need to convert a text script into a structured JSON script for video production.
---

# draft-script

Converts a plain-text lecture or script into a structured JSON audio-visual script following the cut schema.

## Usage

```bash
python cut/skills/draft-script/scripts/draft_script.py --input lecture.txt --output workspace/{project}/{timestamp}/script.json
```
