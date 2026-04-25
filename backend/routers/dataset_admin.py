from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from typing import List, Optional
from pydantic import BaseModel
from services.supabase_client import get_supabase
from services.auth import get_current_admin
import pandas as pd
import io
from datetime import date

router = APIRouter(prefix="/api/datasets", tags=["Dataset Admin"])

# Skema response
class DatasetOut(BaseModel):
    id: int
    name: str
    jumlah_data: int
    tanggal_upload: str  # date sebagai string

class DatasetItemOut(BaseModel):
    id: int
    text: str
    label: Optional[str] = None

class PaginatedItems(BaseModel):
    items: List[DatasetItemOut]
    total: int
    page: int
    per_page: int

# Endpoint upload CSV
@router.post("/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(...),
    admin=Depends(get_current_admin)
):
    # Baca file CSV
    content = await file.read()
    try:
        df = pd.read_csv(io.StringIO(content.decode("utf-8")), sep=None, engine="python")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal membaca CSV: {str(e)}")

    if df.empty:
        raise HTTPException(status_code=400, detail="CSV kosong")

    # Ambil kolom pertama sebagai teks, kolom kedua sebagai label jika ada
    cols = df.columns.tolist()
    if len(cols) >= 2:
        text_col = cols[0]
        label_col = cols[1]
    else:
        text_col = cols[0]
        label_col = None

    jumlah = len(df)

    supabase = get_supabase()

    # Insert dataset
    dataset_data = {
        "name": name.strip(),
        "jumlah_data": jumlah,
        "tanggal_upload": str(date.today())
    }
    res = supabase.table("datasets").insert(dataset_data).execute()
    dataset_id = res.data[0]["id"]

    # Insert items
    items_to_insert = []
    for _, row in df.iterrows():
        text = str(row[text_col]).strip()
        if not text:
            continue
        label = str(row[label_col]).strip() if label_col and not pd.isna(row[label_col]) else None
        items_to_insert.append({
            "dataset_id": dataset_id,
            "text": text,
            "label": label
        })

    if items_to_insert:
        supabase.table("dataset_items").insert(items_to_insert).execute()

    return {"message": "Dataset berhasil diupload", "dataset_id": dataset_id}

# List datasets
@router.get("/", response_model=List[DatasetOut])
async def list_datasets(admin=Depends(get_current_admin)):
    supabase = get_supabase()
    res = supabase.table("datasets").select("*").order("created_at", desc=True).execute()
    datasets = []
    for row in res.data:
        datasets.append(DatasetOut(
            id=row["id"],
            name=row["name"],
            jumlah_data=row["jumlah_data"],
            tanggal_upload=str(row["tanggal_upload"])
        ))
    return datasets

# Rename dataset
@router.put("/{dataset_id}/rename")
async def rename_dataset(dataset_id: int, name: str = Form(...), admin=Depends(get_current_admin)):
    supabase = get_supabase()
    # Cek ada dataset
    res = supabase.table("datasets").select("id").eq("id", dataset_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")
    supabase.table("datasets").update({"name": name.strip()}).eq("id", dataset_id).execute()
    return {"message": "Nama dataset berhasil diubah"}

# Hapus dataset
@router.delete("/{dataset_id}")
async def delete_dataset(dataset_id: int, admin=Depends(get_current_admin)):
    supabase = get_supabase()
    res = supabase.table("datasets").select("id").eq("id", dataset_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")
    # Hapus items dulu (cascade akan menghapus otomatis jika sudah diset)
    supabase.table("datasets").delete().eq("id", dataset_id).execute()
    return {"message": "Dataset berhasil dihapus"}

# Ambil items dataset dengan paginasi
@router.get("/{dataset_id}/items", response_model=PaginatedItems)
async def get_dataset_items(
    dataset_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    admin=Depends(get_current_admin)
):
    supabase = get_supabase()

    # Cek dataset ada
    ds = supabase.table("datasets").select("id").eq("id", dataset_id).execute()
    if not ds.data:
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")

    # Hitung total
    count_res = supabase.table("dataset_items").select("id", count="exact").eq("dataset_id", dataset_id).execute()
    total = count_res.count if count_res.count else 0

    # Ambil halaman
    start = (page - 1) * per_page
    items_res = supabase.table("dataset_items").select("*").eq("dataset_id", dataset_id)\
                .range(start, start + per_page - 1).order("id").execute()

    items = [DatasetItemOut(id=it["id"], text=it["text"], label=it.get("label")) for it in items_res.data]

    return PaginatedItems(items=items, total=total, page=page, per_page=per_page)