# EcoTrack AI

EcoTrack AI is a prototype smart plastic-waste monitoring platform based on the SRS in [REQUIREMENTS.md](REQUIREMENTS.md).

## Run the API

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Open the interactive API documentation at `http://127.0.0.1:8000/docs`.

For production-like local use, set a private signing secret before starting the API:

```powershell
$env:ECOTRACK_AUTH_SECRET = "replace-with-a-long-random-secret"
```

## Run the frontend

In a second terminal, serve the frontend directory:

```powershell
python -m http.server 5500 --directory frontend
```

Open the dashboard at `http://127.0.0.1:5500` after starting the API.

## Automatic Location and Map

The report form requests the browser's Geolocation permission automatically. When permission is granted, latitude and longitude are filled from the device GPS and submitted with the report. The map opens on the GIDA industrial area in Gorakhpur and displays report markers across the sector view. Use refresh to return to the GIDA overview after exploring a GPS location. Location access works on `localhost` or `127.0.0.1`; production deployments must use HTTPS.

The campus panel also links to the provided ITM GIDA Google Street View panorama at `26.7430558,83.2733427` through the **360 view** action.

If GPS permission is denied, the form automatically tries `GET /location/ip`. This uses the request network IP through `ipapi.co` and is only an approximate location; local development requests use Gorakhpur as the demo fallback. The form also includes a manual **Use network** option.

### Cleaned-location notifications

When an administrator approves collection evidence, EcoTrack calls the reporter's email and optional AI-agent webhook notification. Configure SMTP and webhook settings on the backend:

```powershell
$env:ECOTRACK_SMTP_HOST = "smtp.example.com"
$env:ECOTRACK_SMTP_PORT = "587"
$env:ECOTRACK_SMTP_USER = "notifications@example.com"
$env:ECOTRACK_SMTP_PASSWORD = "your-smtp-password"
$env:ECOTRACK_AGENT_WEBHOOK = "https://your-agent.example.com/ecotrack-events"
```

The event is `location_cleaned` and includes the report ID, reporter ID/email, and location. If these services are not configured, verification still succeeds and no credentials are exposed to the frontend. Evidence images are validated as JPEG, PNG, or WebP and stored under `uploads/evidence`. Set `ECOTRACK_UPLOADS_DIR` to choose another storage directory.

### Optional Google Geolocation API

The project also exposes a secure server-side proxy at `POST /location/google`. The browser must never contain the Google API key. Configure it before starting the API:

```powershell
$env:GOOGLE_MAPS_API_KEY = "your-server-side-key"
```

Google Geolocation request example:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/location/google" -H "Content-Type: application/json" -d "{\"considerIp\":true,\"radioType\":\"gsm\"}"
```

Reverse-geocode coordinates into a readable address:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/location/reverse-geocode" -H "Content-Type: application/json" -d "{\"latitude\":26.7395,\"longitude\":83.4495}"
```

Get the key from **Google Cloud Console**: create/select a project, enable **Geolocation API** under **APIs & Services > Library**, then create a key under **APIs & Services > Credentials**. Restrict the key to the Geolocation API and your server IPs where possible. Google may require billing, and `considerIp` estimates the server request IP; browser GPS is generally more accurate and remains the primary implementation.

## Prototype Users

The current prototype uses these demo identities through the `user_id` request field:

- `citizen-demo`
- `admin-demo`
- `collector-demo`

Demo login accounts for testing the complete workflow:

- Administrator: `admin@ecotrack.local` / `admin12345`
- Collector: `collector@ecotrack.local` / `collector123`

## Implemented API Surface

- `GET /health` - service health check
- `POST /auth/register` - create a citizen account
- `POST /auth/login` - receive a bearer access token
- `GET /auth/me` - resolve the authenticated user from a bearer token
- `POST /reports` - citizen report creation with image upload, coordinates, description, and image analysis
- `GET /reports` - report listing with status, category, and user filters
- `GET /reports/{report_id}` - protected report detail for its owner, assigned collector, or administrator
- `GET /collectors` - administrator-only list of available collection team members
- `PATCH /reports/{report_id}/status` - administrator or assigned collector status updates
- `POST /reports/{report_id}/assignment` - administrator assigns a collector
- `POST /reports/{report_id}/evidence` - assigned collector uploads completion evidence or submits a reference
- `POST /reports/{report_id}/verify` - administrator approves or rejects evidence
- `GET /analytics` - report totals, status counts, and category counts

## Prototype Limitations

Reports and registered users are stored in the local SQLite database `ecotrack.db` and survive server restarts. Set the `ECOTRACK_DATABASE` environment variable to use another database path. Report and evidence images are validated as JPEG, PNG, or WebP, limited to 10 MB, and stored under `uploads/reports` and `uploads/evidence`. Set `ECOTRACK_AI_ENDPOINT` to connect an external computer-vision service; without it, the local prototype validates the image and returns a clearly marked fallback classification.
