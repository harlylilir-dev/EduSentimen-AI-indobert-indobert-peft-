from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from services.supabase_client import get_supabase
from services.auth import decode_jwt

router = APIRouter(prefix="/dashboard", tags=["Dashboard Admin"])
security = HTTPBearer()

@router.get("")
async def dashboard(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = decode_jwt(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Token tidak valid atau kadaluarsa")

    supabase = get_supabase()
    res = supabase.table("comments").select("*").order("created_at", desc=True).limit(100).execute()
    return {"data": res.data}