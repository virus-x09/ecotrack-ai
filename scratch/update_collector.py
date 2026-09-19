import sys
import sqlite3
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.auth import hash_password

conn = sqlite3.connect('e:/IDEATHON/ecotrack.db')
cur = conn.cursor()

new_email = 'digitalminddilip0906@gmail.com'
new_password_hash = hash_password('dilip0906')

# Check if digitalminddilip0906@gmail.com already exists.
cur.execute("SELECT user_id FROM users WHERE email=?", (new_email,))
existing = cur.fetchone()

if existing:
    # Update the password of existing digitalminddilip0906@gmail.com
    cur.execute("UPDATE users SET password_hash=?, role='collector' WHERE email=?", (new_password_hash, new_email))
else:
    # Update collector@ecotrack.local to digitalminddilip0906@gmail.com
    cur.execute("UPDATE users SET email=?, password_hash=? WHERE email='collector@ecotrack.local'", (new_email, new_password_hash))

conn.commit()
print("Updated collector email and password")
