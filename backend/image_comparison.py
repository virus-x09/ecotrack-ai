"""General-purpose visual comparison used by the EcoTrack AI dashboard."""

from io import BytesIO

import numpy as np
from PIL import Image


MATCH_THRESHOLD = 75.0
ANALYSIS_SIZE = (128, 128)


def _load_image(data: bytes) -> Image.Image:
    try:
        image = Image.open(BytesIO(data)).convert("RGB")
        if image.width < 2 or image.height < 2:
            raise ValueError("Image is too small")
        return image
    except Exception as error:
        raise ValueError("The uploaded file is not a valid image") from error


def _image_array(image: Image.Image) -> np.ndarray:
    return np.asarray(image.resize(ANALYSIS_SIZE, Image.Resampling.LANCZOS), dtype=np.float32)


def _grayscale(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114


def _edge_map(gray: np.ndarray) -> np.ndarray:
    vertical = np.abs(np.diff(gray, axis=0, prepend=gray[:1, :]))
    horizontal = np.abs(np.diff(gray, axis=1, prepend=gray[:, :1]))
    return np.clip((vertical + horizontal) / 255.0, 0.0, 1.0)


def _histogram_similarity(first: np.ndarray, second: np.ndarray) -> float:
    first_hist, _ = np.histogramdd(first.reshape(-1, 3), bins=(8, 8, 8), range=((0, 256),) * 3)
    second_hist, _ = np.histogramdd(second.reshape(-1, 3), bins=(8, 8, 8), range=((0, 256),) * 3)
    first_hist /= max(first_hist.sum(), 1)
    second_hist /= max(second_hist.sum(), 1)
    return float(np.minimum(first_hist, second_hist).sum())


def _basic_details(image: Image.Image) -> dict[str, object]:
    rgb = _image_array(image)
    gray = _grayscale(rgb)
    edges = _edge_map(gray)
    average = np.round(rgb.mean(axis=(0, 1))).astype(int).tolist()
    quantised = (rgb.astype(np.uint8) // 32) * 32 + 16
    colours, counts = np.unique(quantised.reshape(-1, 3), axis=0, return_counts=True)
    dominant = colours[int(np.argmax(counts))].astype(int).tolist()
    width, height = image.size
    return {
        "width": width, "height": height, "aspect_ratio": round(width / height, 3),
        "average_colour": {"rgb": average, "hex": "#{:02X}{:02X}{:02X}".format(*average)},
        "dominant_colour": {"rgb": dominant, "hex": "#{:02X}{:02X}{:02X}".format(*dominant)},
        "brightness": round(float(gray.mean() / 255.0 * 100), 2),
        "contrast": round(float(gray.std() / 127.5 * 100), 2),
        "edge_detail": round(float((edges > 0.12).mean() * 100), 2),
    }


def compare_image_bytes(first_bytes: bytes, second_bytes: bytes) -> dict[str, object]:
    """Return basic details and TRUE only for a 75%+ visual match."""
    first, second = _load_image(first_bytes), _load_image(second_bytes)
    first_rgb, second_rgb = _image_array(first), _image_array(second)
    appearance = 1.0 - float(np.abs(first_rgb - second_rgb).mean() / 255.0)
    detail_similarity = 1.0 - float(np.abs(_edge_map(_grayscale(first_rgb)) - _edge_map(_grayscale(second_rgb))).mean())
    first_ratio, second_ratio = first.width / first.height, second.width / second.height
    components = {
        "visual_appearance": round(max(0.0, appearance) * 100, 2),
        "colour_distribution": round(_histogram_similarity(first_rgb, second_rgb) * 100, 2),
        "image_detail": round(max(0.0, detail_similarity) * 100, 2),
        "composition": round(min(first_ratio, second_ratio) / max(first_ratio, second_ratio) * 100, 2),
    }
    similarity = round(components["visual_appearance"] * .45 + components["colour_distribution"] * .25 + components["image_detail"] * .20 + components["composition"] * .10, 2)
    match = similarity >= MATCH_THRESHOLD
    return {
        "success": True, "match": match, "similarity": similarity, "threshold": MATCH_THRESHOLD,
        "basic_details": {"image_1": _basic_details(first), "image_2": _basic_details(second)},
        "comparison": components,
        "message": "Images match at or above the 75% threshold." if match else "Images match below the 75% threshold.",
    }
