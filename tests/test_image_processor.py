import unittest
from pathlib import Path
from PIL import Image

from instagram_mcp.image_processor import (
    prepare_for_instagram,
    analyze_image,
    load_image,
    add_caption_overlay,
    MIN_ASPECT_RATIO_FEED,
    MAX_ASPECT_RATIO_FEED,
    STORY_ASPECT_RATIO
)


class TestImageProcessor(unittest.TestCase):

    def setUp(self):
        self.temp_dir = Path("/tmp/insta_mcp_tests")
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def test_square_image(self):
        test_path = self.temp_dir / "test_square.png"
        img = Image.new("RGBA", (1000, 1000), (50, 100, 200, 255))
        img.save(test_path)

        dest = prepare_for_instagram(test_path, target_type="feed")
        res_img, _ = load_image(str(dest))
        analysis = analyze_image(res_img)

        self.assertEqual(analysis["format"], "JPEG")
        self.assertEqual(analysis["mode"], "RGB")
        self.assertTrue(analysis["is_valid_feed"])
        self.assertAlmostEqual(analysis["aspect_ratio"], 1.0, places=2)

    def test_tall_image_padded_to_feed(self):
        # 9:16 vertical image (too tall for feed)
        test_path = self.temp_dir / "test_tall.png"
        img = Image.new("RGBA", (768, 1344), (200, 50, 50, 200))
        img.save(test_path)

        dest = prepare_for_instagram(test_path, target_type="feed", fit_mode="pad")
        res_img, _ = load_image(str(dest))
        analysis = analyze_image(res_img)

        self.assertTrue(analysis["is_valid_feed"])
        self.assertGreaterEqual(analysis["aspect_ratio"], 0.795)

    def test_wide_image_padded_to_feed(self):
        # 21:9 ultrawide (too wide for feed)
        test_path = self.temp_dir / "test_wide.png"
        img = Image.new("RGB", (2100, 900), (50, 200, 50))
        img.save(test_path)

        dest = prepare_for_instagram(test_path, target_type="feed", fit_mode="pad")
        res_img, _ = load_image(str(dest))
        analysis = analyze_image(res_img)

        self.assertTrue(analysis["is_valid_feed"])
        self.assertLessEqual(analysis["aspect_ratio"], 1.915)

    def test_story_aspect_ratio(self):
        test_path = self.temp_dir / "test_story_input.png"
        img = Image.new("RGB", (1000, 1000), (100, 100, 100))
        img.save(test_path)

        dest = prepare_for_instagram(test_path, target_type="story", fit_mode="pad")
        res_img, _ = load_image(str(dest))
        analysis = analyze_image(res_img)

        self.assertTrue(analysis["is_valid_story"])
        self.assertAlmostEqual(analysis["aspect_ratio"], 9 / 16, places=1)

    def test_caption_overlay(self):
        img = Image.new("RGB", (800, 800), (30, 30, 40))
        overlaid = add_caption_overlay(img, "Cyberpunk Cat 🐾", position="bottom")

        self.assertEqual(overlaid.size, (800, 800))
        self.assertEqual(overlaid.mode, "RGB")


if __name__ == "__main__":
    unittest.main()

