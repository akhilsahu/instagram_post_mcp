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

    # Step A: Test /me endpoint
    print("\nConnecting to Meta Graph API (/me)...")
    try:
        me_info = await client._request("GET", "me", params={"fields": "id,name"})
        print(f"✅ Connected to Meta User: {me_info.get('name')} (ID: {me_info.get('id')})")
    except InstagramAPIError as e:
        print(f"❌ [FAILED] Unable to query /me: {e}")
        return False

    # Step B: Auto-detect or verify Instagram Account
    print("\nSearching for linked Instagram Business/Creator accounts...")
    try:
        pages_res = await client._request(
            "GET",
            "me/accounts",
            params={"fields": "id,name,instagram_business_account{id,username,name}"}
        )
        pages = pages_res.get("data", [])
        if not pages:
            print("⚠️ No Facebook Pages found on this user account.")
        else:
            print(f"Found {len(pages)} Facebook Page(s):")
            for p in pages:
                ig = p.get("instagram_business_account")
                if ig:
                    print(f"   - Page: {p.get('name')} -> Linked Instagram: @{ig.get('username')} (ID: {ig.get('id')})")
                else:
                    print(f"   - Page: {p.get('name')} (No Instagram account linked to this page)")

        account_id = await client.get_account_id()
        print(f"\n✅ Active Instagram Account ID: {account_id}")

        profile = await client.get_profile()
        print("✅ Account Profile Verified:")
        print(f"   - Username: @{profile.get('username')}")
        print(f"   - Name: {profile.get('name')}")
        print(f"   - Followers: {profile.get('followers_count', 'N/A')}")
        print(f"   - Media count: {profile.get('media_count', 'N/A')}")
        return True

    except InstagramAPIError as e:
        print(f"❌ [FAILED] Error fetching Instagram account: {e}")
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
