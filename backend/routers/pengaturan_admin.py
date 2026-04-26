from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import os
import logging
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
)
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset
from supabase import create_client, Client

# ================== KONFIGURASI DATABASE ==================
# Untuk sementara hardcode dulu (jangan commit ke public repo)
SUPABASE_URL = "https://yxdufmhnfbedgkaffgno.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl4ZHVmbWhuZmJlZGdrYWZmZ25vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NzAzMTg4MCwiZXhwIjoyMDkyNjA3ODgwfQ.yuX4dTuBKF4jwApMLZQITjxGFFpGm1xyW5YfiBx6zxw"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter(prefix="/api", tags=["training"])
logging.basicConfig(level=logging.INFO)

# ================== MODEL GLOBAL UNTUK PREDIKSI ==================
# Akan diisi setelah aktivasi model via endpoint /api/model/activate/{model_id}
model = None
tokenizer = None
id2label = {}
MODEL_READY = False

def load_model_from_storage(session_id: int):
    """Unduh model & tokenizer dari Supabase Storage, muat ke memori."""
    global model, tokenizer, id2label, MODEL_READY
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        # Dapatkan daftar file
        files = supabase.storage.from_("models").list(f"session_{session_id}")
        if not files:
            raise Exception("Tidak ada file model di storage")
        for f in files:
            file_bytes = supabase.storage.from_("models").download(f"session_{session_id}/{f['name']}")
            with open(os.path.join(tmpdir, f['name']), "wb") as fp:
                fp.write(file_bytes)
        # Muat tokenizer & model
        tokenizer = AutoTokenizer.from_pretrained(tmpdir)
        model = AutoModelForSequenceClassification.from_pretrained(tmpdir)
        # Dapatkan label mapping jika ada
        id2label = model.config.id2label if hasattr(model.config, "id2label") else {}
        MODEL_READY = True


