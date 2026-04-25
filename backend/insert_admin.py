import bcrypt
from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

username = "sangbintang"
password = "1234"
hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

supabase.table("admins").insert({
    "username": username,
    "password_hash": hashed
}).execute()

print("Admin berhasil disimpan!")