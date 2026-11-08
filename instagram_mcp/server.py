import os
import io
import json
import httpx
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

from mcp.server.mcpserver import MCPServer

from instagram_mcp.config import settings
from instagram_mcp.instagram_client import InstagramClient, InstagramAPIError
from instagram_mcp.image_processor import (
    prepare_for_instagram,
    analyze_image,
    load_image,
    ImageProcessingError
)
from instagram_mcp.uploader import get_public_image_url, UploadError

# Create the MCP Server instance
app = MCPServer(
    name="instagram-poster",
    instructions=(
        "Instagram Publishing MCP Server. Allows AI agents to validate, format, and post "
        "AI-generated images, carousels, and stories to Instagram via the official Meta Graph API."
    )
)

client = InstagramClient()


def _is_url(source: str) -> bool:
    """Check if the string is a web URL."""
    s = source.strip().lower()
    return s.startswith("http://") or s.startswith("https://")


async def _resolve_image_to_url(
    image_source: str,
    target_type: str = "feed",
    auto_format: bool = True,
    fit_mode: str = "pad"
) -> str:
    """
    Takes an image source (local file, URL, or base64 data) and returns a publicly
    accessible HTTPS URL ready for the Instagram Graph API.
    """
    # If it's already a URL and auto_format is False, return it directly
    if _is_url(image_source) and not auto_format:
        return image_source

    # If it's a URL and auto_format is True, download it to temp first for formatting
    if _is_url(image_source) and auto_format:
        async with httpx.AsyncClient(timeout=30.0) as http_c:
            resp = await http_c.get(image_source)
            if resp.status_code != 200:
                raise ValueError(f"Failed to download image from URL {image_source}: HTTP {resp.status_code}")
            image_bytes = resp.content
        local_prep = prepare_for_instagram(
            image_bytes,
            target_type=target_type,
            fit_mode=fit_mode
        )
        return await get_public_image_url(local_prep)

    # If it's a local file or base64
    if auto_format:
        local_prep = prepare_for_instagram(
            image_source,
            target_type=target_type,
            fit_mode=fit_mode
        )
    else:
        # Save raw to temp file if not already a path
        if image_source.startswith("data:image/") or ";base64," in image_source:
            local_prep = prepare_for_instagram(image_source, target_type=target_type)
        else:
            local_prep = Path(image_source).expanduser().resolve()
            if not local_prep.exists():
                raise FileNotFoundError(f"Local file does not exist: {image_source}")

    return await get_public_image_url(local_prep)


@app.tool()
async def post_image(
    image_source: str,
    caption: str = "",
    auto_format: bool = True,
    fit_mode: str = "pad",
    location_id: Optional[str] = None
) -> str:
    """
    Publish a single image to an Instagram Business or Creator account feed.

    Args:
        image_source: Path to a local image file (e.g. '/tmp/ai_artwork.png'), a base64 data string, or a public HTTPS URL.
        caption: Caption text for the post, including hashtags and emojis.
        auto_format: If True (recommended for AI images), automatically adjusts aspect ratio to Instagram feed limits (between 4:5 and 1.91:1) and converts to RGB JPEG.
        fit_mode: How to adjust aspect ratio if outside 4:5 - 1.91:1. 'pad' adds a stylish blurred background border (preserves entire artwork), 'crop' center-crops the image.
        location_id: Optional Facebook Page ID for location tagging.

    Returns:
        JSON string containing the post result: permalink, post_id, and status.
    """
    try:
        settings.validate_meta_credentials()

        # Step 1: Ensure image is in valid format and get public HTTPS URL
        public_url = await _resolve_image_to_url(
            image_source=image_source,
            target_type="feed",
            auto_format=auto_format,
            fit_mode=fit_mode
        )

        # Step 2: Create media container in Meta Graph API
        creation_id = await client.create_image_container(
            image_url=public_url,
            caption=caption,
            location_id=location_id
        )

        # Step 3: Wait for container to finish processing
        await client.wait_for_container(creation_id)

        # Step 4: Publish container
        media_id = await client.publish_container(creation_id)

        # Step 5: Retrieve post details and permalink
        details = await client.get_media_details(media_id)

        return json.dumps({
            "status": "success",
            "message": "Image published successfully to Instagram!",
            "post_id": media_id,
            "permalink": details.get("permalink", f"https://www.instagram.com/p/{media_id}"),
            "caption": caption,
            "timestamp": details.get("timestamp")
        }, indent=2)

    except (InstagramAPIError, ImageProcessingError, UploadError, ValueError, FileNotFoundError) as e:
        return json.dumps({
            "status": "error",
            "error_type": type(e).__name__,
            "message": str(e)
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "UnexpectedError",
            "message": f"An unexpected error occurred: {str(e)}"
        }, indent=2)


