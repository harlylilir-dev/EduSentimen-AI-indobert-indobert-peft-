from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from services.supabase_client import get_supabase
from services.auth import get_current_admin
from utils.text_cleaning import clean_text
from datetime import date
import json

router = APIRouter(prefix="/api/preprocess", tags=["Preprocessing"])

class PreprocessItem(BaseModel):
    no: int
    teks: str
    cleaned: str
    label: Optional[str] = None

class SaveDatasetRequest(BaseModel):
    name: str

@router.get("/{raw_dataset_id}", response_model=List[PreprocessItem])
async def preprocess_raw_dataset(raw_dataset_id: int, admin=Depends(get_current_admin)):
    supabase = get_supabase()

    # Ambil data JSONB dari raw_datasets
    res = supabase.table("raw_datasets").select("data").eq("id", raw_dataset_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Dataset mentah tidak ditemukan")

    all_data = res.data[0]["data"]
    # Supabase mengembalikan JSONB sebagai list/dict Python, tidak perlu json.loads lagi
    if isinstance(all_data, str):
        all_data = json.loads(all_data)

    result = []
    for idx, item in enumerate(all_data):
        cleaned = clean_text(item["text"])
        result.append(PreprocessItem(
            no=idx + 1,
            teks=item["text"],
            cleaned=cleaned,
            label=item.get("label")
        ))

    return result

@router.post("/{raw_dataset_id}/save-as-dataset")
async def save_preprocessed_dataset(
    raw_dataset_id: int,
    req: SaveDatasetRequest,
    admin=Depends(get_current_admin)
):
    supabase = get_supabase()

    # Ambil data mentah
    res = supabase.table("raw_datasets").select("data").eq("id", raw_dataset_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Dataset mentah tidak ditemukan")

    all_data = res.data[0]["data"]
    if isinstance(all_data, str):
        all_data = json.loads(all_data)

    # Membersihkan dan menyiapkan array untuk clean_datasets
    clean_items = []
    for item in all_data:
        clean_text_value = clean_text(item["text"])
        clean_items.append({
            "text": clean_text_value,
            "label": item.get("label")
        })

    jumlah = len(clean_items)

    # Simpan ke clean_datasets
    insert_res = supabase.table("clean_datasets").insert({
        "name": req.name.strip(),
        "jumlah_data": jumlah,
        "tanggal_upload": str(date.today()),
        "data": json.dumps(clean_items)  # Supabase akan mengonversi ke JSONB
    }).execute()

    return {
        "message": "Dataset bersih berhasil disimpan",
        "dataset_id": insert_res.data[0]["id"]
    }