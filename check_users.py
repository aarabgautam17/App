import sqlite3
import pandas as pd

# Connect to the database
conn = sqlite3.connect("school_portal.db")

print("--- EduTrack 360 User Roster ---")
# Use pandas to read the SQL directly into a beautiful table
df = pd.read_sql_query("SELECT student_id, role, name FROM users", conn)

if df.empty:
    print("⚠️ Database is empty. No users registered.")
else:
    print(df.to_string(index=False))

conn.close()