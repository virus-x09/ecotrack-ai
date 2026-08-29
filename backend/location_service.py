import os

import googlemaps


def google_geolocate(payload: dict[str, object]) -> dict[str, object]:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_MAPS_API_KEY is not configured on the server")

    try:
        client = googlemaps.Client(key=api_key, timeout=10)
        result = client.geolocate(**payload)
    except Exception as error:
        raise ValueError("Google Geolocation service is unavailable") from error

    location = result.get("location")
    if not isinstance(location, dict) or "lat" not in location or "lng" not in location:
        raise ValueError("Google returned no valid location")
    return {
        "latitude": location["lat"],
        "longitude": location["lng"],
        "accuracy_meters": result.get("accuracy"),
        "provider": "google-geolocation",
    }


def google_reverse_geocode(latitude: float, longitude: float) -> dict[str, object]:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_MAPS_API_KEY is not configured on the server")
    try:
        client = googlemaps.Client(key=api_key, timeout=10)
        results = client.reverse_geocode((latitude, longitude), language="en")
    except Exception as error:
        raise ValueError("Google Geocoding service is unavailable") from error
    if not results:
        raise ValueError("Google returned no address for these coordinates")
    return {
        "address": results[0].get("formatted_address"),
        "latitude": latitude,
        "longitude": longitude,
        "provider": "google-geocoding",
    }
