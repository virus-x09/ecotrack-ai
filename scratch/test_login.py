import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

response = client.post(
    "/auth/login",
    json={
        "email": "ecotrackaipwd@gmail.com",
        "password": "admin12345"
    }
)

print("Status Code:", response.status_code)
print("Response Body:", response.json())
