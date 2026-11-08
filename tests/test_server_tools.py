import unittest
import asyncio
import json
from pathlib import Path
from PIL import Image

from instagram_mcp.server import (
    format_caption,
    post_image,
    post_carousel,
    post_story,
    format_and_preview_image
)


class TestServerTools(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_dir = Path("/tmp/insta_mcp_server_tests")
        cls.test_dir.mkdir(parents=True, exist_ok=True)
        cls.sample_image = cls.test_dir / "sample_art.jpg"
        img = Image.new("RGB", (600, 600), (40, 80, 160))
        img.save(cls.sample_image)

    def test_format_caption_valid(self):
        res = json.loads(format_caption(
            text="Futuristic cyberpunk landscape.",
            hashtags=["AIArt", "#Cyberpunk", "Art"],
            call_to_action="Follow for more daily AI designs!"
        ))
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["is_valid_for_instagram"])
        self.assertEqual(res["hashtag_count"], 3)
        self.assertIn("#AIArt #Cyberpunk #Art", res["caption"])

    def test_format_caption_limit_warning(self):
        # Generate 35 hashtags (exceeds Instagram limit of 30)
        tags = [f"tag{i}" for i in range(35)]
        res = json.loads(format_caption(text="Photo test", hashtags=tags))
        self.assertEqual(res["status"], "warning")
        self.assertFalse(res["is_valid_for_instagram"])
        self.assertTrue(len(res["warnings"]) > 0)

    def test_post_image_dry_run(self):
        result = asyncio.run(post_image(
            image_source=str(self.sample_image),
            caption="Test post",
            dry_run=True
        ))
        data = json.loads(result)
        self.assertEqual(data["status"], "dry_run_success")
        self.assertIn("simulated_permalink", data)
        self.assertTrue(data["image_analysis"]["is_valid_feed"])

    def test_post_carousel_dry_run(self):
        result = asyncio.run(post_carousel(
            images=[str(self.sample_image), str(self.sample_image)],
            caption="Test carousel",
            dry_run=True
        ))
        data = json.loads(result)
        self.assertEqual(data["status"], "dry_run_success")
        self.assertEqual(len(data["items"]), 2)

    def test_post_story_dry_run(self):
        result = asyncio.run(post_story(
            image_source=str(self.sample_image),
            caption="Daily Highlight",
            dry_run=True
        ))
        data = json.loads(result)
        self.assertEqual(data["status"], "dry_run_success")
        self.assertEqual(data["caption_overlay"], "Daily Highlight")

    def test_format_and_preview(self):
        result = format_and_preview_image(
            image_source=str(self.sample_image),
            caption_overlay="Title Bar",
            target_type="feed"
        )
        data = json.loads(result)
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["processed_image"]["is_valid_feed"])


if __name__ == "__main__":
    unittest.main()

