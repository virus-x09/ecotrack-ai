import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.main import login, LoginRequest

try:
    response = login(LoginRequest(email="ecotrackaipwd@gmail.com", password="admin12345"))
    print("SUCCESS: Login successful!")
    print("Response:", response)
except Exception as e:
    print("ERROR:", str(e))
