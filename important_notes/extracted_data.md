# Extracted Data from Duplicate Files

During the cleanup of the duplicate `IDEATHON` folder, we identified some architectural differences and code variations. The duplicate folder seemed to contain a slightly different implementation (possibly a cloud-hosted version or an alternative UI design).

Here are the important details that you can implement in your main codebase later if desired:

## 1. Backend: PostgreSQL & Vercel Blob Storage Integration
The duplicate backend (`main.py` and `database.py`) was configured to use PostgreSQL instead of SQLite, and to upload images to **Vercel Blob Storage** instead of storing them locally as BLOBs in the database.

**Upload to Vercel Blob (from duplicate `main.py`):**
```python
def upload_to_vercel_blob(filename: str, file_bytes: bytes) -> str:
    token = os.getenv("BLOB_READ_WRITE_TOKEN")
    if not token:
        raise HTTPException(status_code=500, detail="Vercel Blob token is missing")
    url = f"https://blob.vercel-storage.com/{filename}"
    headers = {
        "authorization": f"Bearer {token}",
    }
    response = requests.put(url, headers=headers, data=file_bytes)
    response.raise_for_status()
    return response.json()["url"]
```

**PostgreSQL Syntax (from duplicate `database.py`):**
The duplicate database queries used `%s` placeholders and `psycopg2.extras.DictCursor`, along with `ON CONFLICT` for upserts:
```python
# Example UPSERT in PostgreSQL
cursor.execute(
    """
    INSERT INTO reports (
        report_id, user_id, image_reference, ai_result, category,
        latitude, longitude, description, timestamp, status,
        collector_id, evidence_reference
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (report_id) DO UPDATE SET
        ai_result = EXCLUDED.ai_result,
        category = EXCLUDED.category,
        status = EXCLUDED.status,
        collector_id = EXCLUDED.collector_id,
        evidence_reference = EXCLUDED.evidence_reference
    """,
    (...)
)
```

## 2. Frontend: Dynamic Sidebar Profile UI
The duplicate `app.js` contained logic to dynamically update the user's name and initials in the sidebar. We will merge this into the main `app.js` right now, so you don't have to worry about it!

## 3. Frontend: Alternative Authentication UI (Lighter Theme)
The duplicate `auth.css` had a lighter, greener UI theme compared to the current dark/glassmorphic theme. If you prefer the lighter theme, here are the CSS variables that were used:

```css
:root {
  --auth-bg-light: #F1FCF3;
  --auth-bg-gradient: radial-gradient(ellipse at top right, #C0F2CB 0%, #F1FCF3 50%, #E4E2D6 100%);
  --eco-primary: #2BA84A;
  --eco-primary-hover: #1D3B1F;
  --eco-dark: #082B13;
  --text-main: #1D3B1F;
  --text-muted: #575B58;
  --input-bg: #FFFFFF;
  --input-border: #DFF9E5;
  --card-bg: rgba(255, 255, 255, 0.95);
}
```

The buttons were also styled as solid green buttons without the neon border effects:
```css
.primary-button.neon-btn {
  background: var(--eco-primary);
  color: #ffffff;
  border: none;
  box-shadow: 0 4px 6px -1px rgba(43, 168, 74, 0.3), 0 2px 4px -2px rgba(43, 168, 74, 0.3);
}
```

## 4. Unwanted Files Cleaned Up
- Removed the duplicate `IDEATHON\IDEATHON` directory.
- Removed unused root-level files: `fix.py`, `scratch_db.py`, `serve.py`, and `auth-smoke.db`.
- Removed `index.html` from the root (which was just a redirect to the `frontend/` folder).

*(Note: The fixes to the eye toggle for passwords and the dynamic sidebar profile have been merged into your active codebase.)*
