from flask import Blueprint, request, jsonify
import pandas as pd
import json
import torch
import os

train_bp = Blueprint('train', __name__)

# ================= DATASET CLASS =================
class CustomDataset(torch.utils.data.Dataset):
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __getitem__(self, idx):
        return {
            "input_ids": torch.tensor(self.encodings["input_ids"][idx]),
            "attention_mask": torch.tensor(self.encodings["attention_mask"][idx]),
            "labels": torch.tensor(self.labels[idx])
        }

    def __len__(self):
        return len(self.labels)


# ================= TRAIN =================
@train_bp.route('/train', methods=['POST'])
def train_model():
    try:
        # ================= FILE =================
        file = request.files.get('file')
        if not file:
            return jsonify({"error": "File tidak ditemukan"}), 400

        config = json.loads(request.form.get('config', "{}"))

        # ================= AMBIL CONFIG TAMBAHAN =================
        indobert = config.get("indobert", {})
        general = config.get("general", {})
        validation = config.get("validation", {})

        df = pd.read_csv(file)

        # ================= VALIDASI =================
        if 'teks' not in df.columns or 'label' not in df.columns:
            return jsonify({"error": "CSV harus punya kolom teks dan label"}), 400

        texts = df['teks'].astype(str).tolist()

        # ================= LABEL =================
        labels_raw = df['label'].astype(int).tolist()

        label_to_id = {1:0,2:1,3:2,4:3,5:4,6:5,7:6}

        labels = []
        for l in labels_raw:
            if l not in label_to_id:
                return jsonify({"error": f"Label tidak valid: {l}"}), 400
            labels.append(label_to_id[l])


        # ================= SPLIT DATA =================
        from sklearn.model_selection import train_test_split

        from sklearn.model_selection import train_test_split, StratifiedKFold

        if validation.get("method") == "split":

            train_ratio = validation.get("split_ratio", 0.8)

            X_train, X_test, y_train, y_test = train_test_split(
                texts,
                labels,
                test_size=1 - train_ratio,
                random_state=general.get("random_state", 42),
                shuffle=general.get("shuffle", True)
            )

            texts = X_train
            labels = y_train


        elif validation.get("method") == "kfold":

            k = validation.get("k_fold", 5)
            epoch_fold = validation.get("epoch_fold", 3)

            skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=42)

            all_losses = []

            for fold, (train_idx, val_idx) in enumerate(skf.split(texts, labels)):

                print(f"===== FOLD {fold+1} =====")

                X_train = [texts[i] for i in train_idx]
                y_train = [labels[i] for i in train_idx]

                # TOKENIZE PER FOLD
                encodings = tokenizer(
                    X_train,
                    truncation=True,
                    padding=True,
                    max_length=max_length
                )

                dataset = CustomDataset(encodings, y_train)

                training_args = TrainingArguments(
                    output_dir=f"./models/fold_{fold}",
                    num_train_epochs=epoch_fold,  # 🔥 pakai ini
                    per_device_train_batch_size=batch,
                    learning_rate=lr,
                    logging_steps=10
                )

                trainer = Trainer(
                    model=model,
                    args=training_args,
                    train_dataset=dataset
                )

                trainer.train()

            return jsonify({
                "message": f"K-Fold Training selesai ({k} fold)"
            })

        # ================= CONFIG =================
        epoch = int(config.get("epoch", 3))
        lr = float(config.get("lr", 2e-5))
        batch = int(config.get("batch", 8))
        peft = config.get("peft", {})

        # ================= LOAD MODEL =================
        from transformers import AutoTokenizer, AutoModelForSequenceClassification

        model_name = indobert.get("model_name", "indobenchmark/indobert-base-p1")
        max_length = indobert.get("max_length", 128)
        optimizer = indobert.get("optimizer", "adamw")
        weight_decay = indobert.get("weight_decay", 0.01)
        warmup = indobert.get("warmup", 0.1)

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSequenceClassification.from_pretrained(
            model_name,
            num_labels=7
        )

        # ================= PEFT =================
        if peft and "lora" in peft:
            from peft import LoraConfig, get_peft_model

            lora_cfg = peft["lora"]

            peft_config = LoraConfig(
                r=lora_cfg.get("r", 8),
                lora_alpha=lora_cfg.get("alpha", 16),
                lora_dropout=lora_cfg.get("dropout", 0.1),
                bias=lora_cfg.get("bias", "none"),
                task_type="SEQ_CLS"
            )

            model = get_peft_model(model, peft_config)

        # ================= DEVICE =================
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model.to(device)

        # ================= TOKENIZE =================
        encodings = tokenizer(
            texts,
            truncation=True,
            padding=True,
            max_length=max_length
        )

        dataset = CustomDataset(encodings, labels)

        # ================= TRAINING =================
        from transformers import Trainer, TrainingArguments

        training_args = TrainingArguments(
        output_dir="./models/output",
        num_train_epochs=epoch,
        per_device_train_batch_size=batch,
        learning_rate=lr,
        weight_decay=weight_decay,
        warmup_ratio=warmup,
        optim=optimizer,
        logging_steps=10,
        remove_unused_columns=False
        )

        # ================= EARLY STOPPING =================
        from transformers import EarlyStoppingCallback

        callbacks = []

        if general.get("early_stopping", 0) > 0:
            callbacks.append(EarlyStoppingCallback(
                early_stopping_patience=general.get("early_stopping")
            ))

        trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        callbacks=callbacks
    )

        trainer.train()

        # ================= SAVE MODEL =================
        os.makedirs("./models", exist_ok=True)

        save_path = f"./models/model_{int(pd.Timestamp.now().timestamp())}"
        model.save_pretrained(save_path)
        tokenizer.save_pretrained(save_path)

        # ================= SIMPAN HISTORY =================
        history_path = "./models/history.json"

        if not os.path.exists(history_path):
            with open(history_path, "w") as f:
                json.dump([], f)

        with open(history_path, "r") as f:
            history = json.load(f)

        history.append({
            "nama_file": file.filename,
            "model_path": save_path,
            "model": "IndoBERT + PEFT" if peft else "IndoBERT",
            "epoch": epoch
        })

        with open(history_path, "w") as f:
            json.dump(history, f, indent=4)

        return jsonify({
            "message": "Training selesai",
            "model_path": save_path
        })

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": str(e)}), 500


# ================= GET MODELS =================
@train_bp.route('/models', methods=['GET'])
def get_models():
    try:
        with open("./models/history.json", "r") as f:
            data = json.load(f)
        return jsonify(data)
    except:
        return jsonify([])