import asyncio
import json
from typing import Optional, Dict, Any, List
import httpx

from instagram_mcp.config import settings


class InstagramAPIError(Exception):
    """Raised when Instagram Graph API returns an error."""
    def __init__(self, message: str, code: Optional[int] = None, subcode: Optional[int] = None, raw_response: Optional[dict] = None):
        super().__init__(message)
        self.code = code
        self.subcode = subcode
        self.raw_response = raw_response


class InstagramClient:
    """Async client for Instagram Graph API."""

    def __init__(
        self,
        access_token: Optional[str] = None,
        account_id: Optional[str] = None,
        api_version: Optional[str] = None
    ):
        self.access_token = access_token or settings.access_token
        self.account_id = account_id or settings.account_id
        self.api_version = api_version or settings.api_version
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    def _ensure_token(self) -> None:
        if not self.access_token:
            raise InstagramAPIError(
                "INSTAGRAM_ACCESS_TOKEN is missing. Please set it in your .env file."
            )

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        timeout: float = 60.0
    ) -> Dict[str, Any]:
        """Make an authenticated request to the Meta Graph API."""
        self._ensure_token()
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        query_params = dict(params or {})
        query_params["access_token"] = self.access_token

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.request(method, url, params=query_params, data=data)

        try:
            res_json = resp.json()
        except Exception:
            raise InstagramAPIError(
                f"HTTP {resp.status_code} Non-JSON response: {resp.text}"
            )

        if "error" in res_json:
            err = res_json["error"]
            err_msg = err.get("message", "Unknown error")
            err_code = err.get("code")
            err_subcode = err.get("error_subcode")
            type_info = err.get("type", "OAuthException")
            
            help_hint = ""
            if err_code == 190:
                help_hint = " (Your Access Token has expired or is invalid. Please generate a new Long-lived Token)."
            elif err_code == 200:
                help_hint = " (Permission denied. Make sure token has 'instagram_content_publish' and 'instagram_basic' scopes)."
            elif "aspect ratio" in err_msg.lower():
                help_hint = " (Aspect ratio invalid. Must be between 4:5 and 1.91:1)."

            raise InstagramAPIError(
                f"[{type_info}] {err_msg}{help_hint}",
                code=err_code,
                subcode=err_subcode,
                raw_response=res_json
            )

        if resp.status_code >= 400:
            raise InstagramAPIError(f"HTTP {resp.status_code} Error: {resp.text}")

        return res_json

    async def list_available_instagram_accounts(self) -> List[Dict[str, Any]]:
        """
        Discovers all Instagram Business/Creator accounts accessible with this token.
        Supports both Page tokens and User tokens.
        """
        self._ensure_token()
        found_accounts: Dict[str, Dict[str, Any]] = {}

        # Strategy 1: Inspect token via /debug_token to get scoped target IDs
        try:
            debug_res = await self._request(
                "GET",
                "debug_token",
                params={"input_token": self.access_token}
            )
            data = debug_res.get("data", {})
            for scope_info in data.get("granular_scopes", []):
                if scope_info.get("scope") in ("instagram_content_publish", "instagram_basic"):
                    for target_id in scope_info.get("target_ids", []):
                        if target_id not in found_accounts:
                            found_accounts[target_id] = {"id": target_id}
        except Exception:
            pass

        # Strategy 2: Query /me/accounts (works when token is a User token)
        try:
            res = await self._request("GET", "me/accounts", params={"fields": "id,name,instagram_business_account{id,username}"})
            for page in res.get("data", []):
                ig = page.get("instagram_business_account")
                if ig and "id" in ig:
                    found_accounts[ig["id"]] = {"id": ig["id"], "username": ig.get("username")}
        except Exception:
            pass

        # Enrich accounts with profile info
        results = []
        for account_id in found_accounts:
            try:
                profile = await self._request("GET", account_id, params={"fields": "id,username,name,followers_count,media_count"})
                results.append(profile)
            except Exception:
                results.append({"id": account_id, "username": "unknown"})

        return results

    async def get_account_id(self) -> str:
        """
        Returns the Instagram Business/Creator Account ID.
        If not set in .env, automatically discovers it from the access token.
        """
        if self.account_id:
            return self.account_id

        accounts = await self.list_available_instagram_accounts()
        if not accounts:
            raise InstagramAPIError(
                "Could not auto-detect an Instagram Business/Creator Account ID for this token. "
                "Ensure your Instagram account is switched to Business or Creator and connected to a Facebook Page, "
                "or specify INSTAGRAM_ACCOUNT_ID in your .env file."
            )

        # Cache the first detected account ID
        self.account_id = accounts[0]["id"]
        return self.account_id

    async def get_profile(self) -> Dict[str, Any]:
        """Fetch details about the connected Instagram account."""
        account_id = await self.get_account_id()
        fields = "id,username,name,profile_picture_url,biography,followers_count,follows_count,media_count"
        return await self._request("GET", account_id, params={"fields": fields})

    async def create_image_container(
        self,
        image_url: str,
        caption: Optional[str] = None,
        is_carousel_item: bool = False,
        location_id: Optional[str] = None,
        user_tags: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Creates a media container for a single image.
        Returns the container creation ID.
        """
        account_id = await self.get_account_id()
        payload: Dict[str, Any] = {
            "image_url": image_url
        }

        if caption and not is_carousel_item:
            payload["caption"] = caption
        if is_carousel_item:
            payload["is_carousel_item"] = "true"
        if location_id:
            payload["location_id"] = location_id
        if user_tags:
            payload["user_tags"] = json.dumps(user_tags)

        res = await self._request("POST", f"{account_id}/media", data=payload)
        return res["id"]

    async def create_story_container(self, image_url: str) -> str:
        """
        Creates a media container for an Instagram Story.
        Returns the container creation ID.
        """
        account_id = await self.get_account_id()
        payload = {
            "image_url": image_url,
            "media_type": "STORIES"
        }
        res = await self._request("POST", f"{account_id}/media", data=payload)
        return res["id"]

    async def create_carousel_container(
        self,
        item_container_ids: List[str],
        caption: Optional[str] = None,
        location_id: Optional[str] = None
    ) -> str:
        """
        Creates a parent carousel container linking multiple item containers.
        Returns the carousel container creation ID.
        """
        if len(item_container_ids) < 2:
            raise ValueError("Carousel posts require at least 2 images.")
        if len(item_container_ids) > 10:
            raise ValueError("Instagram carousels support a maximum of 10 items.")

        account_id = await self.get_account_id()
        payload: Dict[str, Any] = {
            "media_type": "CAROUSEL",
            "children": ",".join(item_container_ids)
        }
        if caption:
            payload["caption"] = caption
        if location_id:
            payload["location_id"] = location_id

        res = await self._request("POST", f"{account_id}/media", data=payload)
        return res["id"]

    async def wait_for_container(
        self,
        creation_id: str,
        timeout_seconds: int = 60,
        poll_interval: float = 2.0
    ) -> str:
        """
        Polls container status until it is FINISHED and ready to publish.
        """
        elapsed = 0.0
        while elapsed < timeout_seconds:
            res = await self._request(
                "GET",
                creation_id,
                params={"fields": "status_code,status"}
            )
            status_code = res.get("status_code", "").upper()

            if status_code in ("FINISHED", "PUBLISHED"):
                return status_code
            elif status_code == "ERROR":
                err_detail = res.get("status", "Container processing failed")
                raise InstagramAPIError(f"Container failed processing: {err_detail}", raw_response=res)
            elif status_code == "EXPIRED":
                raise InstagramAPIError("Container expired before publishing.", raw_response=res)

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        # If image, sometimes status_code is already ready without explicit polling
        return "FINISHED"

    async def publish_container(self, creation_id: str) -> str:
        """
        Publishes the media container to the Instagram account.
        Returns published media ID.
        """
        account_id = await self.get_account_id()
        res = await self._request(
            "POST",
            f"{account_id}/media_publish",
            data={"creation_id": creation_id}
        )
        return res["id"]

    async def get_media_details(self, media_id: str) -> Dict[str, Any]:
        """Fetch published media permalink, caption, and metrics."""
        fields = "id,caption,media_type,media_url,permalink,timestamp,like_count,comments_count"
        return await self._request("GET", media_id, params={"fields": fields})

    async def get_recent_posts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch the most recent posts published to this account."""
        account_id = await self.get_account_id()
        fields = "id,caption,media_type,media_url,permalink,timestamp,like_count,comments_count"
        res = await self._request(
            "GET",
            f"{account_id}/media",
            params={"fields": fields, "limit": limit}
        )
        return res.get("data", [])

