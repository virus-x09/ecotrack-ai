import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def lookup_ip_location(client_ip: str | None) -> dict[str, object]:
    if not client_ip or client_ip in {"127.0.0.1", "::1"}:
        return {
            "provider": "ipapi.co",
            "ip": client_ip,
            "city": "Gorakhpur",
            "region": "Uttar Pradesh",
            "country": "India",
            "latitude": 26.7606,
            "longitude": 83.3732,
            "accuracy": "approximate",
        }

    request = Request(f"https://ipapi.co/{client_ip}/json/", headers={"User-Agent": "EcoTrack-AI/1.0"})
    try:
        with urlopen(request, timeout=5) as response:
            result = json.loads(response.read().decode())
    except (HTTPError, URLError, TimeoutError) as error:
        raise ValueError("IP location service is unavailable") from error

    if result.get("error") or result.get("latitude") is None or result.get("longitude") is None:
        raise ValueError("No location was found for this IP address")
    return {
        "provider": "ipapi.co",
        "ip": result.get("ip", client_ip),
        "city": result.get("city"),
        "region": result.get("region"),
        "country": result.get("country_name"),
        "latitude": result["latitude"],
        "longitude": result["longitude"],
        "accuracy": "approximate",
    }
