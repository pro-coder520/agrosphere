import os
from supabase import create_client, Client

url: str = os.getenv("SUPABASE_URL", "")
key: str = os.getenv("SUPABASE_KEY", "")

# Optional: Add a runtime check to warn you if keys are missing
if not url or not key:
    print("Warning: Supabase credentials missing in .env")

# Create the client connection
supabase: Client = create_client(url, key)