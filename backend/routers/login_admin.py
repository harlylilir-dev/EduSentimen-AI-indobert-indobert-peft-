from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.supabase_client import get_supabase
from services.auth import check_password, create_jwt

router = APIRouter(prefix="/login", tags=["Login Admin"])

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

@router.post("", response_model=TokenResponse)
def login(request: LoginRequest):
    supabase = get_supabase()
    # Cari admin
    res = supabase.table("admins").select("*").eq("username", request.username).execute()
    if not res.data:
        raise HTTPException(status_code=401, detail="Username atau password salah")
    admin = res.data[0]
    hashed = admin["password_hash"]
    if not check_password(request.password, hashed):
        raise HTTPException(status_code=401, detail="Username atau password salah")
    token = create_jwt(request.username)
    return TokenResponse(access_token=token, token_type="bearer")