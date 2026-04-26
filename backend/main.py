from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import raw_datasets, clean_datasets, preprocessing_admin, login_admin, predict, upload_csv, dashboard_admin
from utils.text_cleaning import clean_text
from routers import preprocessing_admin

# Inisialisasi model hanya sekali
MODEL_READY = False
try:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    from peft import PeftModel
    import os

    base_model = "indobenchmark/indobert-base-p1"
    peft_path = "./model_adaptor"

    if os.path.isdir(peft_path):
        model = AutoModelForSequenceClassification.from_pretrained(base_model, num_labels=6)
        model = PeftModel.from_pretrained(model, peft_path)
        model.eval()
        tokenizer = AutoTokenizer.from_pretrained(base_model)
        id2label = {0: "marah", 1: "sedih", 2: "senang", 3: "takut", 4: "cinta", 5: "netral"}

        predict.set_model_dependencies(model, tokenizer, id2label)
        MODEL_READY = True
        print("✅ Model IndoBERT + PEFT berhasil dimuat.")
except Exception as e:
    print(f"⚠️ Model tidak bisa dimuat: {e}")

app = FastAPI(
    title="EduSentiment AI Backend",
    max_request_body_size=100_000_000  # 100 MB (sesuaikan dengan kebutuhan)
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mounting router
app.include_router(login_admin.router)
app.include_router(predict.router)
app.include_router(upload_csv.router)
app.include_router(dashboard_admin.router)
app.include_router(raw_datasets.router)
app.include_router(clean_datasets.router)
app.include_router(preprocessing_admin.router)

@app.get("/")
def root():
    return {
        "message": "EduSentiment AI Backend",
        "model_ready": MODEL_READY
    }