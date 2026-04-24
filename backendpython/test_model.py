from transformers import AutoModel, AutoTokenizer

model_name = "indobenchmark/indobert-base-p1"

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name)

print("✅ IndoBERT berhasil load")