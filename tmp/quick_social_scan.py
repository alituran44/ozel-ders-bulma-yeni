import asyncio
import os
import sys

# Windows Loop Policy initialization
if os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

sys.path.append(os.path.join(os.getcwd(), 'backend'))

from ultra_deep_scan import run_ultra_deep_scan, fb_group_queries, ig_queries, web_queries
import ultra_deep_scan

# Override queries to focus ONLY on Facebook and Instagram for this run
ultra_deep_scan.fb_group_queries = fb_group_queries[:10] # Top 10
ultra_deep_scan.ig_queries = ig_queries # All IG
ultra_deep_scan.web_queries = [] # Skip general web
ultra_deep_scan.PHASE_3_ENABLED = False # DonanımHaber skip
ultra_deep_scan.PHASE_4_ENABLED = False # Sahibinden skip

if __name__ == "__main__":
    print("🚀 Quick Social Scan (FB & IG) starting...")
    asyncio.run(run_ultra_deep_scan())
