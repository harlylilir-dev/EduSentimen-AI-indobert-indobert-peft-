from flask import request, jsonify
from backend.app import app
from backend.services.model_service import *

@app.route('/models', methods=['GET'])
def get_models():
    return jsonify(load_models())

@app.route('/models', methods=['POST'])
def save_model():
    data = request.json
    save_model_config(data)
    return jsonify({"message": "Model disimpan"})

@app.route('/models/<id>', methods=['DELETE'])
def delete_model(id):
    delete_model_config(id)
    return jsonify({"message": "Model dihapus"})