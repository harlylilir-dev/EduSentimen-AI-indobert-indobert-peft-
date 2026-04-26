from dotenv import load_dotenv
import os

load_dotenv()
print("URL:", os.getenv("SUPABASE_URL"))
print("KEY:", os.getenv("SUPABASE_KEY")[:10] + "..." if os.getenv("SUPABASE_KEY") else "NONE")