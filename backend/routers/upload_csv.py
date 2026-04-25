from fastapi import APIRouter, File, UploadFile, HTTPException
import pandas as pd
import io
import html
from datetime import datetime
from services.supabase_client import get_supabase
# Impor predict helper jika mau prediksi massal
# Untuk efisiensi, bisa panggil fungsi prediksi langsung tanpa HTTP overlap

router = APIRouter(prefix="/upload-csv", tags=["Upload CSV"])

@router.post("")
async def upload_csv(file: UploadFile = File(...)):
    # Baca dan bersihkan CSV (copy dari code sebelumnya)
    content = file.file.read().decode("utf-8", errors="ignore")
    stream = io.StringIO(content)
    try:
        df = pd.read_csv(stream, sep=",", engine="python", on_bad_lines="skip")
    except:
        stream.seek(0)
        df = pd.read_csv(stream, sep=";", engine="python", on_bad_lines="skip")

    if df.empty:
        raise HTTPException(status_code=400, detail="CSV kosong")

    df.columns = df.columns.str.strip()
    if len(df.columns) == 1:
        df.columns = ["teks"]
    else:
        df.rename(columns={df.columns[0]: "teks"}, inplace=True)

    # Di sini harus memanggil prediksi massal (bisa dari predict.py)
    # Untuk sederhana kita simpan teks mentah tanpa prediksi dulu
    # (atau impor fungsi prediksi)
    results = []
    for _, row in df.iterrows():
        raw = str(row["teks"])
        raw = html.unescape(raw)
        # Nanti ganti dengan prediksi sungguhan
        dummy_emotion = "netral"
        dummy_conf = 0.5
        supabase = get_supabase()
        supabase.table("comments").insert({
            "text": raw,
            "emotion": dummy_emotion,
            "confidence": dummy_conf
        }).execute()
        results.append({"teks": raw, "emotion": dummy_emotion, "confidence": dummy_conf})

    return {"processed": len(results), "results": results}