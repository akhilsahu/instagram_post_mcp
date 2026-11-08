# Instagram Publishing MCP Server 📸🤖

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that allows AI agents to directly post AI-generated images, carousels, and stories to an Instagram Business or Creator account using the official Meta Graph API.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP Specification](https://img.shields.io/badge/MCP-2024--11--05-green.svg)](https://modelcontextprotocol.io/)

---

## 📑 Table of Contents
- [✨ Key Features](#-key-features)
- [🛠️ MCP Tools Exposed to AI Agents](#️-mcp-tools-exposed-to-ai-agents)
- [🔑 Complete Guide: Generating Your Instagram Access Token](#-complete-guide-generating-your-instagram-access-token)
  - [Step 1: Switch to an Instagram Professional Account](#step-1-switch-to-an-instagram-professional-account)
  - [Step 2: Connect Instagram to a Facebook Page](#step-2-connect-instagram-to-a-facebook-page)
  - [Step 3: Create a Meta Developer App](#step-3-create-a-meta-developer-app)
  - [Step 4: Generate Your Access Token in Graph API Explorer](#step-4-generate-your-access-token-in-graph-api-explorer)
  - [Step 5: Convert to a 60-Day Long-Lived Token](#step-5-convert-to-a-60-day-long-lived-token)
- [⚙️ Local Installation & Configuration](#️-local-installation--configuration)
- [🔌 Setting Up the MCP in Every Client / App](#-setting-up-the-mcp-in-every-client--app)
  - [1. Google Gemini / Antigravity IDE](#1-google-gemini--antigravity-ide)
  - [2. Claude Desktop](#2-claude-desktop)
  - [3. Cursor IDE](#3-cursor-ide)
  - [4. Windsurf IDE](#4-windsurf-ide)
  - [5. Custom Python Agents (LangChain, CrewAI, AutoGen)](#5-custom-python-agents-langchain-crewai-autogen)
- [🧪 Testing Your Setup](#-testing-your-setup)
- [💡 How an AI Agent Uses It](#-how-an-ai-agent-uses-it)
- [📂 Project Structure](#-project-structure)

---

## ✨ Key Features

- **Built for AI Images**: AI image generators often output PNGs, non-standard dimensions, or huge files. This server automatically:
  - Adjusts aspect ratios to valid Instagram feed boundaries (between **4:5 (0.80)** portrait and **1.91:1** landscape).
  - Offers **smart padding** (with a stylish blurred background of the artwork) or **center-cropping**.
  - Converts RGBA transparency to Instagram-compliant RGB JPEG.
  - Compresses images if they exceed Meta's 8MB limit.
- **Typographic Caption Overlays**: Render clean lower-third typographic banners directly onto your image visual (crucial for Instagram Stories, which do not have native API caption fields).
- **Seamless Local File Support**: Meta Graph API strictly requires public HTTPS URLs. This server handles local files (`/path/to/artwork.png`), base64 strings, or remote URLs:
  - **Zero-config fallback**: Uses temporary public hosting out-of-the-box (`tmpfiles.org` / `litterbox`).
  - **Dedicated storage**: Direct integration with [ImgBB](https://api.imgbb.com/) or [Cloudinary](https://cloudinary.com/).
- **Multi-Account Auto-Discovery**: Automatically discovers all linked Instagram accounts from your token without needing manual ID lookups.
- **Multiple Post Formats**: Single photo posts, multi-image carousels (2–10 images), and 9:16 vertical stories.
- **Dry-Run Simulation**: Test your entire agent pipeline end-to-end safely without publishing live posts.

---

## 🛠️ MCP Tools Exposed to AI Agents

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `post_image` | Publish a single image to Instagram feed | `image_source`, `caption`, `caption_overlay`, `auto_format`, `fit_mode`, `dry_run` |
| `post_carousel` | Publish 2–10 images as a swipeable carousel | `images`, `caption`, `caption_overlay`, `auto_format`, `fit_mode`, `dry_run` |
| `post_story` | Publish an image to Instagram Stories (9:16) | `image_source`, `caption`, `caption_overlay`, `auto_format`, `fit_mode`, `dry_run` |
| `format_caption` | Format & validate caption and hashtags (2,200 char limit) | `text`, `hashtags`, `call_to_action` |
| `format_and_preview_image` | Validate & prepare image locally without publishing | `image_source`, `caption_overlay`, `target_type`, `fit_mode`, `output_path` |
| `get_instagram_profile` | Get connected Instagram account details | *None* |
| `get_recent_posts` | Retrieve recent published posts and metrics | `limit` (default: 10) |
| `check_setup_status` | Verify credentials and server health | *None* |

---

## 🔑 Complete Guide: Generating Your Instagram Access Token

Instagram Graph API only allows publishing from **Professional (Business or Creator)** accounts connected to a **Facebook Page**. Personal accounts cannot publish via API.

Follow these 5 steps to get your token:

### Step 1: Switch to an Instagram Professional Account
1. Open the Instagram app on your mobile device.
2. Go to your **Profile** > Tap the **Menu (☰)** in top right > **Settings and privacy**.
3. Scroll down to **Account type and tools** > Tap **Switch to professional account**.
4. Choose **Creator** or **Business** and follow the prompts.

### Step 2: Connect Instagram to a Facebook Page
1. On your Instagram profile, tap **Edit Profile**.
2. Under **Public Business Information**, tap **Page**.
3. Choose **Create Facebook Page** or connect an existing Facebook Page you manage.

### Step 3: Create a Meta Developer App
1. Go to [developers.facebook.com](https://developers.facebook.com/) and log in with your Facebook account.
2. Click **My Apps** > **Create App**.
3. When asked "What do you want your app to do?", select **Other** > Click **Next**.
4. Select App Type: **Business** > Click **Next**.
5. Give your App a name (e.g. `My AI Poster`) and enter your email > Click **Create app**.
6. On your App Dashboard under **Add products to your app**, find **Instagram Graph API** and click **Set Up**.

### Step 4: Generate Your Access Token in Graph API Explorer
1. Navigate to the **[Meta Graph API Explorer](https://developers.facebook.com/tools/explorer/)**.
2. In the top right dropdowns:
   - **Meta App**: Select the app you just created.
   - **User or Page**: Select **User Token** (or select your Facebook Page).
3. Under **Permissions**, add these 4 required permissions:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_show_list`
   - `pages_read_engagement`
4. Click **Generate Access Token**.
5. A Facebook authentication popup will appear:
   - Check the Facebook Page linked to your Instagram.
   - Check your Instagram Business/Creator account.
   - Grant all requested permissions and click **Done**.
6. Copy the generated Access Token from the **Access Token** field.

### Step 5: Convert to a 60-Day Long-Lived Token
Tokens generated in the Explorer expire in 1-2 hours. To generate a 60-day token:
1. Open the **[Access Token Debugger](https://developers.facebook.com/tools/debug/accesstoken/)**.
2. Paste your short-lived token and click **Debug**.
3. Scroll down and click **Extend Access Token**.
4. A new **Long-Lived Token** (valid for 60 days) will be generated. Copy this token for your `.env`.

*(Alternatively, via curl)*:
```bash
curl -i -X GET "https://graph.facebook.com/v21.0/oauth/access_token?\
grant_type=fb_exchange_token&\
client_id=YOUR_META_APP_ID&\
client_secret=YOUR_META_APP_SECRET&\
fb_exchange_token=YOUR_SHORT_LIVED_TOKEN"
```

---

## ⚙️ Local Installation & Configuration

### 1. Clone & Set Up Virtual Environment
```bash
git clone https://github.com/akhilsahu/instagram_post_mcp.git
cd instagram_post_mcp

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment (`.env`)
Copy the example file:
```bash
cp .env.example .env
```

Open `.env` and fill in your token:
```env
# REQUIRED: Your Meta Access Token
INSTAGRAM_ACCESS_TOKEN=EAAV...your_token_here

# OPTIONAL: Leave empty to auto-detect account, or specify an ID
INSTAGRAM_ACCOUNT_ID=

# OPTIONAL: Default caption used when an agent omits the caption parameter
DEFAULT_CAPTION=Created with AI ✨ #AIArt #DigitalArt #CreativeAI

# OPTIONAL: Dedicated image hosting (tmpfiles.org used automatically if empty)
IMGBB_API_KEY=
# or
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
```

---

## 🔌 Setting Up the MCP in Every Client / App

Replace `/PATH/TO/instagram_post_mcp` with the absolute path to your cloned repository (e.g. `/Users/aks/Projects/insta_post_mcp`).

### 1. Google Gemini / Antigravity IDE

Antigravity loads MCP servers from `~/.gemini/config/mcp_config.json`.

1. Open or create `~/.gemini/config/mcp_config.json`:
   ```bash
   nano ~/.gemini/config/mcp_config.json
   ```
2. Add the `instagram` server entry:
   ```json
   {
     "mcpServers": {
       "instagram": {
         "command": "/PATH/TO/instagram_post_mcp/.venv/bin/python",
         "args": [
           "/PATH/TO/instagram_post_mcp/run_server.py"
         ]
       }
     }
   }
   ```
3. Restart or reload Gemini. The agent will now discover `post_image`, `post_carousel`, `post_story`, etc.

---

### 2. Claude Desktop

#### macOS:
Open `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "instagram": {
      "command": "/PATH/TO/instagram_post_mcp/.venv/bin/python",
      "args": [
        "/PATH/TO/instagram_post_mcp/run_server.py"
      ]
    }
  }
}
```

#### Windows:
Open `%APPDATA%\Claude\claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "instagram": {
      "command": "C:\\PATH\\TO\\instagram_post_mcp\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\PATH\\TO\\instagram_post_mcp\\run_server.py"
      ]
    }
  }
}
```
*Completely quit and restart Claude Desktop to load the tools.*

---

### 3. Cursor IDE

#### Method A: Via Workspace File (Recommended)
Create `.cursor/mcp.json` inside your project root:
```json
{
  "mcpServers": {
    "instagram": {
      "command": "/PATH/TO/instagram_post_mcp/.venv/bin/python",
      "args": [
        "/PATH/TO/instagram_post_mcp/run_server.py"
      ]
    }
  }
}
```

#### Method B: Via Settings UI
1. Open Cursor **Settings** (`Cmd+,` or `Ctrl+,`).
2. Go to **Features** > **MCP**.
3. Click **+ Add New MCP Server**:
   - **Name**: `instagram`
   - **Type**: `command`
   - **Command**: `/PATH/TO/instagram_post_mcp/.venv/bin/python /PATH/TO/instagram_post_mcp/run_server.py`

---

### 4. Windsurf IDE

Open `~/.codeium/windsurf/mcp_config.json` and add:
```json
{
  "mcpServers": {
    "instagram": {
      "command": "/PATH/TO/instagram_post_mcp/.venv/bin/python",
      "args": [
        "/PATH/TO/instagram_post_mcp/run_server.py"
      ]
    }
  }
}
```

---

### 5. Custom Python Agents (LangChain, CrewAI, AutoGen)

You can launch and connect to the server programmatically via stdio:

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run():
    server_params = StdioServerParameters(
        command="/PATH/TO/instagram_post_mcp/.venv/bin/python",
        args=["/PATH/TO/instagram_post_mcp/run_server.py"],
        env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # List available tools
            tools = await session.list_tools()
            print("Available tools:", [t.name for t in tools.tools])

            # Call post_image tool
            result = await session.call_tool("post_image", {
                "image_source": "/path/to/my_image.png",
                "caption": "Generative digital art #AIArt #DigitalArt",
                "auto_format": True
            })
            print(result)

asyncio.run(run())
```

---

## 🧪 Testing Your Setup

The repository includes diagnostic utilities:

### 1. Verify Credentials & Accounts
Tests API connectivity, token permissions, and image hosting reachability:
```bash
./.venv/bin/python verify_setup.py
```

### 2. Dry-Run Publishing Test
Simulates an image formatting and posting flow without touching your live account:
```bash
./.venv/bin/python publish_test_post.py --dry-run
```

### 3. Live Test Post
Publishes a real test graphic to your Instagram feed:
```bash
./.venv/bin/python publish_test_post.py --caption "Hello world from Instagram MCP! 🤖✨"
```

---

## 💡 How an AI Agent Uses It

### 1. Single Feed Image Post
```json
{
  "image_source": "/Users/aks/images/cyberpunk_cat.png",
  "caption": "A futuristic feline wandering neon streets. 🐾✨\n\n#Cyberpunk #AIGenerated #DigitalArt",
  "auto_format": true,
  "fit_mode": "pad"
}
```

### 2. Multi-Image Carousel
```json
{
  "images": [
    "/Users/aks/images/slide1.png",
    "/Users/aks/images/slide2.png",
    "/Users/aks/images/slide3.png"
  ],
  "caption": "3-stage conceptual rendering progression. Swipe to explore! 👉"
}
```

### 3. Instagram Story (with Typographic Overlay)
```json
{
  "image_source": "/Users/aks/images/morning_render.png",
  "caption": "Daily Inspiration ✨ #StoryOfTheDay",
  "auto_format": true,
  "fit_mode": "crop"
}
```

---

## 📂 Project Structure

```
instagram_post_mcp/
├── .env.example                 # Environment configuration template
├── .gitignore                   # Safe git ignore rules (never commits .env)
├── pyproject.toml               # Package configuration
├── requirements.txt             # Python dependencies
├── run_server.py                # Executable stdio entrypoint for MCP clients
├── verify_setup.py              # CLI diagnostic test script
├── publish_test_post.py         # Test publishing helper script
├── example_agent_workflow.py    # End-to-end agent workflow simulation
├── README.md                    # Documentation
└── instagram_mcp/
    ├── __init__.py
    ├── config.py                # Environment and settings loader
    ├── image_processor.py       # Aspect ratio formatter, PIL resizer & text overlay
    ├── uploader.py              # Temporary & cloud image hosting adapters
    ├── instagram_client.py      # Meta Instagram Graph API client
    └── server.py                # FastMCP server & tool definitions
```

---

## 📄 License
MIT License. Free to use and integrate into personal, commercial, or agentic applications.
