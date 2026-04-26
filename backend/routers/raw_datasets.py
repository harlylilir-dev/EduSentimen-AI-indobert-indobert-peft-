from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from services.supabase_client import get_supabase
from services.auth import get_current_admin
import pandas as pd
import io
from datetime import date
import json

router = APIRouter(prefix="/api/raw-datasets", tags=["Raw Datasets"])

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

# Upload file CSV/Excel dan simpan ke raw_datasets sebagai JSONB
@router.post("/upload")
async def upload_raw_dataset(
    file: UploadFile = File(...),
    name: str = Form(...),
    admin=Depends(get_current_admin)
):
    filename = file.filename.lower()
    if not filename.endswith(('.csv', '.xlsx')):
        raise HTTPException(status_code=400, detail="Format file harus CSV atau XLSX")

    content = await file.read()

    # Baca file
    if filename.endswith('.csv'):
        encodings = ['utf-8', 'latin-1', 'windows-1252', 'iso-8859-1']
        df = None
        for enc in encodings:
            try:
                df = pd.read_csv(io.BytesIO(content), sep=None, engine='python', encoding=enc)
                break
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue
        if df is None:
            try:
                import chardet
                detected = chardet.detect(content)
                enc = detected['encoding'] or 'utf-8'
                df = pd.read_csv(io.BytesIO(content), sep=None, engine='python', encoding=enc)
            except Exception:
                raise HTTPException(status_code=400, detail="Gagal membaca CSV, encoding tidak didukung")
    else:
        try:
            df = pd.read_excel(io.BytesIO(content), engine='openpyxl')
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Gagal membaca Excel: {str(e)}")

    if df.empty:
        raise HTTPException(status_code=400, detail="File kosong atau tidak memiliki data")

    cols = df.columns.tolist()
    text_col = cols[0]
    label_col = cols[1] if len(cols) > 1 else None

    # Buat array JSON
    data_json = []
    for _, row in df.iterrows():
        text = str(row[text_col]).strip()
        if not text:
            continue
        label = str(row[label_col]).strip() if label_col and not pd.isna(row[label_col]) else None
        data_json.append({"text": text, "label": label})

    if not data_json:
        raise HTTPException(status_code=400, detail="Tidak ada teks yang valid")

    jumlah = len(data_json)
    supabase = get_supabase()

    res = supabase.table("raw_datasets").insert({
        "name": name.strip(),
        "jumlah_data": jumlah,
        "tanggal_upload": str(date.today()),
        "data": json.dumps(data_json)  # simpan sebagai string JSON, Supabase akan mengonversi ke JSONB
    }).execute()

    return {"message": "Dataset mentah berhasil diupload", "dataset_id": res.data[0]["id"]}

# List semua raw datasets
@router.get("/", response_model=List[DatasetOut])
async def list_raw_datasets(admin=Depends(get_current_admin)):
    supabase = get_supabase()
    res = supabase.table("raw_datasets").select("id,name,jumlah_data,tanggal_upload").order("created_at", desc=True).execute()
    return [
        DatasetOut(
            id=row["id"],
            name=row["name"],
            jumlah_data=row["jumlah_data"],
            tanggal_upload=str(row["tanggal_upload"])
        )
        for row in res.data
    ]

# Rename
@router.put("/{dataset_id}/rename")
async def rename_raw_dataset(dataset_id: int, name: str = Form(...), admin=Depends(get_current_admin)):
    supabase = get_supabase()
    supabase.table("raw_datasets").update({"name": name.strip()}).eq("id", dataset_id).execute()
    return {"message": "Nama dataset berhasil diubah"}

# Hapus
@router.delete("/{dataset_id}")
async def delete_raw_dataset(dataset_id: int, admin=Depends(get_current_admin)):
    supabase = get_supabase()
    supabase.table("raw_datasets").delete().eq("id", dataset_id).execute()
    return {"message": "Dataset mentah berhasil dihapus"}

# Detail dengan pagination dari data JSONB
@router.get("/{dataset_id}/items", response_model=PaginatedItems)
async def get_raw_items(
    dataset_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    admin=Depends(get_current_admin)
):
    supabase = get_supabase()
    res = supabase.table("raw_datasets").select("data").eq("id", dataset_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")

    all_data = res.data[0]["data"]  # ini sudah list/dict hasil parsing JSONB dari Supabase
    if isinstance(all_data, str):
        import json
        all_data = json.loads(all_data)
    total = len(all_data)
    start = (page - 1) * per_page
    page_items = all_data[start:start+per_page]
    items = [
        DatasetItemOut(no=i+1, text=item["text"], label=item.get("label"))
        for i, item in enumerate(page_items, start=start)
    ]
    return PaginatedItems(items=items, total=total, page=page, per_page=per_page)