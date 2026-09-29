#!/usr/bin/env python3
"""
Tutor Skill Project Initialization Script

Features:
1. Check dependencies (uv, manim, edge-tts, etc.)
2. Create project directory structure
3. Copy scaffold templates
4. Generate example CSV file

Usage:
    python init.py [project_directory]

Creates the project structure in the current directory by default.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


# ========== Configuration ==========
SKILL_DIR = Path(__file__).parent.resolve()
TEMPLATES_DIR = SKILL_DIR / "templates"
SCRIPTS_DIR = SKILL_DIR / "scripts"

# Dependency check configuration
DEPENDENCIES = {
    "uv": {
        "check": ["uv", "--version"],
        "install_hint": "curl -LsSf https://astral.sh/uv/install.sh | sh",
        "required": True,
    },
    "manim": {
        "check": ["manim", "--version"],
        "install_hint": "uv pip install manim",
        "required": True,
    },
    "edge-tts": {
        "check": ["edge-tts", "--version"],
        "install_hint": "uv pip install edge-tts",
        "required": True,
    },
    "ffmpeg": {
        "check": ["ffmpeg", "-version"],
        "install_hint": "brew install ffmpeg (macOS) or apt install ffmpeg (Linux)",
        "required": False,  # Optional but recommended
    },
}

# Project directory structure
PROJECT_STRUCTURE = {
    "audio": "Audio files directory",
    "media": "Manim render output",
    "assets": "Static assets",
}


# ========== Color Output ==========
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    RESET = "\033[0m"


def ok(msg):
    print(f"{Colors.GREEN}✓{Colors.RESET} {msg}")


def warn(msg):
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {msg}")


def error(msg):
    print(f"{Colors.RED}✗{Colors.RESET} {msg}")


def info(msg):
    print(f"{Colors.BLUE}ℹ{Colors.RESET} {msg}")


# ========== Dependency Check ==========
def check_dependency(name, config):
    """Check a single dependency"""
    try:
        result = subprocess.run(
            config["check"],
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            version = result.stdout.decode().strip().split('\n')[0][:50]
            ok(f"{name}: {version}")
            return True
    except FileNotFoundError:
        pass

    if config["required"]:
        error(f"{name}: Not installed (Required)")
        info(f"  Install: {config['install_hint']}")
    else:
        warn(f"{name}: Not installed (Optional)")
        info(f"  Install: {config['install_hint']}")

    return not config["required"]


def check_all_dependencies():
    """Check all dependencies"""
    print("=" * 50)
    print("Checking Dependencies")
    print("=" * 50)

    all_ok = True
    for name, config in DEPENDENCIES.items():
        if not check_dependency(name, config):
            all_ok = False

    print()
    return all_ok


# ========== Project Initialization ==========
def create_directory_structure(project_dir):
    """Create project directory structure"""
    print("=" * 50)
    print("Creating Project Directories")
    print("=" * 50)

    project_path = Path(project_dir)
    project_path.mkdir(parents=True, exist_ok=True)

    for dirname, description in PROJECT_STRUCTURE.items():
        dirpath = project_path / dirname
        dirpath.mkdir(exist_ok=True)
        ok(f"{dirname}/ - {description}")

    print()


def copy_templates(project_dir):
    """Copy scaffold templates"""
    print("=" * 50)
    print("Copying Template Files")
    print("=" * 50)

    project_path = Path(project_dir)

    # Copy script_scaffold.py
    scaffold_src = TEMPLATES_DIR / "script_scaffold.py"
    scaffold_dst = project_path / "script.py"

    if scaffold_src.exists():
        shutil.copy2(scaffold_src, scaffold_dst)
        ok(f"script.py - Scaffold template (from script_scaffold.py)")
        info("  Hint: Implement the TODO sections based on the storyboard")
    else:
        error(f"Template not found: {scaffold_src}")

    # Copy script_example.py as reference
    example_src = TEMPLATES_DIR / "script_example.py"
    example_dst = project_path / "script_example.py"

    if example_src.exists():
        shutil.copy2(example_src, example_dst)
        ok(f"script_example.py - Full example (for reference)")
    else:
        warn("script_example.py template not found")

    print()


def generate_csv_template(project_dir):
    """Generate example CSV file"""
    print("=" * 50)
    print("Generating Audio List Template")
    print("=" * 50)

    project_path = Path(project_dir)
    csv_path = project_path / "audio_list.csv"

    csv_content = """filename,text
audio_001_intro.wav,"Hello everyone! Today we will learn about the triangle angle sum theorem."
audio_002_draw_triangle.wav,"First, let's draw an arbitrary triangle."
audio_003_mark_angles.wav,"Mark the three interior angles of the triangle."
audio_004_draw_parallel.wav,"Draw a line parallel to the base passing through the top vertex."
audio_005_proof.wav,"Use the properties of parallel lines for the proof."
audio_006_summary.wav,"Summary: The sum of the interior angles of a triangle is 180 degrees."
"""

    if not csv_path.exists():
        csv_path.write_text(csv_content, encoding='utf-8')
        ok(f"audio_list.csv - Audio list template")
        info("  Usage: python {}/scripts/generate_tts.py audio_list.csv ./audio".format(SKILL_DIR))
    else:
        warn("audio_list.csv already exists, skipping")

    print()


def generate_gitignore(project_dir):
    """Generate .gitignore file"""
    project_path = Path(project_dir)
    gitignore_path = project_path / ".gitignore"

    if not gitignore_path.exists():
        content = """# Manim
media/
__pycache__/
*.pyc

# Audio
audio/*.wav
audio/*.mp3
!audio/audio_info.json

# Video
*.mp4
*.mov

# Temp
.DS_Store
*.log
"""
        gitignore_path.write_text(content)
        ok(".gitignore")


# ========== Main Process ==========
def main():
    # Parse arguments
    project_dir = sys.argv[1] if len(sys.argv) > 1 else "."

    print("\n" + "=" * 50)
    print("Tutor Skill - Project Initialization")
    print("=" * 50)
    print(f"Project Directory: {Path(project_dir).resolve()}")
    print(f"Skill Directory: {SKILL_DIR}")
    print()

    # 1. Check dependencies
    if not check_all_dependencies():
        print("=" * 50)
        error("Dependency check failed. Please install required dependencies first.")
        print()
        print("Quick Install:")
        print("  uv pip install manim edge-tts mutagen")
        sys.exit(1)

    # 2. Create directory structure
    create_directory_structure(project_dir)

    # 3. Copy templates
    copy_templates(project_dir)

    # 4. Generate CSV
    generate_csv_template(project_dir)

    # 5. Generate gitignore
    generate_gitignore(project_dir)

    # Done
    print("=" * 50)
    ok("Project initialization complete!")
    print("=" * 50)
    print()
    print("Next steps:")
    print("  1. Edit audio_list.csv to fill in the dialogues")
    print("  2. Generate audio: python {}/scripts/generate_tts.py audio_list.csv ./audio".format(SKILL_DIR))
    print("  3. Edit script.py to implement animations")
    print("  4. Render video: manim -pqh script.py MathScene")
    print()


if __name__ == "__main__":
    main()

