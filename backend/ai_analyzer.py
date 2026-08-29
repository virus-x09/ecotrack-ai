import json
import os
from typing import Any
from urllib.request import Request, urlopen

from PIL import Image
from io import BytesIO


AI_ENDPOINT = os.getenv("ECOTRACK_AI_ENDPOINT")


def _local_analysis(image_bytes: bytes, filename: str) -> dict[str, Any]:
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image.verify()
    except Exception as error:
        raise ValueError("The uploaded file is not a valid image") from error

    name = filename.lower()
    category = "other_plastic"
    for keyword, detected_category in {
        "bottle": "bottle",
        "bag": "bag",
        "wrapper": "wrapper",
        "container": "container",
    }.items():
        if keyword in name:
            category = detected_category
            break
    return {
        "ai_result": "plastic_detected",
        "category": category,
        "confidence": 0.62,
        "provider": "local-prototype",
    }


def analyze_image(image_bytes: bytes, filename: str) -> dict[str, Any]:
    if not AI_ENDPOINT:
        return _local_analysis(image_bytes, filename)

    request = Request(
        AI_ENDPOINT,
        data=image_bytes,
        headers={"Content-Type": "application/octet-stream", "X-Filename": filename},
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode())
        if not isinstance(result, dict) or "ai_result" not in result or "category" not in result:
            raise ValueError("AI service returned an invalid response")
        result["provider"] = "external"
        return result
    except Exception:
        return _local_analysis(image_bytes, filename)
