#!/usr/bin/env python3
"""
Manim Teaching Video Render Script
Full pipeline: Check code -> Render video

Usage:
    python scripts/render.py [options]

Options:
    -f, --file      Specify script file (Default: script.py)
    -s, --scene     Specify scene class name (Default: MathScene)
    -q, --quality   Render quality: l(ow)/m(edium)/h(igh)/k(4k) (Default: high)
    -p, --preview   Preview after rendering (Default: enabled)
    --no-check      Skip code checking (Not recommended)

Examples:
    python scripts/render.py                    # Render script.py by default
    python scripts/render.py -f my_script.py    # Render specified file
    python scripts/render.py -q k               # Render in 4K quality
"""

import subprocess
import sys
import argparse
from pathlib import Path


class RenderPipeline:
    """Render Pipeline"""

    QUALITY_MAP = {
        'l': '480p15',
        'low': '480p15',
        'm': '720p30',
        'medium': '720p30',
        'h': '1080p60',
        'high': '1080p60',
        'k': '2160p60',
        '4k': '2160p60',
    }

    def __init__(self, script_file='script.py', scene_name='MathScene',
                 quality='high', preview=True, skip_check=False):
        self.script_file = Path(script_file)
        self.scene_name = scene_name
        self.quality = self.QUALITY_MAP.get(quality, '1080p60')
        self.preview = preview
        self.skip_check = skip_check

        # Check script path
        self.script_dir = Path(__file__).parent.parent
        self.check_script = self.script_dir / 'scripts' / 'check.py'

    def run_check(self):
        """Step 1: Run code check"""
        if self.skip_check:
            print("⚠️  Skipping code check (Not recommended)")
            return True

        print("🔍 Step 1/2: Code structure check")
        print("=" * 50)

        if not self.check_script.exists():
            print(f"❌ Check script does not exist: {self.check_script}")
            return False

        try:
            result = subprocess.run(
                [sys.executable, str(self.check_script), str(self.script_file)],
                cwd=self.script_dir,
                capture_output=False
            )
            return result.returncode == 0
        except Exception as e:
            print(f"❌ Check failed: {e}")
            return False

    def run_render(self):
        """Step 2: Run Manim render"""
        print("\n🎬 Step 2/2: Rendering video")
        print("=" * 50)

        if not self.script_file.exists():
            print(f"❌ Script file does not exist: {self.script_file}")
            return False

        # Build manim command
        cmd = ['manim']

        # Quality parameter
        cmd.extend(['-q', self.quality[0]])  # l/m/h/k

        # Preview parameter
        if self.preview:
            cmd.append('-p')

        # Script and scene
        cmd.extend([str(self.script_file), self.scene_name])

        print(f"Executing command: {' '.join(cmd)}")
        print()

        try:
            result = subprocess.run(cmd, cwd=self.script_dir)
            return result.returncode == 0
        except FileNotFoundError:
            print("❌ manim command not found, please ensure it's installed: pip install manim")
            return False
        except Exception as e:
            print(f"❌ Render failed: {e}")
            return False

    def copy_to_root(self):
        """Step 3: Copy video to root directory"""
        print("\n📁 Copying video to root directory")
        print("=" * 50)

        # Find generated video file
        media_dir = self.script_dir / 'media' / 'videos' / self.script_file.stem

        if not media_dir.exists():
            print(f"⚠️  Media directory does not exist: {media_dir}")
            return

        # Search by resolution priority
        possible_paths = [
            media_dir / '2160p60' / f'{self.scene_name}.mp4',
            media_dir / '1920p60' / f'{self.scene_name}.mp4',
            media_dir / '1080p60' / f'{self.scene_name}.mp4',
            media_dir / '720p30' / f'{self.scene_name}.mp4',
            media_dir / '480p15' / f'{self.scene_name}.mp4',
        ]

        video_src = None
        for path in possible_paths:
            if path.exists():
                video_src = path
                break

        if video_src:
            import shutil
            video_dst = self.script_dir / f'{self.scene_name}.mp4'
            try:
                shutil.copy2(video_src, video_dst)
                print(f"✅ Video copied: {video_dst}")
                print(f"   Source file: {video_src}")
            except Exception as e:
                print(f"⚠️  Copy failed: {e}")
        else:
            print("⚠️  Generated video file not found")

    def run(self):
        """Run full pipeline"""
        print("\n" + "=" * 50)
        print("🎬 Manim Teaching Video Render Pipeline")
        print("=" * 50)
        print(f"Script file: {self.script_file}")
        print(f"Scene class name: {self.scene_name}")
        print(f"Render quality: {self.quality}")
        print("=" * 50 + "\n")

        # Step 1: Check
        if not self.run_check():
            print("\n⛔ Code check failed, render terminated.")
            print("   Please fix errors and retry, or use --no-check to skip (Not recommended)")
            return False

        # Step 2: Render
        if not self.run_render():
            print("\n⛔ Render failed.")
            return False

        # Step 3: Copy
        self.copy_to_root()

        print("\n" + "=" * 50)
        print("✅ Render complete!")
        print("=" * 50)

        return True


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Manim Teaching Video Render Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    python scripts/render.py                    # Render script.py by default
    python scripts/render.py -f my_script.py    # Render specified file
    python scripts/render.py -s MyScene         # Specify scene class name
    python scripts/render.py -q k               # Render in 4K quality
    python scripts/render.py --no-check         # Skip check (Not recommended)
        '''
    )

    parser.add_argument(
        '-f', '--file',
        default='script.py',
        help='Script file to render (Default: script.py)'
    )

    parser.add_argument(
        '-s', '--scene',
        default='MathScene',
        help='Scene class name (Default: MathScene)'
    )

    parser.add_argument(
        '-q', '--quality',
        default='high',
        choices=['l', 'low', 'm', 'medium', 'h', 'high', 'k', '4k'],
        help='Render quality: l/low(480p), m/medium(720p), h/high(1080p), k/4k(2160p) (Default: high)'
    )

    parser.add_argument(
        '-p', '--preview',
        action='store_true',
        default=True,
        help='Preview after rendering (Default: enabled)'
    )

    parser.add_argument(
        '--no-preview',
        action='store_true',
        help='Do not preview after rendering'
    )

    parser.add_argument(
        '--no-check',
        action='store_true',
        help='Skip code checking (Not recommended)'
    )

    args = parser.parse_args()

    # Process --no-preview
    preview = not args.no_preview

    # Create pipeline
    pipeline = RenderPipeline(
        script_file=args.file,
        scene_name=args.scene,
        quality=args.quality,
        preview=preview,
        skip_check=args.no_check
    )

    # Run
    success = pipeline.run()

    # Exit code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
