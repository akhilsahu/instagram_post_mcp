import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Search for .env in current working dir or package root
env_path = Path.cwd() / ".env"
if not env_path.exists():
    env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


@dataclass
class Settings:
    # Instagram Meta Graph API Credentials
    access_token: str = os.getenv("INSTAGRAM_ACCESS_TOKEN", "").strip()
    account_id: str = os.getenv("INSTAGRAM_ACCOUNT_ID", "").strip()
    api_version: str = os.getenv("GRAPH_API_VERSION", "v21.0").strip()

    # Optional Cloud Hosting for local images
    imgbb_api_key: Optional[str] = os.getenv("IMGBB_API_KEY", "").strip() or None
    cloudinary_cloud_name: Optional[str] = os.getenv("CLOUDINARY_CLOUD_NAME", "").strip() or None
    cloudinary_api_key: Optional[str] = os.getenv("CLOUDINARY_API_KEY", "").strip() or None
    cloudinary_api_secret: Optional[str] = os.getenv("CLOUDINARY_API_SECRET", "").strip() or None

    # Processing configuration
    auto_format_images: bool = os.getenv("AUTO_FORMAT_IMAGES", "true").lower() in ("true", "1", "yes")
    temp_dir: Path = Path(os.getenv("INSTA_TEMP_DIR", "/tmp/insta_mcp"))

    def validate_meta_credentials(self) -> None:
        """Check if minimum required credentials for Graph API are present."""
        if not self.access_token:
            raise ValueError(
                "INSTAGRAM_ACCESS_TOKEN is not set. Please set it in your .env file or environment variables."
            )


settings = Settings()
settings.temp_dir.mkdir(parents=True, exist_ok=True)
