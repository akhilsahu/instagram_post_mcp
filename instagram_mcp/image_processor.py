import io
import os
import math
import base64
import uuid
from pathlib import Path
from typing import Tuple, Optional, Union
from PIL import Image, ImageOps, ImageFilter, ImageDraw, ImageFont

from instagram_mcp.config import settings

# Instagram API constraints
MIN_ASPECT_RATIO_FEED = 4 / 5  # 0.80 (portrait)
MAX_ASPECT_RATIO_FEED = 1.91 / 1  # 1.91 (landscape)
STORY_ASPECT_RATIO = 9 / 16  # 0.5625 (vertical)
MAX_FILE_SIZE_BYTES = 8 * 1024 * 1024  # 8 MB
RECOMMENDED_MAX_DIMENSION = 1920
RECOMMENDED_MIN_DIMENSION = 320


class ImageProcessingError(Exception):
    """Raised when image processing fails."""
    pass


def load_image(image_input: Union[str, bytes, Path, io.BytesIO]) -> Tuple[Image.Image, Optional[str]]:
    """
    Loads an image from a file path, base64 string, or raw bytes.
    Returns (PIL.Image, source_name).
    """
    try:
        if isinstance(image_input, (str, Path)):
            path_str = str(image_input).strip()
            # Check if it's base64 encoded
            if path_str.startswith("data:image/") or ";base64," in path_str:
                base64_data = path_str.split(";base64,")[-1]
                raw_bytes = base64.b64decode(base64_data)
                img = Image.open(io.BytesIO(raw_bytes))
                return img, "base64_image.jpg"
            
            # Check if local file exists
            file_path = Path(path_str).expanduser().resolve()
            if not file_path.exists():
                raise FileNotFoundError(f"Local image file not found: {path_str}")
            img = Image.open(file_path)
            return img, file_path.name
        
        elif isinstance(image_input, bytes):
            img = Image.open(io.BytesIO(image_input))
            return img, "memory_image.jpg"
        
        elif isinstance(image_input, io.BytesIO):
            image_input.seek(0)
            img = Image.open(image_input)
            return img, "stream_image.jpg"
        
        else:
            raise ValueError(f"Unsupported image input type: {type(image_input)}")
            
    except Exception as e:
        raise ImageProcessingError(f"Failed to load image: {e}") from e


def analyze_image(img: Image.Image) -> dict:
    """Returns metadata and aspect ratio info about the image."""
    width, height = img.size
    aspect_ratio = width / height
    
    # 0.795 to 1.915 accounts for slight integer pixel rounding
    is_valid_feed = 0.795 <= aspect_ratio <= 1.915
    is_valid_story = abs(aspect_ratio - STORY_ASPECT_RATIO) < 0.05
    
    return {
        "width": width,
        "height": height,
        "format": img.format or "UNKNOWN",
        "mode": img.mode,
        "aspect_ratio": round(aspect_ratio, 4),
        "is_valid_feed": is_valid_feed,
        "is_valid_story": is_valid_story,
        "orientation": "square" if abs(aspect_ratio - 1.0) < 0.05 else ("portrait" if aspect_ratio < 1.0 else "landscape")
    }


def to_rgb(img: Image.Image, bg_color: Tuple[int, int, int] = (255, 255, 255)) -> Image.Image:
    """Converts any PIL image mode (RGBA, P, CMYK, etc.) to RGB with background fill."""
    if img.mode == "RGB":
        return img
    
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        alpha_img = img.convert("RGBA")
        background = Image.new("RGB", alpha_img.size, bg_color)
        background.paste(alpha_img, mask=alpha_img.split()[3])
        return background
    
    return img.convert("RGB")


