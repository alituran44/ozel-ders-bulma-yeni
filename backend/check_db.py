import sqlite3, os

DB_PATH = "backend/database/leads.db"
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT COUNT(*) as cnt FROM leads")
print("Total leads:", cur.fetchone()["cnt"])

cur.execute("SELECT platform, COUNT(*) as cnt FROM leads GROUP BY platform")
rows = cur.fetchall()
print("\nBy platform:")
for r in rows:
    print(f"  {r['platform']}: {r['cnt']}")

cur.execute("SELECT subject, COUNT(*) as cnt FROM leads GROUP BY subject ORDER BY cnt DESC LIMIT 20")
rows = cur.fetchall()
print("\nBy subject:")
for r in rows:
    print(f"  {r['subject']}: {r['cnt']}")

print("\nSample leads:")
cur.execute("SELECT id, platform, subject, content, original_link FROM leads LIMIT 5")
for r in cur.fetchall():
    d = dict(r)
    print(f"  [{d['platform']}] {d['subject']}: {d['content'][:120]}...")

conn.close()
