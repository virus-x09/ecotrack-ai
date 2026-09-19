# Integrate Google Gemini AI for Waste Image Analysis

This document outlines the plan to integrate a real AI computer-vision model (Google Gemini) to analyze and classify the uploaded plastic waste images in the EcoTrack AI platform.

## User Review Required
> [!IMPORTANT]
> To use the Gemini API, you will need a valid **Gemini API Key**. Once this plan is implemented, you will need to add it to your environment variables (or `.env` file) as `GEMINI_API_KEY`.

## Proposed Changes

### Backend Dependencies
We will add the official Google Generative AI SDK to the backend so we can communicate with Gemini models.

#### [MODIFY] [requirements.txt](file:///e:/IDEATHON/requirements.txt)
- Add `google-genai` to the list of dependencies.

### AI Analyzer Module
We will update the AI analyzer to prioritize the Gemini API if the API key is present. 

#### [MODIFY] [ai_analyzer.py](file:///e:/IDEATHON/backend/ai_analyzer.py)
- Import the Gemini client.
- Create a new `_gemini_analysis` function that:
  - Takes the image bytes and passes it to the `gemini-2.5-flash` (or `gemini-1.5-flash`) model.
  - Prompts the model to detect if the image contains plastic waste and classify it into one of the expected categories (`bottle`, `bag`, `wrapper`, `container`, `other_plastic`).
  - Instructs the model to return a structured JSON response matching the required schema: `{"ai_result": "plastic_detected", "category": "...", "confidence": 0.9}`.
- Update the main `analyze_image` function to route to Gemini if `GEMINI_API_KEY` is set, otherwise fall back to the existing `ECOTRACK_AI_ENDPOINT` or local fallback.

## Verification Plan
1. **Automated Check:** Restart the backend API server.
2. **Manual Verification:** 
   - Add `GEMINI_API_KEY` to the environment.
   - Upload an image through the frontend or via API.
   - Verify that the Gemini model successfully categorizes the image and that the frontend displays the result.