# ================== FUNGSI TRAINING (BACKGROUND) ==================
def train_model(session_id: int):
    """
    Fungsi training dijalankan di background thread.
    """
    session_resp = supabase.table("training_sessions").select("*").eq("id", session_id).single().execute()
    if not session_resp.data:
        logging.error(f"Session {session_id} tidak ditemukan")
        return
    session = session_resp.data

    # Update status -> running
    supabase.table("training_sessions").update({
        "status": "running",
        "started_at": "now()"
    }).eq("id", session_id).execute()

    try:
        # Ambil dataset
        dataset_id = session["clean_dataset_id"]
        ds_resp = supabase.table("clean_datasets").select("data").eq("id", dataset_id).single().execute()
        if not ds_resp.data:
            raise Exception("Dataset bersih tidak ditemukan")
        raw_data = ds_resp.data["data"]  # list of {text, label}
        df = pd.DataFrame(raw_data)
        df["label"] = df["label"].astype("category").cat.codes
        num_classes = len(df["label"].unique())

        # Config training
        config = session["config"]
        train_ratio = config.get("train_ratio", 0.8)
        random_seed = config.get("random_seed", 42)
        train_df, val_df = train_test_split(
            df, test_size=1 - train_ratio, random_state=random_seed, stratify=df["label"]
        )

        # Model & tokenizer
        model_name = config.get("model_name", "indobenchmark/indobert-base-p2")
        tokenizer_local = AutoTokenizer.from_pretrained(model_name)
        base_model = AutoModelForSequenceClassification.from_pretrained(
            model_name,
            num_labels=num_classes,
            ignore_mismatched_sizes=True
        )

        # PEFT
        if session["model"] == "indobert_peft" and "peft" in config:
            peft_cfg = config["peft"]
            if "lora" in peft_cfg:
                lora = peft_cfg["lora"]
                lora_config = LoraConfig(
                    r=lora.get("r", 8),
                    lora_alpha=lora.get("alpha", 16),
                    lora_dropout=lora.get("dropout", 0.1),
                    target_modules=lora.get("target_modules", "q_proj,v_proj").split(","),
                    bias=lora.get("bias", "none"),
                    task_type=TaskType.SEQ_CLS
                )
                base_model = get_peft_model(base_model, lora_config)
            elif "qlora" in peft_cfg:
                raise NotImplementedError("QLoRA belum didukung. Gunakan LoRA.")

        # Tokenisasi
        def tokenize_fn(examples):
            return tokenizer_local(
                examples["text"],
                truncation=True,
                padding="max_length",
                max_length=config.get("max_length", 128)
            )

        train_dataset = Dataset.from_pandas(train_df)
        val_dataset = Dataset.from_pandas(val_df)
        train_dataset = train_dataset.map(tokenize_fn, batched=True)
        val_dataset = val_dataset.map(tokenize_fn, batched=True)

        output_dir = f"./results/{session_id}"
        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=config.get("epoch", 5),
            per_device_train_batch_size=config.get("batch_size", 16),
            per_device_eval_batch_size=config.get("batch_size", 16),
            learning_rate=float(config.get("lr", 2e-5)),
            weight_decay=config.get("weight_decay", 0.01),
            evaluation_strategy="epoch",
            save_strategy="epoch",
            logging_dir=f"./logs/{session_id}",
            load_best_model_at_end=True,
            metric_for_best_model="accuracy",
            seed=random_seed,
            report_to="none"
        )

        def compute_metrics(eval_pred):
            logits, labels = eval_pred
            preds = logits.argmax(-1)
            return {
                "accuracy": accuracy_score(labels, preds),
                "f1": f1_score(labels, preds, average="weighted")
            }

        trainer = Trainer(
            model=base_model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            compute_metrics=compute_metrics,
        )

        trainer.train()

        # Simpan hasil training
        model_dir = f"./saved_models/{session_id}"
        trainer.save_model(model_dir)
        tokenizer_local.save_pretrained(model_dir)

        # Upload ke Supabase Storage
        bucket_name = "models"
        for root, dirs, files in os.walk(model_dir):
            for file in files:
                file_path = os.path.join(root, file)
                with open(file_path, "rb") as f:
                    supabase.storage.from_(bucket_name).upload(
                        f"session_{session_id}/{file}",
                        f.read(),
                        {"upsert": "true"}
                    )

        eval_metrics = trainer.evaluate()
        supabase.table("training_sessions").update({
            "status": "completed",
            "metrics": eval_metrics,
            "finished_at": "now()"
        }).eq("id", session_id).execute()

        logging.info(f"✅ Training session {session_id} completed.")

    except Exception as e:
        logging.error(f"Training session {session_id} gagal: {str(e)}")
        supabase.table("training_sessions").update({
            "status": "failed",
            "finished_at": "now()"
        }).eq("id", session_id).execute()


# ================== ENDPOINT ==================
class TrainStartResponse(BaseModel):
    message: str

@router.post("/train/start/{session_id}", response_model=TrainStartResponse)
async def start_training(session_id: int, background_tasks: BackgroundTasks):
    session_resp = supabase.table("training_sessions").select("status").eq("id", session_id).single().execute()
    if not session_resp.data:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan")
    if session_resp.data["status"] != "pending":
        raise HTTPException(status_code=400, detail="Sesi sudah berjalan/selesai")

    background_tasks.add_task(train_model, session_id)
    return {"message": f"Training untuk sesi {session_id} dimulai di background"}


@router.get("/train/status/{session_id}")
async def get_training_status(session_id: int):
    res = supabase.table("training_sessions").select("status, metrics, started_at, finished_at").eq("id", session_id).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan")
    return res.data


# ================== AKTIVASI MODEL ==================
@router.post("/model/activate/{model_id}")
async def activate_model(model_id: int):
    """Aktifkan model dari sesi training terakhir yang completed untuk model_id ini."""
    session_resp = supabase.table("training_sessions") \
        .select("id") \
        .eq("model_id", model_id) \
        .eq("status", "completed") \
        .order("created_at", desc=True) \
        .limit(1).single().execute()
    if not session_resp.data:
        raise HTTPException(status_code=404, detail="Tidak ada sesi training completed untuk model ini")

    session_id = session_resp.data["id"]
    try:
        load_model_from_storage(session_id)
        return {"message": f"Model session_{session_id} berhasil diaktifkan", "ready": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memuat model: {str(e)}")