def pad_to_aspect_ratio(
    img: Image.Image,
    target_aspect_ratio: float,
    bg_style: str = "blur",
    bg_color: Tuple[int, int, int] = (0, 0, 0)
) -> Image.Image:
    """
    Pads an image to meet a target aspect ratio.
    bg_style: 'blur' (blurred background of original), 'black', 'white', or 'color'.
    """
    width, height = img.size
    current_ratio = width / height
    
    if abs(current_ratio - target_aspect_ratio) < 0.005:
        return img
    
    if current_ratio > target_aspect_ratio:
        # Current image is wider than target -> need to increase height (letterbox)
        new_width = width
        new_height = int(math.ceil(width / target_aspect_ratio))
    else:
        # Current image is taller than target -> need to increase width (pillarbox)
        new_height = height
        new_width = int(math.ceil(height * target_aspect_ratio))
    
    x_offset = (new_width - width) // 2
    y_offset = (new_height - height) // 2
    
    if bg_style == "blur":
        # Create a blurred stretched background from original image
        bg = img.copy().resize((new_width, new_height), Image.Resampling.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=30))
        bg.paste(img, (x_offset, y_offset))
        return bg
    else:
        color = (255, 255, 255) if bg_style == "white" else bg_color
        canvas = Image.new("RGB", (new_width, new_height), color)
        canvas.paste(img, (x_offset, y_offset))
        return canvas


def crop_to_aspect_ratio(img: Image.Image, target_aspect_ratio: float) -> Image.Image:
    """Center crops image to match the target aspect ratio."""
    width, height = img.size
    current_ratio = width / height
    
    if abs(current_ratio - target_aspect_ratio) < 0.005:
        return img
    
    if current_ratio > target_aspect_ratio:
        # Current image is too wide -> crop width
        new_width = int(round(height * target_aspect_ratio))
        offset = (width - new_width) // 2
        box = (offset, 0, offset + new_width, height)
    else:
        # Current image is too tall -> crop height
        new_height = int(round(width / target_aspect_ratio))
        offset = (height - new_height) // 2
        box = (0, offset, width, offset + new_height)
        
    return img.crop(box)


def add_caption_overlay(
    img: Image.Image,
    caption: str,
    position: str = "bottom",
    font_size: Optional[int] = None,
    text_color: Tuple[int, int, int] = (255, 255, 255)
) -> Image.Image:
    """
    Renders a stylish typographic caption banner over the image.
    Useful for Stories or branding AI artwork directly on the visual.
    """
    if not caption or not caption.strip():
        return img

    canvas = img.convert("RGBA")
    width, height = canvas.size

    # Calculate proportional font size if not provided
    calculated_size = font_size or max(24, int(width / 28))
    
    # Try system fonts (macOS / Linux / fallback)
    font = None
    system_fonts = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNS.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "Helvetica", "Arial"
    ]
    for fp in system_fonts:
        try:
            font = ImageFont.truetype(fp, calculated_size)
            break
        except Exception:
            continue
    if font is None:
        try:
            font = ImageFont.load_default(size=calculated_size)
        except Exception:
            font = ImageFont.load_default()

    # Wrap text into lines fitting within 85% of image width
    words = caption.strip().split()
    lines = []
    current_line = []
    max_text_width = int(width * 0.85)

    temp_draw = ImageDraw.Draw(canvas)
    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = temp_draw.textbbox((0, 0), test_line, font=font)
        line_w = bbox[2] - bbox[0]
        if line_w <= max_text_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))

    # Calculate total text block height
    line_spacing = int(calculated_size * 0.35)
    total_text_height = len(lines) * calculated_size + (len(lines) - 1) * line_spacing
    banner_padding = int(calculated_size * 0.8)
    banner_height = total_text_height + (banner_padding * 2)

    # Determine Y position of the banner
    if position == "top":
        banner_top = int(height * 0.08)
    elif position == "center":
        banner_top = (height - banner_height) // 2
    else:  # bottom
        banner_top = height - banner_height - int(height * 0.08)

    # Draw semi-transparent dark backdrop for legibility
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    
    # Rounded rectangle banner
    banner_margin = int(width * 0.05)
    overlay_draw.rounded_rectangle(
        [banner_margin, banner_top, width - banner_margin, banner_top + banner_height],
        radius=16,
        fill=(15, 15, 20, 185)
    )

    # Render lines of text centered
    curr_y = banner_top + banner_padding
    for line in lines:
        bbox = overlay_draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        lx = (width - lw) // 2
        overlay_draw.text((lx, curr_y), line, fill=(*text_color, 255), font=font)
        curr_y += calculated_size + line_spacing

    # Composite overlay onto canvas and convert back to RGB
    combined = Image.alpha_composite(canvas, overlay)
    return combined.convert("RGB")