@app.tool()
async def post_carousel(
    images: List[str],
    caption: str = "",
    auto_format: bool = True,
    fit_mode: str = "pad",
    location_id: Optional[str] = None
) -> str:
    """
    Publish a multi-image carousel post (2 to 10 images) to Instagram.

    Args:
        images: List of image sources (local file paths, base64 strings, or HTTPS URLs).
        caption: Post caption with hashtags and emojis.
        auto_format: If True, automatically optimizes each image for Instagram dimensions and format.
        fit_mode: 'pad' (blurred padding) or 'crop' (center crop).
        location_id: Optional Facebook Page ID for location tagging.

    Returns:
        JSON string with carousel post ID and permalink.
    """
    try:
        if len(images) < 2:
            return json.dumps({
                "status": "error",
                "message": "A carousel post requires at least 2 images (up to 10)."
            })
        if len(images) > 10:
            return json.dumps({
                "status": "error",
                "message": "Instagram carousels support a maximum of 10 images."
            })

        settings.validate_meta_credentials()

        # Step 1: Prepare and upload each item
        item_ids = []
        for idx, img_src in enumerate(images, 1):
            public_url = await _resolve_image_to_url(
                image_source=img_src,
                target_type="feed",
                auto_format=auto_format,
                fit_mode=fit_mode
            )
            item_id = await client.create_image_container(
                image_url=public_url,
                is_carousel_item=True
            )
            item_ids.append(item_id)

        # Step 2: Wait for item containers
        for item_id in item_ids:
            await client.wait_for_container(item_id)

        # Step 3: Create parent carousel container
        carousel_id = await client.create_carousel_container(
            item_container_ids=item_ids,
            caption=caption,
            location_id=location_id
        )

        # Step 4: Wait for carousel container
        await client.wait_for_container(carousel_id)

        # Step 5: Publish carousel
        media_id = await client.publish_container(carousel_id)

        # Step 6: Fetch post permalink
        details = await client.get_media_details(media_id)

        return json.dumps({
            "status": "success",
            "message": f"Carousel with {len(images)} images published successfully!",
            "post_id": media_id,
            "permalink": details.get("permalink", f"https://www.instagram.com/p/{media_id}"),
            "caption": caption
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": type(e).__name__,
            "message": str(e)
        }, indent=2)


@app.tool()
async def post_story(
    image_source: str,
    auto_format: bool = True,
    fit_mode: str = "pad"
) -> str:
    """
    Publish an image to Instagram Stories (vertical 9:16 format, disappears after 24 hours).

    Args:
        image_source: Path to local image file, base64 data, or HTTPS URL.
        auto_format: Automatically formats image to 9:16 vertical story aspect ratio.
        fit_mode: 'pad' (blurred padding) or 'crop' (center crop).

    Returns:
        JSON string with story publication status.
    """
    try:
        settings.validate_meta_credentials()

        public_url = await _resolve_image_to_url(
            image_source=image_source,
            target_type="story",
            auto_format=auto_format,
            fit_mode=fit_mode
        )

        creation_id = await client.create_story_container(image_url=public_url)
        await client.wait_for_container(creation_id)
        media_id = await client.publish_container(creation_id)

        return json.dumps({
            "status": "success",
            "message": "Story published successfully to Instagram!",
            "story_id": media_id
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": type(e).__name__,
            "message": str(e)
        }, indent=2)


