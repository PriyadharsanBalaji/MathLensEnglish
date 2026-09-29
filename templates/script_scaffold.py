"""
Math Video Scene Scaffold

Generate complete animation based on storyboard and audio info

Usage:
1. Copy this file as script.py
2. Implement the TODO sections based on the math problem
3. Run: manim -pqh script.py MathScene

Troubleshooting:
- Rendering hangs: Usually an audio issue, try disabling add_scene_audio
- deepcopy error: Do not store self references in Mobjects
- Video not generated: Check if copy_video_to_root path is correct
"""

from manim import *
import json
import os


class MathScene(Scene):
    """
    Math Teaching Video Scene

    Core Principles:
    1. Math First - Build the correct mathematical model first
    2. Audio-Visual Sync - Use wait_for_narration() to align highlights with voiceover
    3. Highlight Mapping - Highlight whatever the voiceover mentions
    4. Minimal Validation - assert_geometry only verifies key facts and canvas bounds
    """

    # ========== 1. Config Parameters ==========
    config.pixel_width = 1920
    config.pixel_height = 1080
    config.frame_rate = 60

    COLORS = {
        'background': '#1a1a2e',
        'primary': '#4ecca3',
        'secondary': '#e94560',
        'highlight': '#ffc107',
        'text': '#ffffff',
        'text_secondary': '#aaaaaa',
        'grid': '#2a2a4e',
        'axis': '#444466',
    }

    # ========== 2. Scene Info Array (Read from storyboard) ==========
    SCENES = [
        # (Scene number, Scene name, Audio filename, Duration in seconds)
        # Duration read from audio/audio_info.json
        # TODO: Fill in based on storyboard
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.audio_dir = "audio"
        self.audio_info_file = os.path.join(self.audio_dir, "audio_info.json")
        self._current_scene_num = None
        self._current_scene_name = ""
        self._scene_start_time = 0.0
        self._audio_safety_margin = 0.2
        self._audio_data = self._load_audio_data()
        self._sync_points = {}  # {scene_num: [{idx, text, time}, ...]}

    # ========== 3. Audio Management ==========
    def _load_audio_data(self):
        """Load audio duration and sync points from audio_info.json"""
        if not os.path.exists(self.audio_info_file):
            return {}

        try:
            with open(self.audio_info_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load audio info: {e}")
            return {}

        timings = {}
        for item in data.get('files', []):
            scene_num = item.get('scene')
            duration = item.get('duration')
            if scene_num and duration:
                timings[scene_num] = duration

            sp = item.get('sync_points', [])
            if scene_num and sp:
                self._sync_points[scene_num] = sp

        for i, (scene_num, name, audio_file, _) in enumerate(self.SCENES):
            if scene_num in timings:
                self.SCENES[i] = (scene_num, name, audio_file, timings[scene_num])

        return timings

    def add_scene_audio(self, scene_num, play_audio=True):
        """Add audio for the specified scene"""
        for sn, name, audio_file, duration in self.SCENES:
            if sn == scene_num:
                audio_path = os.path.join(self.audio_dir, audio_file)
                if os.path.exists(audio_path):
                    if play_audio:
                        self.add_sound(audio_path)
                    return duration
                else:
                    print(f"Warning: Audio file not found: {audio_path}")
                    return 0
        return 0

    def start_scene_with_audio(self, scene_num):
        """
        Start a scene and play its audio (anti-overlap entry point)

        Returns: float - The audio duration for the scene (seconds)
        """
        self._current_scene_num = scene_num
        self._scene_start_time = self.time

        for sn, name, _, duration in self.SCENES:
            if sn == scene_num:
                self._current_scene_name = name
                expected = float(duration or 0)
                break
        else:
            self._current_scene_name = f"Scene {scene_num}"
            expected = 0.0

        self.add_scene_audio(scene_num, play_audio=True)
        print(
            f"\n▶ Scene {scene_num}: {self._current_scene_name} | "
            f"audio={expected:.2f}s | t={self._scene_start_time:.2f}s"
        )
        return expected

    def end_scene_with_audio(self, expected_duration=None, safety_margin=None):
        """End a scene and pad wait time, ensuring no early jump to next scene causing overlap."""
        if expected_duration is None:
            expected_duration = 0.0
        if safety_margin is None:
            safety_margin = self._audio_safety_margin

        elapsed = self.time - self._scene_start_time
        target = max(0.0, float(expected_duration)) + max(0.0, float(safety_margin))
        remaining = target - elapsed

        if remaining > 1e-3:
            self.wait(remaining)
            elapsed = self.time - self._scene_start_time

        if elapsed + 1e-3 < target:
            print(
                f"⚠ Scene {self._current_scene_num} timeline short: "
                f"elapsed={elapsed:.2f}s < target={target:.2f}s"
            )
        else:
            print(
                f"✓ Scene {self._current_scene_num} done: "
                f"elapsed={elapsed:.2f}s / target={target:.2f}s"
            )

    # ========== 4. Intra-Scene Sync Tools (Core) ==========
    def wait_until_scene_time(self, target_time):
        """
        Wait until the specified time within the current scene (seconds relative to scene start).

        If animation exceeds target time, prints a warning but does not rewind.
        Usage: self.wait_until_scene_time(3.7)  # Wait until 3.7s after scene starts
        """
        elapsed = self.time - self._scene_start_time
        remaining = target_time - elapsed
        if remaining > 0.05:
            self.wait(remaining)
        elif remaining < -0.3:
            print(
                f"  ⚠ Scene {self._current_scene_num} animation timeout {abs(remaining):.2f}s "
                f"(target {target_time:.1f}s, actual {elapsed:.1f}s)"
            )

    def wait_for_narration(self, keyword):
        """
        Wait until the voiceover says the sentence containing the keyword.

        Searches for the first entry containing the keyword from the current scene's sync_points,
        then calls wait_until_scene_time() to align.

        Usage:
            self.wait_for_narration("incircle")
            self.play(FadeIn(incircle))
        """
        target = self.get_sync_time(keyword)
        if target is not None:
            self.wait_until_scene_time(target)
        else:
            print(
                f"  ⚠ Scene {self._current_scene_num} sync point '{keyword}' not found, "
                f"skipping wait (check sync_points in audio_info.json)"
            )

    def get_sync_time(self, keyword):
        """
        Find the sync point time containing the keyword in the current scene.

        Returns: float seconds, None if not found
        """
        points = self._sync_points.get(self._current_scene_num, [])
        for sp in points:
            if keyword in sp.get("text", ""):
                return sp["time"]
        return None

    def get_sync_time_by_index(self, sentence_idx):
        """
        Get sync point time by sentence index (0th sentence, 1st sentence...).

        Returns: float seconds, None if not found
        """
        points = self._sync_points.get(self._current_scene_num, [])
        for sp in points:
            if sp.get("idx") == sentence_idx:
                return sp["time"]
        return None

    # ========== 5. Geometry Calculation (Must implement) ==========
    def calculate_geometry(self):
        """
        Calculate positions and properties of all geometric elements

        Coordinate system notes:
        - Point format: (x, y) - z coordinate is always 0
        - Recommended bounds for geometric shapes: (-5, 5) x (-4, 4)

        Returns: dict containing data for all geometric objects
        """
        geometry = {
            'points': {},
            'lines': {},
            'circles': {},
            'arcs': {},
            'polygons': {},
        }
        # TODO: [Must Implement] Calculate all point coordinates based on problem geometry
        return geometry

    # ========== 6. Geometry Validation (Must implement) ==========
    def assert_geometry(self, geometry):
        """
        Validate geometry calculation correctness (Minimal validation principle)

        Validation checks:
        1. Facts given by the problem (e.g. two edges are equal)
        2. Precision issues: use relative error for comparisons
        3. Canvas bounds check: Ensure shapes are within the visible area
        """
        def approx_equal(a, b, epsilon=1e-4):
            return abs(a - b) < epsilon

        # TODO: [Must Implement] Verify geometry correctness

        def check_canvas_bounds(geometry):
            all_points = list(geometry.get('points', {}).values())
            for circle in geometry.get('circles', {}).values():
                cx, cy = circle['center']
                r = circle['radius']
                all_points.extend([(cx+r, cy), (cx-r, cy), (cx, cy+r), (cx, cy-r)])

            if not all_points:
                return True

            xs = [p[0] for p in all_points]
            ys = [p[1] for p in all_points]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)

            CANVAS_MIN_X, CANVAS_MAX_X = -7, 7
            CANVAS_MIN_Y, CANVAS_MAX_Y = -4, 4

            if min_x < CANVAS_MIN_X or max_x > CANVAS_MAX_X:
                print(f"Warning: Shapes exceed horizontal bounds: X bounds [{min_x:.2f}, {max_x:.2f}]")
            if min_y < CANVAS_MIN_Y or max_y > CANVAS_MAX_Y:
                print(f"Warning: Shapes exceed vertical bounds: Y bounds [{min_y:.2f}, {max_y:.2f}]")

            center_x = (min_x + max_x) / 2
            center_y = (min_y + max_y) / 2
            if abs(center_x) > 3.0:
                 print(f"Warning: Shape center offset heavily from x-axis: {center_x:.2f}")
            if abs(center_y) > 2.0:
                 print(f"Warning: Shape center offset heavily from y-axis: {center_y:.2f}")
            return True

        check_canvas_bounds(geometry)
        print("Geometry validation passed!")

    # ========== 7. Graphic Elements Definition ==========
    def define_elements(self, geometry):
        """Define Manim graphical objects (but do not create animations yet)"""
        elements = {
            'points': {},
            'lines': {},
            'circles': {},
            'labels': {},
        }

        def to_3d(p):
            return (p[0], p[1], 0.0)

        # TODO: Define graphic elements based on storyboard requirements
        return elements

    # ========== 8. Subtitle Tools ==========
    def create_subtitle(self, text, position=DOWN * 3.5):
        """Create subtitle object"""
        subtitle = Text(text, font_size=36, color=self.COLORS['text'])
        subtitle.to_edge(position)
        return subtitle

    def fade_in(self, mobject, run_time=0.5):
        return FadeIn(mobject, run_time=run_time)

    def fade_out(self, mobject, run_time=0.5):
        return FadeOut(mobject, run_time=run_time)

    def show_subtitle_timed(self, text, duration, position=DOWN * 3.5,
                            fade_in_time=0.5, fade_out_time=0.5):
        """Show subtitle and auto exit after specified duration"""
        subtitle = self.create_subtitle(text, position)
        self.play(self.fade_in(subtitle), run_time=fade_in_time)
        hold_time = max(0.0, duration - fade_in_time - fade_out_time)
        self.wait(hold_time)
        self.play(self.fade_out(subtitle), run_time=fade_out_time)
        return subtitle

    def show_subtitle_with_audio(self, text, audio_duration, position=DOWN * 3.5):
        """Show subtitle and keep it until audio finishes"""
        subtitle = self.create_subtitle(text, position)
        self.play(self.fade_in(subtitle), run_time=0.5)
        self.wait(max(0.0, audio_duration - 1.0))
        self.play(self.fade_out(subtitle), run_time=0.5)
        return subtitle

    # ========== 9. Highlight Tools ==========
    def highlight_element(self, element, color=None, scale=1.3, duration=0.8):
        """Highlight specified element"""
        color = color or self.COLORS['highlight']
        original_color = element.get_color()
        self.play(
            element.animate.scale(scale).set_color(color),
            run_time=0.4
        )
        self.wait(duration - 0.4)
        self.play(
            element.animate.scale(1/scale).set_color(original_color),
            run_time=0.4
        )

    def indicate_equal_lines(self, line1, line2, duration=1.2):
        """Indicate two lines are equal (highlight simultaneously)"""
        self.play(
            line1.animate.set_color(self.COLORS['highlight']).set_stroke(width=6),
            line2.animate.set_color(self.COLORS['highlight']).set_stroke(width=6),
            run_time=0.5
        )
        self.wait(duration - 0.8)
        self.play(
            line1.animate.set_color(self.COLORS['primary']).set_stroke(width=3),
            line2.animate.set_color(self.COLORS['primary']).set_stroke(width=3),
            run_time=0.5
        )

    # ========== 10. Main Flow ==========
    def construct(self):
        """Main Construction Flow"""
        self.camera.background_color = self.COLORS['background']

        geometry = self.calculate_geometry()
        self.assert_geometry(geometry)
        elements = self.define_elements(geometry)

        for scene_num, scene_name, audio_file, duration in self.SCENES:
            method_name = f"play_scene_{scene_num}"
            if hasattr(self, method_name):
                expected_duration = self.start_scene_with_audio(scene_num)
                getattr(self, method_name)(elements, geometry)
                self.end_scene_with_audio(expected_duration)
            else:
                print(f"Warning: play_scene_{scene_num} not implemented")

        self.copy_video_to_root()

    def copy_video_to_root(self):
        """Copy video to project root after rendering"""
        import shutil
        from pathlib import Path

        scene_name = self.__class__.__name__
        possible_paths = [
            Path(f"media/videos/script/1920p60/{scene_name}.mp4"),
            Path(f"media/videos/script/1080p60/{scene_name}.mp4"),
            Path(f"media/videos/script/720p30/{scene_name}.mp4"),
        ]

        video_src = None
        for path in possible_paths:
            if path.exists():
                video_src = path
                break

        if video_src:
            video_dst = Path(f"{scene_name}.mp4")
            try:
                shutil.copy2(video_src, video_dst)
                print(f"\n✓ Video copied to: {video_dst.absolute()}")
            except Exception as e:
                print(f"\n⚠️ Video copy failed: {e}")
        else:
            print(f"\n⚠️ Video file not found")


# ========== Usage Instructions ==========
"""
Important Reminders:
1. All geometry calculations must be done in calculate_geometry()
2. assert_geometry() must check the canvas bounds
3. Each scene must be wrapped by start_scene_with_audio()/end_scene_with_audio()
4. Highlight whatever the voiceover mentions
5. Use wait_for_narration("keyword") to align voice and highlights - do not manually estimate duration - N
6. Use wait_until_scene_time(seconds) for precise timing within a scene
7. Use create_subtitle() to create subtitles, do not use the Subtitle class
8. The end of the scene is automatically padded by end_scene_with_audio(), no manual wait is needed in play_scene_X()
9. All point coordinates use 2D (x, y); convert with to_3d() in define_elements
10. Subtitle exit: Use show_subtitle_timed() or show_subtitle_with_audio() to ensure text exits

Sync alignment example (Recommended style):
    def play_scene_2(self, elements, geometry):
        # Narration sentence 1: "First, let's look at triangle ABC"
        self.wait_for_narration("triangle ABC")
        self.play(Create(triangle, run_time=1.0))

        # Narration sentence 2: "Its incircle I, tangent to the three sides"
        self.wait_for_narration("incircle")
        self.play(FadeIn(incircle, run_time=0.5))

        # No manual wait needed - end_scene_with_audio() will auto-pad
"""