def prepare_for_instagram(
    image_input: Union[str, bytes, Path, io.BytesIO],
    target_type: str = "feed",
    fit_mode: str = "pad",
    bg_style: str = "blur",
    caption_overlay: Optional[str] = None,
    output_path: Optional[Union[str, Path]] = None,
    quality: int = 95
) -> Path:
    """
    Prepares any image (including AI generated ones) for Instagram publishing:
    1. Converts format to RGB JPEG
    2. Adjusts aspect ratio (feed: 0.8 - 1.91, story: 9:16)
    3. Optionally renders a typographic caption overlay onto the image
    4. Resizes if exceeds maximum dimensions
    5. Compresses if size > 8MB
    6. Saves as a clean JPEG ready for Graph API upload.
    
    Returns the Path to the processed image file.
    """
    img, src_name = load_image(image_input)
    img = ImageOps.exif_transpose(img)  # Respect EXIF rotation
    img = to_rgb(img)
    
    width, height = img.size
    aspect_ratio = width / height
    
    if target_type == "story":
        target_ratio = STORY_ASPECT_RATIO
        if abs(aspect_ratio - target_ratio) >= 0.01:
            if fit_mode == "crop":
                img = crop_to_aspect_ratio(img, target_ratio)
            else:
                img = pad_to_aspect_ratio(img, target_ratio, bg_style=bg_style)
    else:
        # Feed post: aspect ratio must be between 0.8 and 1.91
        if aspect_ratio < MIN_ASPECT_RATIO_FEED:
            # Too tall: make it 4:5 (0.80)
            if fit_mode == "crop":
                img = crop_to_aspect_ratio(img, MIN_ASPECT_RATIO_FEED)
            else:
                img = pad_to_aspect_ratio(img, MIN_ASPECT_RATIO_FEED, bg_style=bg_style)
        elif aspect_ratio > MAX_ASPECT_RATIO_FEED:
            # Too wide: make it 1.91:1
            if fit_mode == "crop":
                img = crop_to_aspect_ratio(img, MAX_ASPECT_RATIO_FEED)
            else:
                img = pad_to_aspect_ratio(img, MAX_ASPECT_RATIO_FEED, bg_style=bg_style)
    
    # Apply optional typographic caption overlay
    if caption_overlay:
        img = add_caption_overlay(img, caption_overlay)

    # Scale down if dimensions are excessively large (e.g. > 2160px)
    max_dim = max(img.size)
    if max_dim > RECOMMENDED_MAX_DIMENSION:
        scale = RECOMMENDED_MAX_DIMENSION / max_dim
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    
    # Scale up if smaller than minimum required by Instagram (320px)
    min_dim = min(img.size)
    if min_dim < RECOMMENDED_MIN_DIMENSION:
        scale = RECOMMENDED_MIN_DIMENSION / min_dim
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    
    # Determine destination file path
    if output_path:
        dest_path = Path(output_path).expanduser().resolve()
        dest_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        uid = uuid.uuid4().hex[:10]
        dest_path = settings.temp_dir / f"ig_ready_{uid}.jpg"
    
    # Save as JPEG with size check (< 8MB)
    current_quality = quality
    while current_quality >= 60:
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=current_quality, optimize=True)
        size = buffer.tell()
        if size <= MAX_FILE_SIZE_BYTES:
            with open(dest_path, "wb") as f:
                f.write(buffer.getvalue())
            return dest_path
        current_quality -= 10
    
    # If still too large, resize by 75% and save
    img = img.resize((int(img.width * 0.75), int(img.height * 0.75)), Image.Resampling.LANCZOS)
    img.save(dest_path, format="JPEG", quality=80, optimize=True)
    return dest_path
