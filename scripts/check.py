#!/usr/bin/env python3
"""
Manim Teaching Video Code Check Script
Verifies whether script.py contains necessary functions and structures

Usage:
    python scripts/check.py [script_file]

Checks script.py by default, or another specified file.
"""

import ast
import sys
import os
from pathlib import Path


class CodeChecker:
    """Code Structure Checker"""

    # Required functions
    REQUIRED_FUNCTIONS = [
        'calculate_geometry',
        'assert_geometry',
        'define_elements',
    ]

    # Recommended functions (warns but does not block)
    RECOMMENDED_FUNCTIONS = [
        'play_scene',
    ]

    # Required classes (inner classes included)
    REQUIRED_CLASSES = [
        'Subtitle',
        'TitleSubtitle',
    ]

    def __init__(self, file_path):
        self.file_path = Path(file_path)
        self.errors = []
        self.warnings = []
        self.tree = None
        self.classes = {}  # class name -> method list
        self.class_method_calls = {}  # class name -> {method name: set(call names)}
        self.scene_classes = set()  # Classes inheriting from Scene

    def parse(self):
        """Parse Python file"""
        if not self.file_path.exists():
            self.errors.append(f"File not found: {self.file_path}")
            return False

        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.tree = ast.parse(content)
            return True
        except SyntaxError as e:
            self.errors.append(f"Syntax error: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Parse failed: {e}")
            return False

    def analyze(self):
        """Analyze code structure"""
        if not self.tree:
            return

        # Iterate top-level definitions
        for node in ast.iter_child_nodes(self.tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                methods = []
                method_calls = {}
                inner_classes = []
                is_scene_class = False

                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == 'Scene':
                        is_scene_class = True
                    elif isinstance(base, ast.Attribute) and base.attr == 'Scene':
                        is_scene_class = True
                if is_scene_class:
                    self.scene_classes.add(class_name)

                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        methods.append(item.name)
                        calls = set()
                        for sub in ast.walk(item):
                            if isinstance(sub, ast.Call):
                                if isinstance(sub.func, ast.Attribute):
                                    calls.add(sub.func.attr)
                                elif isinstance(sub.func, ast.Name):
                                    calls.add(sub.func.id)
                        method_calls[item.name] = calls
                    elif isinstance(item, ast.ClassDef):
                        inner_classes.append(item.name)
                        # Record inner class methods as well
                        inner_methods = [n.name for n in item.body
                                        if isinstance(n, ast.FunctionDef)]
                        self.classes[f"{class_name}.{item.name}"] = inner_methods

                self.classes[class_name] = methods
                self.class_method_calls[class_name] = method_calls

    def check_required_functions(self):
        """Check if required functions exist"""
        all_methods = set()
        for class_name, methods in self.classes.items():
            all_methods.update(methods)

        for func_name in self.REQUIRED_FUNCTIONS:
            if func_name not in all_methods:
                self.errors.append(
                    f"Missing required function: {func_name}()\n"
                    f"  Please implement this method in MathScene class\n"
                    f"  Purpose: {self._get_function_description(func_name)}"
                )

    def check_recommended_functions(self):
        """Check for recommended functions"""
        all_methods = set()
        for class_name, methods in self.classes.items():
            all_methods.update(methods)

        for func_name in self.RECOMMENDED_FUNCTIONS:
            if func_name not in all_methods:
                self.warnings.append(
                    f"Missing recommended function: {func_name}()\n"
                    f"  Recommended to implement for better animation control per scene"
                )

    def check_subtitle_classes(self):
        """Check if subtitle classes exist"""
        # Check if Subtitle and TitleSubtitle are defined as inner classes
        found_subtitle = False
        found_title = False

        for class_name in self.classes.keys():
            if '.' in class_name:
                outer, inner = class_name.split('.')
                if inner == 'Subtitle':
                    found_subtitle = True
                if inner == 'TitleSubtitle':
                    found_title = True

        if not found_subtitle:
            self.warnings.append(
                "Subtitle class not found\n"
                "  Recommendation: Copy Subtitle class definition from templates/script_scaffold.py\n"
                "  Purpose: Avoid text leftover issues due to forgotten render/exit"
            )

        if not found_title:
            self.warnings.append(
                "TitleSubtitle class not found\n"
                "  Recommendation: Copy TitleSubtitle class definition from templates/script_scaffold.py"
            )

    def check_scene_class(self):
        """Check if there is a class inheriting from Scene"""
        found_scene = False
        for node in ast.iter_child_nodes(self.tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == 'Scene':
                        found_scene = True
                        break
                    elif isinstance(base, ast.Attribute):
                        if base.attr == 'Scene':
                            found_scene = True
                            break

        if not found_scene:
            self.errors.append(
                "Class inheriting from Scene not found\n"
                "  There must be at least one class inheriting from Scene, e.g.: class MathScene(Scene):"
            )

    def check_add_sound(self):
        """Check for add_sound calls (audio integration)"""
        has_add_sound = False

        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == 'add_sound':
                        has_add_sound = True
                        break
                elif isinstance(node.func, ast.Name):
                    if node.func.id == 'add_sound':
                        has_add_sound = True
                        break

        if not has_add_sound:
            self.warnings.append(
                "No add_sound() call detected\n"
                "  Reminder: Corresponding audio file should be added for each scene animation\n"
                "  Example: self.add_sound('audio/audio_001_intro.wav')"
            )

    def check_audio_timeline_guards(self):
        """
        Check audio timeline guards to avoid audio overlap:
        - When scene splits exist, should use start_scene_with_audio / end_scene_with_audio
        - If directly using add_sound, should also have explicit wait_for_audio or end_scene_with_audio guard
        """
        for class_name in self.scene_classes:
            methods = self.class_method_calls.get(class_name, {})
            if not methods:
                continue

            method_names = set(methods.keys())
            all_calls = set()
            for calls in methods.values():
                all_calls.update(calls)

            has_play_scene_methods = any(name.startswith("play_scene_") for name in method_names)
            has_start_guard = "start_scene_with_audio" in all_calls
            has_end_guard = ("end_scene_with_audio" in all_calls) or ("wait_for_audio" in all_calls)
            has_add_sound = "add_sound" in all_calls

            if has_play_scene_methods and not has_start_guard:
                self.warnings.append(
                    f"{class_name} detected play_scene_* split methods, but start_scene_with_audio() not used\n"
                    "  Recommendation: Uniformly start each scene from start_scene_with_audio() in construct()"
                )

            if has_play_scene_methods and not has_end_guard:
                self.errors.append(
                    f"{class_name} detected split structure, but end_scene_with_audio()/wait_for_audio() wrap up not found\n"
                    "  Risk: Next scene might start early, causing previous and next audio to overlap"
                )

            if has_add_sound and not has_end_guard:
                self.errors.append(
                    f"{class_name} used add_sound(), but missing audio wrap up wait mechanism\n"
                    "  Recommendation: Use end_scene_with_audio(expected_duration) or wait_for_audio()"
                )

    def check_sync_methods(self):
        """
        Check if sync alignment methods (wait_for_narration / wait_until_scene_time) are used.
        If there are play_scene_* methods but no sync methods used, give recommendation.
        """
        for class_name in self.scene_classes:
            methods = self.class_method_calls.get(class_name, {})
            if not methods:
                continue

            play_scene_methods = {
                name: calls for name, calls in methods.items()
                if name.startswith("play_scene_")
            }

            if not play_scene_methods:
                continue

            has_any_sync = False
            for name, calls in play_scene_methods.items():
                if "wait_for_narration" in calls or "wait_until_scene_time" in calls:
                    has_any_sync = True
                    break

            if not has_any_sync:
                self.warnings.append(
                    f"play_scene_* methods in {class_name} do not use wait_for_narration() or wait_until_scene_time()\n"
                    "  Recommendation: Use sync methods to precisely align voiceover and visuals, instead of self.wait(duration - N) manual estimation\n"
                    "  Example: self.wait_for_narration('incircle') will wait until voiceover reaches that keyword"
                )

    def check_duration_minus_antipattern(self):
        """
        Detect duration - N anti-pattern: used in play_scene_*
        self.wait(max(..., duration - N)) manual fallback.
        """
        if not self.file_path.exists():
            return

        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                source = f.read()
        except Exception:
            return

        import re
        pattern = re.compile(
            r'self\.wait\s*\(\s*max\s*\(.+?duration\s*-',
            re.DOTALL
        )
        matches = pattern.findall(source)
        if matches:
            self.warnings.append(
                f"Detected {len(matches)} occurrences of self.wait(max(..., duration - N)) anti-pattern\n"
                "  Issue: Manual remaining duration calculation is error-prone when adding/removing animations\n"
                "  Recommendation: Remove manual fallback, switch to end_scene_with_audio() auto-pad\n"
                "  Reference: play_scene_X() should focus on visual actions, no manual fallback needed"
            )

    def _get_function_description(self, func_name):
        """Get function description"""
        descriptions = {
            'calculate_geometry': 'Calculate coordinates and properties for all geometric elements (points, lines, circles)',
            'assert_geometry': 'Verify correctness of geometry calculation and canvas bounds',
            'define_elements': 'Define Manim graphical objects (points, lines, circles, etc.)',
        }
        return descriptions.get(func_name, 'Unknown function')

    def run(self):
        """Run all checks"""
        print(f"🔍 Checking file: {self.file_path}")
        print("=" * 50)

        # Parse
        if not self.parse():
            return False

        # Analyze
        self.analyze()

        # Various checks
        self.check_scene_class()
        self.check_required_functions()
        self.check_recommended_functions()
        self.check_subtitle_classes()
        self.check_add_sound()
        self.check_audio_timeline_guards()
        self.check_sync_methods()
        self.check_duration_minus_antipattern()

        # Output results
        return self.report()

    def report(self):
        """Output check report"""
        success = len(self.errors) == 0

        # Errors
        if self.errors:
            print("\n❌ Errors (Must fix):")
            for i, error in enumerate(self.errors, 1):
                print(f"\n  {i}. {error}")

        # Warnings
        if self.warnings:
            print("\n⚠️  Warnings (Recommended to fix):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"\n  {i}. {warning}")

        # Success message
        if success and not self.warnings:
            print("\n✅ All checks passed! Ready to start rendering.")
        elif success:
            print("\n✅ Required checks passed, but there are warnings recommended to be handled.")

        print("\n" + "=" * 50)

        if success:
            print("🎬 Next step: Run render command")
            print(f"   manim -pqh {self.file_path} MathScene")
        else:
            print("⛔ Check failed, please fix errors and retry.")

        return success


def main():
    """Main function"""
    # Get file to check
    if len(sys.argv) > 1:
        script_file = sys.argv[1]
    else:
        script_file = "script.py"

    # Check file path
    script_path = Path(script_file)

    # Run check
    checker = CodeChecker(script_path)
    success = checker.run()

    # Return exit code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
