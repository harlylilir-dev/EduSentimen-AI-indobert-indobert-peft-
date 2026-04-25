from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from services.supabase_client import get_supabase
from utils.text_cleaning import clean_text
import torch

router = APIRouter(prefix="/predict", tags=["Prediksi"])

class PredictRequest(BaseModel):
    text: str

class PredictResponse(BaseModel):
    id: int = None
    text: str
    emotion: str
    confidence: float
    created_at: str

# Nanti akan diisi referensi model dari main.py
model = None
tokenizer = None
id2label = {}

def set_model_dependencies(model_obj, tokenizer_obj, label_mapping):
    global model, tokenizer, id2label
    model = model_obj
    tokenizer = tokenizer_obj
    id2label = label_mapping

@router.post("", response_model=PredictResponse)
def predict_single(req: PredictRequest):
    if model is None:
        raise HTTPException(status_code=500, detail="Model belum dimuat")

    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Teks tidak boleh kosong")

    cleaned = clean_text(text)
    inputs = tokenizer(cleaned, return_tensors="pt", truncation=True, padding=True, max_length=256)
    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.softmax(outputs.logits, dim=1)
        confidence, pred_idx = torch.max(probs, dim=1)
    emotion = id2label.get(pred_idx.item(), "netral")
    confidence_val = round(confidence.item(), 4)

    # Simpan ke Supabase
    data = {
        "text": text,
        "emotion": emotion,
        "confidence": confidence_val,
        "created_at": datetime.utcnow().isoformat()
    }
    supabase = get_supabase()
    res = supabase.table("comments").insert(data).execute()
    saved = res.data[0]

    return PredictResponse(
        id=saved["id"],
        text=saved["text"],
        emotion=saved["emotion"],
        confidence=saved["confidence"],
        created_at=saved["created_at"]
    )