@app.tool()
def format_and_preview_image(
    image_source: str,
    target_type: str = "feed",
    fit_mode: str = "pad",
    output_path: Optional[str] = None
) -> str:
    """
    Inspects and prepares an AI-generated image for Instagram without publishing.
    Verifies aspect ratio, format, dimensions, and saves an Instagram-ready JPEG copy.

    Args:
        image_source: Path to local image file or base64 string.
        target_type: 'feed' (aspect ratio 4:5 to 1.91:1) or 'story' (9:16 vertical).
        fit_mode: 'pad' (blurred background padding) or 'crop' (center crop).
        output_path: Optional destination file path for the optimized JPEG.

    Returns:
        JSON string with original image analysis, validation status, and formatted image path.
    """
    try:
        raw_img, _ = load_image(image_source)
        analysis = analyze_image(raw_img)

        dest_file = prepare_for_instagram(
            image_source,
            target_type=target_type,
            fit_mode=fit_mode,
            output_path=output_path
        )

        # Inspect resulting image
        processed_img, _ = load_image(str(dest_file))
        processed_analysis = analyze_image(processed_img)

        return json.dumps({
            "status": "success",
            "original_image": analysis,
            "processed_image": {
                "file_path": str(dest_file),
                "file_size_kb": round(dest_file.stat().st_size / 1024, 2),
                **processed_analysis
            }
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, indent=2)


@app.tool()
async def get_instagram_profile() -> str:
    """
    Retrieve profile details of the connected Instagram Business/Creator account.
    Useful for the AI agent to verify identity, username, follower count, and media count.

    Returns:
        JSON string containing username, name, followers_count, media_count, etc.
    """
    try:
        settings.validate_meta_credentials()
        profile = await client.get_profile()
        return json.dumps({
            "status": "success",
            "account": profile
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, indent=2)


@app.tool()
async def get_recent_posts(limit: int = 10) -> str:
    """
    Retrieve the most recent posts published by the connected Instagram account.
    Useful for checking past captions, post URLs, and engagement metrics.

    Args:
        limit: Number of recent posts to retrieve (1 to 25, default 10).

    Returns:
        JSON string listing recent posts with id, caption, permalink, likes, and comments.
    """
    try:
        settings.validate_meta_credentials()
        posts = await client.get_recent_posts(limit=min(max(1, limit), 25))
        return json.dumps({
            "status": "success",
            "count": len(posts),
            "posts": posts
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, indent=2)


@app.tool()
async def check_setup_status() -> str:
    """
    Diagnose the Instagram MCP server setup, verifying API credentials, account ID,
    and image hosting availability.

    Returns:
        JSON string detailing configuration status and actionable hints.
    """
    results: Dict[str, Any] = {
        "status": "ok",
        "has_access_token": bool(settings.access_token),
        "account_id_configured": bool(settings.account_id),
        "api_version": settings.api_version,
        "image_hosting": {
            "imgbb": bool(settings.imgbb_api_key),
            "cloudinary": bool(settings.cloudinary_cloud_name and settings.cloudinary_api_key),
            "fallback_tmpfiles_active": True
        }
    }

    if not settings.access_token:
        results["status"] = "missing_credentials"
        results["hint"] = "INSTAGRAM_ACCESS_TOKEN is not set in .env. Generate a User or Page token from Meta Developer Portal."
        return json.dumps(results, indent=2)

    try:
        account_id = await client.get_account_id()
        results["detected_account_id"] = account_id
        profile = await client.get_profile()
        results["connected_account"] = {
            "username": profile.get("username"),
            "name": profile.get("name"),
            "followers_count": profile.get("followers_count"),
            "media_count": profile.get("media_count")
        }
    except Exception as e:
        results["status"] = "api_error"
        results["error"] = str(e)
        results["hint"] = (
            "Verify that your Instagram account is switched to Professional/Business or Creator, "
            "linked to a Facebook Page, and the token has 'instagram_content_publish' permission."
        )

    return json.dumps(results, indent=2)


def main():
    """Runs the Instagram MCP server over stdio."""
    app.run(transport="stdio")


if __name__ == "__main__":
    main()
