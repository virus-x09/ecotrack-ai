import sqlite3
import sys

sys.path.append('d:/IDEATHON')
from backend.auth import hash_password

conn = sqlite3.connect('d:/IDEATHON/ecotrack.db')
try:
    h_all = hash_password('12345678')
    conn.execute('UPDATE users SET password_hash = ?', (h_all,))
    conn.commit()
    print('Updated all users passwords to 12345678 successfully!')
except Exception as e:
    print('Error:', e)
