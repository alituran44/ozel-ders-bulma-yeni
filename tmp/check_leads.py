import os, sqlite3
db_path = os.path.join('backend', 'database', 'leads.db')
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT platform, count(*), max(created_at) FROM leads GROUP BY platform")
    results = cursor.fetchall()
    print('Platform Statistics:')
    print('-' * 40)
    for r in results:
        print(f'Platform: {r[0]}, Count: {r[1]}, Last: {r[2]}')
    cursor.execute("SELECT count(*) FROM leads WHERE is_qualified = 1")
    print(f'Total Qualified Leads: {cursor.fetchone()[0]}')
    conn.close()
else:
    print(f'Database not found at {db_path}')
