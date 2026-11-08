import os
import time
import hashlib
import httpx
from pathlib import Path
from typing import Optional

from instagram_mcp.config import settings


class UploadError(Exception):
    """Raised when an image upload fails."""
    pass


async def upload_to_imgbb(image_path: Path, api_key: str) -> str:
    """Uploads a local image file to ImgBB and returns the direct image URL."""
    url = "https://api.imgbb.com/1/upload"
    async with httpx.AsyncClient(timeout=60.0) as client:
        with open(image_path, "rb") as f:
            files = {"image": f}
            data = {"key": api_key}
            response = await client.post(url, data=data, files=files)
            
        if response.status_code != 200:
            raise UploadError(f"ImgBB upload failed ({response.status_code}): {response.text}")
        
        res_data = response.json()
        if not res_data.get("success"):
            raise UploadError(f"ImgBB returned failure: {res_data}")
            
        return res_data["data"]["url"]


async def upload_to_cloudinary(
    image_path: Path,
    cloud_name: str,
    api_key: str,
    api_secret: str
) -> str:
    """Uploads a local image file to Cloudinary using REST API and returns secure URL."""
    timestamp = str(int(time.time()))
    # Generate signature for signed upload
    signature_str = f"timestamp={timestamp}{api_secret}"
    signature = hashlib.sha1(signature_str.encode("utf-8")).hexdigest()
    
    url = f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload"
    async with httpx.AsyncClient(timeout=60.0) as client:
        with open(image_path, "rb") as f:
            files = {"file": f}
            data = {
                "api_key": api_key,
                "timestamp": timestamp,
                "signature": signature
            }
            response = await client.post(url, data=data, files=files)
            
        if response.status_code != 200:
            raise UploadError(f"Cloudinary upload failed ({response.status_code}): {response.text}")
            
        res_data = response.json()
        return res_data.get("secure_url") or res_data["url"]


async def upload_to_tmpfiles(image_path: Path) -> str:
    """
    Zero-config temporary upload using tmpfiles.org.
    Converts page URL to direct download URL (e.g., /123/img.jpg -> /dl/123/img.jpg).
    Files are kept temporarily, sufficient for Instagram Graph API to ingest.
    """
    url = "https://tmpfiles.org/api/v1/upload"
    async with httpx.AsyncClient(timeout=60.0) as client:
        with open(image_path, "rb") as f:
            files = {"file": f}
            response = await client.post(url, files=files)
            
        if response.status_code != 200:
            raise UploadError(f"tmpfiles upload failed ({response.status_code}): {response.text}")
            
        res_data = response.json()
        if res_data.get("status") != "success":
            raise UploadError(f"tmpfiles returned error: {res_data}")
            
        raw_url = res_data["data"]["url"]
        # Convert https://tmpfiles.org/123456/image.jpg to https://tmpfiles.org/dl/123456/image.jpg
        if "tmpfiles.org/" in raw_url and "/dl/" not in raw_url:
            direct_url = raw_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
        else:
            direct_url = raw_url
            
        return direct_url


async def upload_to_litterbox(image_path: Path) -> str:
    """Alternative zero-config temporary upload to Litterbox (catbox.moe 24h temp)."""
    url = "https://litterbox.catbox.moe/resources/internals/api.php"
    async with httpx.AsyncClient(timeout=60.0) as client:
        with open(image_path, "rb") as f:
            files = {"fileToUpload": f}
            data = {"reqtype": "fileupload", "time": "24h"}
            response = await client.post(url, data=data, files=files)
            
        if response.status_code != 200 or not response.text.startswith("https://"):
            raise UploadError(f"Litterbox upload failed: {response.text}")
            
        return response.text.strip()


async def get_public_image_url(image_path: Path) -> str:
    """
    Uploads a prepared local image file to a public host so Meta Instagram servers can access it.
    Prioritizes configured cloud accounts (Cloudinary, ImgBB) and falls back to temporary public hosts.
    """
    if not image_path.exists():
        raise FileNotFoundError(f"Image file to upload does not exist: {image_path}")
        
    errors = []
    
    # 1. Cloudinary if configured
    if settings.cloudinary_cloud_name and settings.cloudinary_api_key and settings.cloudinary_api_secret:
        try:
            return await upload_to_cloudinary(
                image_path,
                settings.cloudinary_cloud_name,
                settings.cloudinary_api_key,
                settings.cloudinary_api_secret
            )
        except Exception as e:
            errors.append(f"Cloudinary error: {e}")
            
    # 2. ImgBB if configured
    if settings.imgbb_api_key:
        try:
            return await upload_to_imgbb(image_path, settings.imgbb_api_key)
        except Exception as e:
            errors.append(f"ImgBB error: {e}")
            
    # 3. Tmpfiles fallback (zero configuration required)
    try:
        return await upload_to_tmpfiles(image_path)
    except Exception as e:
        errors.append(f"tmpfiles error: {e}")
        
    # 4. Litterbox fallback
    try:
        return await upload_to_litterbox(image_path)
    except Exception as e:
        errors.append(f"Litterbox error: {e}")
        
    raise UploadError(
        f"Failed to host image for Instagram Graph API. Errors: {'; '.join(errors)}. "
        "Tip: Set IMGBB_API_KEY or CLOUDINARY credentials in .env for dedicated image hosting."
    )

