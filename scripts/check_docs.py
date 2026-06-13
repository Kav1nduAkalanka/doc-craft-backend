import os
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()
supabase = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

res = supabase.table('documents').select('*').execute()
print(f"Total documents: {len(res.data)}")
for doc in res.data:
    print(f"ID: {doc['id']}, User: {doc['user_id']}, Created: {doc['created_at']}")

today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
print("today_start is:", today_start)

res_today = supabase.table('documents').select('id', count='exact').gte('created_at', today_start).execute()
print(f"Documents today: {len(res_today.data)}")
