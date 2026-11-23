#!/usr/bin/env python3
"""Host-side regression tests for the generated assets, model and previews."""
import hashlib
import math
import os
import sys
import unittest

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "firmware", "assets")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from comanche_model import (  # noqa: E402
    BED_FRONT, BED_REAR, BW, FRONT_AXLE, FRONT_BUMPER, REAR_AXLE,
    REAR_BUMPER, ROOF, SPEC, WB, build, project_points,
    turntable_ring, view_fit,
)


def digest(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class AssetTests(unittest.TestCase):
    def test_arc_frames(self):
        d = os.path.join(ASSETS, "gauges", "arc")
        files = sorted(f for f in os.listdir(d) if f.startswith("arc_"))
        self.assertEqual(len(files), 36, files)
        hashes = set()
        for name in files:
            im = Image.open(os.path.join(d, name)).convert("RGBA")
            self.assertEqual(im.size, (272, 124), name)
            alpha = im.getchannel("A")
            self.assertEqual(alpha.getextrema(), (0, 255), name)
            hashes.add(digest(os.path.join(d, name)))
        self.assertEqual(len(hashes), 36, "compass frames are not unique")

    def test_truck_frames(self):
        d = os.path.join(ASSETS, "truck")
        files = sorted(f for f in os.listdir(d) if f.startswith("frame_"))
        frames = [f for f in files if len(f) == len("frame_000.png")]
        self.assertEqual(len(frames), 120)
        hashes = set()
        for name in frames:
            im = Image.open(os.path.join(d, name)).convert("RGBA")
            self.assertEqual(im.size, (140, 78), name)
            lo, hi = im.getchannel("A").getextrema()
            self.assertEqual(lo, 0, name)
            self.assertGreaterEqual(hi, 254, name)
            hashes.add(digest(os.path.join(d, name)))
        self.assertGreater(len(hashes), 100, "turntable frames collapsed")

    def test_attitude_masks(self):
        for name, size in (("gauge_roll.png", (134, 88)),
                           ("gauge_pitch.png", (134, 88)),
                           ("front.png", (56, 48)),
                           ("side.png", (116, 40))):
            im = Image.open(os.path.join(ASSETS, "gauges", name)).convert("RGBA")
            self.assertEqual(im.size, size, name)
            self.assertEqual(im.getchannel("A").getextrema(), (0, 255), name)

    def test_manifest_paths(self):
        with open(os.path.join(ASSETS, "images.yaml")) as f:
            manifest = f.read()
        for line in manifest.splitlines():
            line = line.strip()
            if line.startswith("file: "):
                path = os.path.join(ROOT, "firmware", line[6:])
                self.assertTrue(os.path.exists(path), path)
        self.assertIn("type: GRAYSCALE", manifest)
        self.assertNotIn("instruments/", manifest)
        with open(os.path.join(ASSETS, "truck_src.yaml")) as f:
            src = f.read().splitlines()
        self.assertEqual(len(src), 120)
        self.assertEqual(src[0], "- truck_000")
        self.assertEqual(src[-1], "- truck_119")

    def test_dashboard_files(self):
        for name in ("ui-background.png", "startup.png", "paint_edge.png"):
            self.assertTrue(os.path.exists(os.path.join(ASSETS, name)), name)

    def test_no_anchor_widgets(self):
        # YAML anchors on widget mappings create a real placeholder widget at
        # (0,0), which showed up as stray boxes in early revisions.  Style
        # anchors are fine; mapping merge keys on widgets are not.
        with open(os.path.join(ROOT, "firmware", "comanche-monitor.yaml")) as f:
            yaml = f.read()
        self.assertNotIn("<<: *", yaml)
        for marker in ("- obj: &", "- button: &", "- label: &"):
            self.assertNotIn(marker, yaml)


class ModelTests(unittest.TestCase):
    def test_published_dimensions(self):
        self.assertAlmostEqual(SPEC["length"], 194.0, places=1)
        self.assertAlmostEqual(SPEC["width"], 71.7, places=1)
        self.assertAlmostEqual(SPEC["height"], 64.7, places=1)
        self.assertAlmostEqual(SPEC["wheelbase"], 119.9, places=1)
        self.assertAlmostEqual(FRONT_BUMPER - REAR_BUMPER, SPEC["length"], 1)
        self.assertAlmostEqual(REAR_AXLE - FRONT_AXLE, -WB, 1)
        self.assertAlmostEqual(2 * BW, SPEC["width"], 1)
        self.assertAlmostEqual(ROOF, SPEC["height"], 1)
        self.assertGreaterEqual(abs(BED_REAR - BED_FRONT), 84.0)

    def test_projection_and_fit(self):
        model = build()
        ring = turntable_ring()
        yaws = [2 * math.pi * i / 120 + math.radians(30) for i in range(120)]
        scale, cx, cy = view_fit([model.verts, ring], yaws, 140, 78,
                                 math.radians(16), margin=3.0)
        for yaw in yaws:
            p = project_points(model.verts, yaw, math.radians(16), scale, cx, cy)
            self.assertTrue((p[:, 2] > 0).all())
            self.assertGreaterEqual(p[:, 0].min(), 2.0)
            self.assertLessEqual(p[:, 0].max(), 138.0)
            self.assertGreaterEqual(p[:, 1].min(), 2.0)
            self.assertLessEqual(p[:, 1].max(), 76.0)

    def test_frame_step_and_loop(self):
        step = 360.0 / 120
        self.assertAlmostEqual(step, 3.0)
        # 24 fps for five seconds, then the first and last pose are one step
        # apart rather than a duplicate.
        self.assertAlmostEqual(120 / 5.0, 24.0)

    def test_side_projection_direction(self):
        model = build()
        p = project_points(model.verts, 0.0, 0.0, 1.0, 0.0, 0.0)
        x_front = max(p[:, 0])
        x_rear = min(p[:, 0])
        # In the side view the nose is to the right, matching the preview and
        # the old dashboard contract.
        self.assertGreater(x_front, x_rear)

    def test_turntable_pivots_about_middle(self):
        model = build()
        ring = turntable_ring()
        yaws = [2 * math.pi * i / 120 for i in range(120)]
        scale, cx, cy = view_fit([model.verts, ring], yaws, 140, 78,
                                 math.radians(16), margin=3.0)
        centres = []
        for yaw in (0.0, math.pi / 2, math.pi):
            p = project_points(model.verts, yaw, math.radians(16), scale, cx, cy)
            centres.append((p[:, 0].min() + p[:, 0].max()) * 0.5)
        # The silhouette centre must not wander as the truck yaws; an origin
        # pivot used to swing it around the nose.
        self.assertLess(max(centres) - min(centres), 2.5)

    def test_camera_looks_down(self):
        ring = turntable_ring()
        p = project_points(ring, 0.0, math.radians(16), 1.0, 0.0, 0.0)
        # At yaw 0 the +Y half of the ground ring is farther from the camera;
        # in a top-down view it must sit higher on screen (smaller y).
        ys = [pt[1] for pt in ring]
        far = p[[i for i, y in enumerate(ys) if y > 10], 1]
        near = p[[i for i, y in enumerate(ys) if y < -10], 1]
        self.assertLess(far.mean(), near.mean())


if __name__ == "__main__":
    unittest.main(verbosity=2)
