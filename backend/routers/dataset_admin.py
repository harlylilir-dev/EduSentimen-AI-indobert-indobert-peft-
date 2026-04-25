from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from typing import List, Optional
from pydantic import BaseModel
from services.supabase_client import get_supabase
from services.auth import get_current_admin
import pandas as pd
import io
from datetime import date

router = APIRouter(prefix="/api/datasets", tags=["Dataset Admin"])

# ---------- Skema ----------
class DatasetOut(BaseModel):
    id: int
    name: str
    jumlah_data: int
    tanggal_upload: str

class DatasetItemOut(BaseModel):
    id: int
    text: str
    label: Optional[str] = None

class PaginatedItems(BaseModel):
    items: List[DatasetItemOut]
    total: int
    page: int
    per_page: int

# ---------- Upload CSV / Excel ----------
@router.post("/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(...),
    admin=Depends(get_current_admin)
):
    filename = file.filename.lower()
    if not filename.endswith(('.csv', '.xlsx')):
        raise HTTPException(status_code=400, detail="Format file harus CSV atau XLSX")

    content = await file.read()

    # --- Baca file sesuai tipe ---
    if filename.endswith('.csv'):
        # Coba beberapa encoding umum
        encodings = ['utf-8', 'latin-1', 'windows-1252', 'iso-8859-1']
        df = None
        for enc in encodings:
            try:
                df = pd.read_csv(io.BytesIO(content), sep=None, engine='python', encoding=enc)
                break
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue

        if df is None:
            # Fallback dengan chardet jika tersedia
            try:
                import chardet
                detected = chardet.detect(content)
                enc = detected['encoding'] or 'utf-8'
                df = pd.read_csv(io.BytesIO(content), sep=None, engine='python', encoding=enc)
            except Exception:
                raise HTTPException(status_code=400, detail="Gagal membaca CSV, encoding tidak didukung")
    else:  # .xlsx
        try:
            df = pd.read_excel(io.BytesIO(content), engine='openpyxl')
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Gagal membaca Excel: {str(e)}")

    if df.empty:
        raise HTTPException(status_code=400, detail="File kosong atau tidak memiliki data")

    # Kolom pertama = teks, kolom kedua (jika ada) = label
    cols = df.columns.tolist()
    text_col = cols[0]
    label_col = cols[1] if len(cols) > 1 else None

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

    # Insert items dalam batch (500 per request)
    BATCH_SIZE = 500
    items_batch = []
    for _, row in df.iterrows():
        text = str(row[text_col]).strip()
        if not text:
            continue
        label = None
        if label_col and not pd.isna(row[label_col]):
            label = str(row[label_col]).strip()
        items_batch.append({
            "dataset_id": dataset_id,
            "text": text,
            "label": label
        })
        if len(items_batch) >= BATCH_SIZE:
            supabase.table("dataset_items").insert(items_batch).execute()
            items_batch.clear()

    # Sisa batch
    if items_batch:
        supabase.table("dataset_items").insert(items_batch).execute()

    return {"message": "Dataset berhasil diupload", "dataset_id": dataset_id}

# ---------- List semua dataset ----------
@router.get("/", response_model=List[DatasetOut])
async def list_datasets(admin=Depends(get_current_admin)):
    supabase = get_supabase()
    res = supabase.table("datasets").select("*").order("created_at", desc=True).execute()
    return [
        DatasetOut(
            id=row["id"],
            name=row["name"],
            jumlah_data=row["jumlah_data"],
            tanggal_upload=str(row["tanggal_upload"])
        )
        for row in res.data
    ]

# ---------- Rename dataset ----------
@router.put("/{dataset_id}/rename")
async def rename_dataset(dataset_id: int, name: str = Form(...), admin=Depends(get_current_admin)):
    supabase = get_supabase()
    res = supabase.table("datasets").select("id").eq("id", dataset_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")
    supabase.table("datasets").update({"name": name.strip()}).eq("id", dataset_id).execute()
    return {"message": "Nama dataset berhasil diubah"}

# ---------- Hapus dataset ----------
@router.delete("/{dataset_id}")
async def delete_dataset(dataset_id: int, admin=Depends(get_current_admin)):
    supabase = get_supabase()
    res = supabase.table("datasets").select("id").eq("id", dataset_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")
    # Hapus dataset (cascade akan menghapus items terkait)
    supabase.table("datasets").delete().eq("id", dataset_id).execute()
    return {"message": "Dataset berhasil dihapus"}

# ---------- Ambil items dataset dengan paginasi ----------
@router.get("/{dataset_id}/items", response_model=PaginatedItems)
async def get_dataset_items(
    dataset_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    admin=Depends(get_current_admin)
):
    supabase = get_supabase()
    ds = supabase.table("datasets").select("id").eq("id", dataset_id).execute()
    if not ds.data:
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")

    # Total items
    count_res = supabase.table("dataset_items").select("id", count="exact").eq("dataset_id", dataset_id).execute()
    total = count_res.count if count_res.count else 0

    start = (page - 1) * per_page
    items_res = supabase.table("dataset_items").select("*").eq("dataset_id", dataset_id)\
                .range(start, start + per_page - 1).order("id").execute()

    items = [DatasetItemOut(id=it["id"], text=it["text"], label=it.get("label")) for it in items_res.data]
    return PaginatedItems(items=items, total=total, page=page, per_page=per_page)