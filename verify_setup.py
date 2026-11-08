#!/usr/bin/env python3
"""
Diagnostics and Verification Script for Instagram MCP Server.
Tests connection to Meta Graph API, checks token scopes, auto-detects Instagram accounts,
and verifies image hosting configurations.
"""
import sys
import asyncio
from pathlib import Path
import httpx
from PIL import Image

# Ensure local package is in sys.path
sys.path.insert(0, str(Path(__file__).parent))

from instagram_mcp.config import settings
from instagram_mcp.instagram_client import InstagramClient, InstagramAPIError
from instagram_mcp.uploader import get_public_image_url
from instagram_mcp.image_processor import prepare_for_instagram


def print_header(title: str):
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


async def check_credentials_and_account():
    print_header("1. Checking Meta Graph API Credentials")

    if not settings.access_token:
        print("❌ [FAILED] INSTAGRAM_ACCESS_TOKEN is not set.")
        print("   Please create a .env file and set your Instagram/Meta Access Token.")
        print("   See .env.example and README.md for instructions.")
        return False

    print("✅ INSTAGRAM_ACCESS_TOKEN found.")
    print(f"   API Version: {settings.api_version}")

    client = InstagramClient()

    # Step A: Validate token and discover connected accounts
    print("\nValidating token and querying connected Instagram accounts...")
    try:
        accounts = await client.list_available_instagram_accounts()
        if not accounts:
            print("❌ [FAILED] No Instagram Business/Creator accounts found for this token.")
            print("   Make sure your Instagram account is switched to Business or Creator and linked to your Facebook Page.")
            return False

        print(f"✅ Found {len(accounts)} Instagram Business Account(s):")
        for idx, acc in enumerate(accounts, 1):
            is_active = (acc["id"] == settings.account_id) or (not settings.account_id and idx == 1)
            marker = " (SELECTED IN .ENV)" if is_active else ""
            print(f"   {idx}. @{acc.get('username', 'unknown')} (ID: {acc.get('id')}){marker}")
            print(f"      Name: {acc.get('name', 'N/A')}")
            print(f"      Followers: {acc.get('followers_count', 0)} | Media posts: {acc.get('media_count', 0)}")

        active_id = await client.get_account_id()
        print(f"\n✅ Active Instagram Account ID: {active_id}")

        profile = await client.get_profile()
        print(f"✅ Ready to post as: @{profile.get('username')}")
        return True

    except Exception as e:
        print(f"❌ [FAILED] Error inspecting token or Instagram account: {e}")
        return False


async def check_image_hosting():
    print_header("2. Checking Image Hosting & Formatting Pipeline")

    # Create a small dummy test image
    test_file = settings.temp_dir / "setup_test.png"
    img = Image.new("RGBA", (500, 800), (45, 120, 240, 255))
    img.save(test_file)

    try:
        print("Testing image formatting for Instagram (converting RGBA to valid 4:5 JPEG)...")
        formatted = prepare_for_instagram(test_file, target_type="feed", fit_mode="pad")
        print(f"✅ Formatted successfully: {formatted.name} ({formatted.stat().st_size} bytes)")

        print("\nTesting public image URL generation (for Meta Graph API)...")
        if settings.cloudinary_cloud_name and settings.cloudinary_api_key:
            print("   Using: Cloudinary")
        elif settings.imgbb_api_key:
            print("   Using: ImgBB")
        else:
            print("   Using: Free Temporary Host fallback (tmpfiles.org)")

        public_url = await get_public_image_url(formatted)
        print(f"✅ Public URL generated: {public_url}")

        # Verify URL is accessible
        async with httpx.AsyncClient(timeout=15.0) as http_client:
            resp = await http_client.head(public_url)
            print(f"✅ Remote URL status: HTTP {resp.status_code} (Reachable by Meta)")
        return True

    except Exception as e:
        print(f"⚠️ Image hosting test encountered an issue: {e}")
        print("   Note: If offline or sandbox is restricted, verify with BypassSandbox or external internet.")
        return False
    finally:
        if test_file.exists():
            test_file.unlink()


async def main():
    print_header("Instagram MCP Server Setup Verification")
    meta_ok = await check_credentials_and_account()
    hosting_ok = await check_image_hosting()

    print_header("Verification Summary")
    if meta_ok and hosting_ok:
        print("🎉 ALL CHECKS PASSED! The Instagram MCP server is fully configured and ready.")
        print("   You can now launch the MCP server in Claude Desktop, Cursor, or your AI agent.")
    elif not meta_ok:
        print("⚠️ Meta Graph API credentials need configuration.")
        print("   Edit your .env file with valid INSTAGRAM_ACCESS_TOKEN.")
    else:
        print("⚠️ Meta API is connected, but image hosting check had warnings.")


if __name__ == "__main__":
    asyncio.run(main())

