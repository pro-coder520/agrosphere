import os
from supabase import create_client, Client
from agrosphere import settings

# Load directly from settings or env
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")

# Create the client connection
supabase: Client = create_client(url, key)