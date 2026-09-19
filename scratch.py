import sqlite3
import json

conn = sqlite3.connect('backend/ecotrack.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM users WHERE user_id='dilipksharma1244@gmail.com'")
row = cursor.fetchone()
if row:
    print(f"Found: {row}")
else:
    print("User not found.")
