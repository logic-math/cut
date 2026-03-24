#!/usr/bin/env python3
"""
check_env.py — Environment dependency checker for the cut skill pack.

Checks:
- Python version (3.11+)
- FFmpeg (system dependency)
- cairosvg (for handraw chart SVG→PNG conversion)
- PyYAML (for config parsing)
- edge-tts (default TTS provider)
- Other optional skill dependencies

Usage:
    python cut/scripts/check_env.py

Also provides workspace creation utility:
    python cut/scripts/check_env.py --workspace-base <dir> --project <name>
"""

import sys
import shutil
import subprocess
import os
import importlib
import argparse
from datetime import datetime


def check_python_version():
    major, minor = sys.version_info.major, sys.version_info.minor
    if major < 3 or (major == 3 and minor < 11):
        print(f"✗ Python {major}.{minor} — requires Python 3.11+")
        print(f"  → Install: https://www.python.org/downloads/")
        return False
    print(f"✓ Python {major}.{minor} OK")
    return True


def check_ffmpeg():
    if shutil.which("ffmpeg") is not None:
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True, text=True
            )
            version_line = result.stdout.split("\n")[0] if result.stdout else "unknown"
            print(f"✓ FFmpeg OK ({version_line})")
        except Exception:
            print("✓ FFmpeg OK")
        return True
    else:
        print("✗ FFmpeg not found")
        print("  → brew install ffmpeg")
        return False


def check_python_package(package_name, import_name=None, pip_name=None):
    if import_name is None:
        import_name = package_name
    if pip_name is None:
        pip_name = package_name
    try:
        mod = importlib.import_module(import_name)
        version = getattr(mod, "__version__", "unknown")
        print(f"✓ {package_name} OK (version: {version})")
        return True
    except ImportError:
        print(f"✗ {package_name} not found")
        print(f"  → pip install {pip_name}")
        return False


def create_workspace(base_dir, project_name):
    """Create a timestamped workspace directory for a project run."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    workspace_path = os.path.join(base_dir, project_name, timestamp)
    os.makedirs(workspace_path, exist_ok=True)
    # Create standard subdirectories
    for subdir in ["assets/narration", "assets/video", "assets/image", "assets/music", "output"]:
        os.makedirs(os.path.join(workspace_path, subdir), exist_ok=True)
    print(f"✓ Workspace created: {workspace_path}")
    return workspace_path


def main():
    parser = argparse.ArgumentParser(description="cut environment checker and workspace utility")
    parser.add_argument("--workspace-base", default=None, help="Base directory for workspace creation")
    parser.add_argument("--project", default=None, help="Project name for workspace creation")
    args = parser.parse_args()

    # Workspace creation mode
    if args.workspace_base and args.project:
        create_workspace(args.workspace_base, args.project)
        return

    print("=" * 50)
    print("cut — Environment Check")
    print("=" * 50)

    all_ok = True

    print("\n[System Dependencies]")
    if not check_python_version():
        all_ok = False
    if not check_ffmpeg():
        all_ok = False

    print("\n[Core Python Packages]")
    core_packages = [
        ("PyYAML", "yaml", "PyYAML"),
        ("cairosvg", "cairosvg", "cairosvg"),
    ]
    for pkg, imp, pip in core_packages:
        if not check_python_package(pkg, imp, pip):
            all_ok = False

    print("\n[TTS Packages]")
    tts_packages = [
        ("edge-tts", "edge_tts", "edge-tts"),
    ]
    for pkg, imp, pip in tts_packages:
        if not check_python_package(pkg, imp, pip):
            all_ok = False

    print("\n[Optional Packages]")
    optional_packages = [
        ("Pillow", "PIL", "Pillow"),
        ("requests", "requests", "requests"),
        ("openai", "openai", "openai"),
    ]
    for pkg, imp, pip in optional_packages:
        # Optional packages: warn but don't fail overall check
        check_python_package(pkg, imp, pip)

    print("\n" + "=" * 50)
    if all_ok:
        print("✓ All required dependencies are satisfied.")
    else:
        print("✗ Some required dependencies are missing. Install them and re-run.")
        sys.exit(1)


if __name__ == "__main__":
    main()
