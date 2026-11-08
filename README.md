# Instagram Publishing MCP Server 📸🤖

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that allows AI agents to directly post AI-generated images, carousels, and stories to an Instagram Business or Creator account using the official Meta Graph API.

---

## ✨ Features

- **Built for AI Images**: AI image generators often produce PNGs or non-standard aspect ratios. The server automatically:
  - Formats aspect ratios to meet Instagram feed limits (between `4:5` portrait and `1.91:1` landscape).
  - Offers padding with blurred background borders or smart center-cropping.
  - Converts transparency/RGBA to RGB JPEG.
  - Compresses images if they exceed Meta's 8MB limit.
- **Seamless Local Image Support**: Meta Graph API requires public HTTPS URLs. This server handles local file paths (e.g. `/tmp/artwork.png`), base64 data, or URLs with zero hassle:
  - **Zero-config fallback**: Uses a temporary public host out-of-the-box.
  - **Custom cloud storage**: Direct integration with ImgBB or Cloudinary.
- **Multiple Post Formats**:
  - **Single Photo Posts**: Feed images with rich captions, hashtags, and location tagging.
  - **Carousels**: Multi-image posts (2 to 10 images) with sequential processing.
  - **Stories**: Vertical (9:16) format expiring after 24 hours.
- **Auto-Discovery**: If `INSTAGRAM_ACCOUNT_ID` is omitted, the server automatically queries connected Facebook Pages and locates the linked Instagram account.
- **Diagnostic & Preview Tools**: AI agents can inspect and validate image formatting before posting.

---

## 🛠️ MCP Tools Exposed to AI Agents

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `post_image` | Publish a single image to Instagram feed | `image_source`, `caption`, `caption_overlay`, `auto_format`, `fit_mode`, `dry_run` |
| `post_carousel` | Publish 2–10 images as a swipeable carousel | `images`, `caption`, `caption_overlay`, `auto_format`, `fit_mode`, `dry_run` |
| `post_story` | Publish an image to Instagram Stories (9:16) | `image_source`, `caption`, `caption_overlay`, `auto_format`, `fit_mode`, `dry_run` |
| `format_caption` | Format and validate caption & hashtags (2,200 char limit) | `text`, `hashtags`, `call_to_action` |
| `format_and_preview_image` | Validate & prepare image locally without publishing | `image_source`, `caption_overlay`, `target_type`, `fit_mode`, `output_path` |
| `get_instagram_profile` | Get connected Instagram account details | *None* |
| `get_recent_posts` | Retrieve recent published posts and metrics | `limit` (default: 10) |
| `check_setup_status` | Verify credentials and server health | *None* |

---

## 🚀 Quick Start

### 1. Requirements
- Python 3.10+
- Instagram Professional (Business or Creator) account
- Facebook Page connected to the Instagram account
- Meta Developer App with Instagram Graph API permissions

### 2. Setup Meta Credentials (5 Minutes)

1. **Switch your Instagram account to Professional**:
   - In Instagram Mobile App: Go to **Settings & Privacy** > **Account type and tools** > **Switch to professional account** (Business or Creator).
2. **Link to a Facebook Page**:
   - In your Instagram profile, tap **Edit profile** > **Page** > Connect or create a Facebook Page.
3. **Create a Meta Developer App**:
   - Go to [developers.facebook.com](https://developers.facebook.com/) and click **Create App**.
   - Select **Other** > **Business**.
   - Add the **Instagram Graph API** product.
4. **Generate Access Token**:
   - Open the **[Graph API Explorer](https://developers.facebook.com/tools/explorer/)**.
   - Select your Meta App.
   - In **User or Page**, select **User Token** or your Facebook Page.
   - Add the following permissions:
     - `instagram_content_publish`
     - `instagram_basic`
     - `pages_show_list`
     - `pages_read_engagement`
   - Click **Generate Access Token**.
   - *(Recommended)* Convert it into a 60-day Long-Lived Token using the Access Token Tool or Meta Developer documentation.

### 3. Configure the MCP Server

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Edit `.env`:
```env
# Required: Your Meta Access Token
INSTAGRAM_ACCESS_TOKEN=EAAG...your_token_here

# Optional: Auto-detected if left empty
INSTAGRAM_ACCOUNT_ID=

# Optional: Dedicated image host (tmpfiles.org used automatically if left empty)
IMGBB_API_KEY=
# or
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
```

### 4. Verify Setup

Run the diagnostics script:
```bash
./.venv/bin/python verify_setup.py
```
This tests:
- Meta API connectivity & token permissions
- Linked Instagram Business accounts
- Image formatting pipeline
- Image hosting reachability

---

## 🔌 Connecting to MCP Clients

### Claude Desktop
Add this to your `claude_desktop_config.json` (typically at `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "instagram": {
      "command": "/Users/aks/Projects/insta_post_mcp/.venv/bin/python",
      "args": ["/Users/aks/Projects/insta_post_mcp/run_server.py"],
      "env": {
        "INSTAGRAM_ACCESS_TOKEN": "your_token_here"
      }
    }
  }
}
```

### Antigravity / Cursor / Custom Agent
Configure command:
- **Command**: `/path/to/insta_post_mcp/.venv/bin/python`
- **Args**: `["/path/to/insta_post_mcp/run_server.py"]`

---

## 💡 How an AI Agent Uses It

When an AI agent generates an image (e.g., using Midjourney, Imagen, DALL-E, or local Stable Diffusion):

1. **Single Image Post**:
   ```json
   {
     "image_source": "/Users/aks/images/cyberpunk_cat.png",
     "caption": "A futuristic feline wandering neon streets. 🐾✨ #Cyberpunk #AIGenerated #DigitalArt",
     "auto_format": true,
     "fit_mode": "pad"
   }
   ```
   *The server formats the image to valid feed aspect ratio, uploads it to temporary public storage, creates the container on Meta, and publishes the post.*

2. **Carousel Post**:
   ```json
   {
     "images": [
       "/Users/aks/images/slide1.png",
       "/Users/aks/images/slide2.png",
       "/Users/aks/images/slide3.png"
     ],
     "caption": "Series of three conceptual renders. Swipe to see the progression! 👉"
   }
   ```

3. **Instagram Story**:
   ```json
   {
     "image_source": "/Users/aks/images/daily_quote.png",
     "auto_format": true,
     "fit_mode": "crop"
   }
   ```

---

## 📂 Project Structure

```
insta_post_mcp/
├── .env.example                 # Environment configuration template
├── .gitignore                   # Git ignore file
├── pyproject.toml               # Package configuration
├── requirements.txt             # Python dependencies
├── run_server.py                # Executable entrypoint for MCP clients
├── verify_setup.py              # CLI diagnostic test script
├── README.md                    # Documentation
└── instagram_mcp/
    ├── __init__.py
    ├── config.py                # Environment and settings loader
    ├── image_processor.py       # Aspect ratio formatter, PIL resizer & converter
    ├── uploader.py              # Temporary & cloud image hosting adapters
    ├── instagram_client.py      # Meta Instagram Graph API client
    └── server.py                # FastMCP server & tool definitions
```

