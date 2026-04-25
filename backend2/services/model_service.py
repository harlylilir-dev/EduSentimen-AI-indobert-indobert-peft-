import json
import os

FILE = "backend/models/model_config.json"

def load_models():
    if not os.path.exists(FILE):
        return []
    with open(FILE, "r") as f:
        return json.load(f)

def save_model_config(data):
    models = load_models()
    models.append(data)
    with open(FILE, "w") as f:
        json.dump(models, f, indent=4)

def delete_model_config(model_id):
    models = load_models()
    models = [m for m in models if m["id"] != model_id]
    with open(FILE, "w") as f:
        json.dump(models, f, indent=4)