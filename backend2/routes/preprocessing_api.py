from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import re
import io

# ================= INIT APP =================
app = Flask(__name__)
CORS(app)

# ================= CLEANING =================
def clean_text(text):
    text = str(text).lower()
    text = re.sub(r'@(\w+)', r'\1', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'#(\w+)', r'\1', text)
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# ================= API =================
@app.route('/preprocess', methods=['POST'])
def preprocess():
    try:
        # 🔥 VALIDASI FILE
        if 'file' not in request.files:
            return jsonify({"error": "File tidak ditemukan"}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({"error": "File kosong"}), 400

        # 🔥 BACA FILE (FIX UTAMA DI SINI)
        try:
            content = file.stream.read().decode("utf-8", errors="ignore")
            stream = io.StringIO(content)

            # auto detect separator
            df = pd.read_csv(stream, sep=None, engine='python')
        except Exception as e:
            return jsonify({"error": f"Gagal membaca CSV: {str(e)}"}), 400

        # 🔥 VALIDASI DATAFRAME
        if df.empty:
            return jsonify({"error": "CSV kosong atau tidak terbaca"}), 400

        print("=== DEBUG DATA ===")
        print("Kolom:", df.columns.tolist())
        print("Jumlah data:", len(df))
        print(df.head())

        # 🔥 CEK KOLOM WAJIB
        if 'teks' not in df.columns:
            return jsonify({
                "error": "Kolom 'teks' tidak ditemukan. Pastikan header CSV = teks"
            }), 400

        hasil = []

        # 🔥 LOOP DATA
        for i, row in df.iterrows():
            try:
                teks = str(row['teks'])
                cleaned = clean_text(teks)

                hasil.append({
                    "teks": teks,
                    "cleaned": cleaned
                })
            except Exception as err:
                print(f"ERROR BARIS {i}:", err)

        return jsonify({
            "jumlah_data": len(hasil),
            "data": hasil
        })

    except Exception as e:
        print("ERROR BESAR:", e)
        return jsonify({"error": str(e)}), 500

# ================= TEST ROUTE =================
@app.route('/')
def home():
    return "API Preprocessing Aktif 🚀"

# ================= RUN =================
if __name__ == '__main__':
    app.run(debug=True, port=5000)