import sqlite3
conn = sqlite3.connect('ecotrack.db')
cur = conn.cursor()
cur.execute("UPDATE users SET email='ecotrackaipwd@gmail.com' WHERE email='admin@ecotrack.local'")
conn.commit()
print("Updated admin email")
