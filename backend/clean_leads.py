import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('backend/database/leads.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute('SELECT id, platform, original_link, content FROM leads ORDER BY created_at DESC')
rows = cur.fetchall()

fake_ids = []
print(f"\nToplam {len(rows)} ilan kontrol ediliyor:\n" + "="*80)
for r in rows:
    link = r['original_link'] or ''
    is_fake = (
        'abc123' in link or
        link.endswith('/posts/1') or
        link.endswith('/posts/456') or
        link == '' or
        ('facebook.com/groups/lgs2026' in link) or
        ('facebook.com/groups/yksyardim' in link)
    )
    status = "❌ SAHTE/BOZUK" if is_fake else "✅ GERCEK"
    print(f"{status} | {r['platform']} | {link[:65]}")
    if is_fake:
        fake_ids.append(r['id'])

print(f"\n{len(fake_ids)} sahte/bozuk ilan tespit edildi.")

if fake_ids:
    for fid in fake_ids:
        cur.execute('DELETE FROM leads WHERE id = ?', (fid,))
    conn.commit()
    print(f"✅ {len(fake_ids)} sahte ilan silindi.")

conn.close()
print("Islem tamamlandi.")
