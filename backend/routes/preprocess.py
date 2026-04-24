from flask import Blueprint, request, jsonify
import traceback
from backend.services.preprocessing_service import process_file

preprocess_bp = Blueprint('preprocess', __name__)

@preprocess_bp.route('/preprocess', methods=['POST'])
def preprocess():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "File tidak ditemukan"}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({"error": "File kosong"}), 400

        hasil, error = process_file(file)

        if error:
            return jsonify({"error": error}), 400

        return jsonify({
            "jumlah_data": len(hasil),
            "data": hasil
        })

    except Exception as e:
        print("ERROR BESAR:")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500