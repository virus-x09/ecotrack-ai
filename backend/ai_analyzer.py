import json
import os
from typing import Any
from urllib.request import Request, urlopen

from PIL import Image
from io import BytesIO


AI_ENDPOINT = os.getenv("ECOTRACK_AI_ENDPOINT")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


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


def _gemini_analysis(image_bytes: bytes, filename: str) -> dict[str, Any]:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = """
    Analyze the uploaded image and determine if plastic waste is present.
    If plastic waste is present, classify it into one of the following categories:
    - bottle
    - bag
    - wrapper
    - container
    - other_plastic
    
    If no plastic waste is present, set ai_result to 'no_plastic_detected' and category to 'none'.
    If plastic waste is present, set ai_result to 'plastic_detected' and use one of the specified categories.
    Estimate your confidence between 0.0 and 1.0.
    
    Respond STRICTLY in the following JSON format without any markdown wrappers:
    {
      "ai_result": "plastic_detected",
      "category": "bottle",
      "confidence": 0.95
    }
    """
    
    # Guess mime type from filename
    mime_type = "image/jpeg"
    lower_name = filename.lower()
    if lower_name.endswith(".png"):
        mime_type = "image/png"
    elif lower_name.endswith(".webp"):
        mime_type = "image/webp"

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=mime_type,
                ),
                prompt,
            ]
        )
        
        result_text = response.text.strip()
        if result_text.startswith("```json"):
            result_text = result_text[7:-3].strip()
        elif result_text.startswith("```"):
            result_text = result_text[3:-3].strip()
            
        result = json.loads(result_text)
        if not isinstance(result, dict) or "ai_result" not in result or "category" not in result:
            raise ValueError("Invalid structure")
            
        result["provider"] = "google-gemini"
        return result
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return _local_analysis(image_bytes, filename)


def analyze_image(image_bytes: bytes, filename: str) -> dict[str, Any]:
    if GEMINI_API_KEY:
        return _gemini_analysis(image_bytes, filename)
        
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
