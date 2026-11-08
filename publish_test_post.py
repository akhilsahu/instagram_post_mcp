#!/usr/bin/env python3
"""
Test Publishing Script for Instagram MCP Server.
Generates a test AI-style image and posts it live to Instagram
(or dry-run if --dry-run flag is passed).
"""
import sys
import asyncio
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))

from instagram_mcp.server import post_image, get_instagram_profile


def create_test_graphic(path: Path) -> Path:
    """Creates a colorful abstract test graphic for Instagram."""
    width, height = 1080, 1080  # Square 1:1 format
    img = Image.new("RGB", (width, height), (18, 18, 24))
    draw = ImageDraw.Draw(img)

    # Draw modern gradient circles and accents
    for r in range(400, 50, -30):
        alpha_color = (
            int(120 + 130 * (r / 400)),
            int(40 + 80 * (1 - r / 400)),
            int(220 - 50 * (r / 400))
        )
        draw.ellipse([540 - r, 540 - r, 540 + r, 540 + r], outline=alpha_color, width=4)

    # Inner core
    draw.ellipse([540 - 100, 540 - 100, 540 + 100, 540 + 100], fill=(240, 180, 50))

    img.save(path, format="JPEG", quality=95)
    print(f"Generated test image: {path}")
    return path


async def main():
    parser = argparse.ArgumentParser(description="Test publishing an image to Instagram")
    parser.add_argument("--dry-run", action="store_true", help="Simulate publishing without posting live to Instagram")
    parser.add_argument("--caption", type=str, default="Hello from Instagram MCP Server! 🤖✨ #AI #Automation #InstagramMCP", help="Post caption")
    args = parser.parse_args()

    # Step 1: Check account
    profile_raw = await get_instagram_profile()
    print("Connected Account:", profile_raw)

    # Step 2: Create image
    test_img = Path("/tmp/instagram_mcp_test.jpg")
    create_test_graphic(test_img)

    # Step 3: Publish
    print(f"\nPublishing image (dry_run={args.dry_run})...")
    result = await post_image(
        image_source=str(test_img),
        caption=args.caption,
        auto_format=True,
        fit_mode="pad",
        dry_run=args.dry_run
    )

    print("\n--- Publish Result ---")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
