import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'backend')
from database.db_manager import get_leads

leads = get_leads(100)
print(f"\nToplam {len(leads)} nitelikli ilan:\n" + "="*80)
for i, l in enumerate(leads, 1):
    print(f"[{i:02}] Platform : {l['platform']}")
    print(f"     Konu    : {l['subject']}")
    print(f"     Konum   : {l['location']}")
    print(f"     Icerik  : {l['content'][:100]}")
    print(f"     Link    : {l['original_link']}")
    if l.get('contact_info'):
        print(f"     Iletisim: {l['contact_info']}")
    print()
