from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 🔥 IMPORT ROUTE
from backend.routes.train import train_bp
from backend.routes.preprocess import preprocess_bp

# 🔥 REGISTER
app.register_blueprint(train_bp)
app.register_blueprint(preprocess_bp)

@app.route('/')
def home():
    return "API Aktif 🚀"