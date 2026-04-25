from fastapi import APIRouter, Depends, HTTPException
from services.supabase_client import get_supabase
from services.auth import get_current_admin
from utils.text_cleaning import clean_text
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/api/preprocess", tags=["Preprocessing"])

class PreprocessItem(BaseModel):
    id: int
    teks: str
    cleaned: str

@router.get("/{dataset_id}", response_model=List[PreprocessItem])
async def preprocess_dataset(dataset_id: int, admin=Depends(get_current_admin)):
    supabase = get_supabase()

    # Cek dataset ada
    ds = supabase.table("datasets").select("id,name").eq("id", dataset_id).execute()
    if not ds.data:
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")

    # Ambil semua items (untuk preprocessing biasanya semua data)
    items_res = supabase.table("dataset_items").select("*").eq("dataset_id", dataset_id).order("id").execute()

    result = []
    for item in items_res.data:
        cleaned = clean_text(item["text"])
        result.append(PreprocessItem(
            id=item["id"],
            teks=item["text"],
            cleaned=cleaned
        ))

    return result