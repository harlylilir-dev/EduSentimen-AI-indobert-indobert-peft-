from fastapi import APIRouter, Depends, HTTPException, Query, Form
from typing import List, Optional
from pydantic import BaseModel
from services.supabase_client import get_supabase
from services.auth import get_current_admin
import json

router = APIRouter(prefix="/api/clean-datasets", tags=["Clean Datasets"])

class DatasetOut(BaseModel):
    id: int
    name: str
    jumlah_data: int
    tanggal_upload: str

class DatasetItemOut(BaseModel):
    no: int
    text: str
    label: Optional[str] = None

class PaginatedItems(BaseModel):
    items: List[DatasetItemOut]
    total: int
    page: int
    per_page: int

@router.get("/", response_model=List[DatasetOut])
async def list_clean_datasets(admin=Depends(get_current_admin)):
    supabase = get_supabase()
    res = supabase.table("clean_datasets").select("id,name,jumlah_data,tanggal_upload").order("created_at", desc=True).execute()
    return [
        DatasetOut(
            id=row["id"],
            name=row["name"],
            jumlah_data=row["jumlah_data"],
            tanggal_upload=str(row["tanggal_upload"])
        )
        for row in res.data
    ]

@router.put("/{dataset_id}/rename")
async def rename_clean_dataset(dataset_id: int, name: str = Form(...), admin=Depends(get_current_admin)):
    supabase = get_supabase()
    supabase.table("clean_datasets").update({"name": name.strip()}).eq("id", dataset_id).execute()
    return {"message": "Nama dataset bersih berhasil diubah"}

@router.delete("/{dataset_id}")
async def delete_clean_dataset(dataset_id: int, admin=Depends(get_current_admin)):
    supabase = get_supabase()
    supabase.table("clean_datasets").delete().eq("id", dataset_id).execute()
    return {"message": "Dataset bersih berhasil dihapus"}

@router.get("/{dataset_id}/items", response_model=PaginatedItems)
async def get_clean_items(
    dataset_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    admin=Depends(get_current_admin)
):
    supabase = get_supabase()
    res = supabase.table("clean_datasets").select("data").eq("id", dataset_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")
    all_data = res.data[0]["data"]
    if isinstance(all_data, str):
        all_data = json.loads(all_data)
    total = len(all_data)
    start = (page - 1) * per_page
    page_items = all_data[start:start+per_page]
    items = [
        DatasetItemOut(no=i+1, text=item["text"], label=item.get("label"))
        for i, item in enumerate(page_items, start=start)
    ]
    return PaginatedItems(items=items, total=total, page=page, per_page=per_page)