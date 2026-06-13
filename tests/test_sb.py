import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

try:
    res = supabase.table('documents').select('id', count='exact').eq('status', 'exported').execute()
    print("SUCCESS!", getattr(res, 'count', None))
except Exception as e:
    print("ERROR:", e)
