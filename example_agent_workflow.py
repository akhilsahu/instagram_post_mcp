#!/usr/bin/env python3
"""
Example AI Agent Workflow:
Simulates how an AI agent generates an image, inspects and formats it,
and publishes it to Instagram using the Instagram MCP tools.
"""
import sys
import asyncio
import json
from pathlib import Path
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))

from instagram_mcp.server import (
    format_and_preview_image,
    post_image,
    post_carousel,
    post_story,
    check_setup_status
)


def generate_sample_artwork(output_path: Path) -> Path:
    """Generates a synthetic AI-style gradient artwork for testing."""
    width, height = 768, 1344  # Typical vertical AI portrait generation (9:16)
    img = Image.new("RGBA", (width, height))
    draw = ImageDraw.Draw(img)

    # Draw vertical color gradient
    for y in range(height):
        r = int(30 + (220 * y / height))
        g = int(20 + (100 * (1 - y / height)))
        b = int(180 + (70 * y / height))
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    # Draw decorative circles
    draw.ellipse([width // 4, height // 3, 3 * width // 4, height // 3 + width // 2], outline=(255, 255, 255, 180), width=6)
    draw.ellipse([width // 3, height // 3 + width // 12, 2 * width // 3, height // 3 + 5 * width // 12], fill=(255, 220, 100, 220))

    img.save(output_path)
    print(f"🎨 Generated sample AI artwork: {output_path} ({width}x{height} RGBA)")
    return output_path


async def main():
    print("=" * 60)
    print("🤖 AI AGENT INSTAGRAM PUBLISHING WORKFLOW SIMULATION")
    print("=" * 60)

    # Step 1: Health check
    print("\n--- Step 1: Checking MCP Status ---")
    status_raw = await check_setup_status()
    status = json.loads(status_raw)
    print(f"Status: {status.get('status')}")
    print(f"Image hosting fallback: {status.get('image_hosting', {}).get('fallback_tmpfiles_active')}")

    # Step 2: Agent produces an AI image
    print("\n--- Step 2: Agent Generates Image ---")
    sample_file = Path("/tmp/ai_artwork_demo.png")
    generate_sample_artwork(sample_file)

    # Step 3: Inspect & format before posting
    print("\n--- Step 3: Agent Previews & Formats Image ---")
    preview_res = json.loads(format_and_preview_image(
        image_source=str(sample_file),
        target_type="feed",
        fit_mode="pad"
    ))
    print(f"Original: {preview_res['original_image']['width']}x{preview_res['original_image']['height']} ({preview_res['original_image']['aspect_ratio']} ratio, format: {preview_res['original_image']['format']})")
    print(f"Formatted: {preview_res['processed_image']['width']}x{preview_res['processed_image']['height']} ({preview_res['processed_image']['aspect_ratio']} ratio, format: {preview_res['processed_image']['format']})")
    print(f"Feed Compliance: ✅ Valid aspect ratio ({preview_res['processed_image']['is_valid_feed']})")

    # Step 4: Publish single image post (using dry-run for simulation)
    print("\n--- Step 4: Agent Publishes Single Feed Post ---")
    post_res = json.loads(await post_image(
        image_source=str(sample_file),
        caption="Exploring digital aesthetics and vibrant color gradients ✨ #GenerativeArt #DigitalAesthetics #CreativeAI",
        auto_format=True,
        fit_mode="pad",
        dry_run=True  # Change to False when live credentials are set
    ))
    print(f"Post Status: {post_res.get('status')}")
    print(f"Message: {post_res.get('message')}")
    print(f"Simulated URL: {post_res.get('simulated_permalink', post_res.get('permalink'))}")

    # Step 5: Publish as 9:16 Story
    print("\n--- Step 5: Agent Publishes to Instagram Stories ---")
    story_res = json.loads(await post_story(
        image_source=str(sample_file),
        auto_format=True,
        fit_mode="pad",
        dry_run=True
    ))
    print(f"Story Status: {story_res.get('status')}")
    print(f"Message: {story_res.get('message')}")

    print("\n" + "=" * 60)
    print("🎉 WORKFLOW COMPLETE! The agent has tested single post, story & preview.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

