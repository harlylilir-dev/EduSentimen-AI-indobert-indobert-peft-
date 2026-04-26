from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import raw_datasets, clean_datasets, preprocessing_admin, login_admin, predict, upload_csv, dashboard_admin
from routers import pengaturan_admin

app = FastAPI(
    title="EduSentiment AI Backend",
    max_request_body_size=100_000_000
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
app.include_router(pengaturan_admin.router)

@app.get("/")
def root():
    # Ambil status model dari pengaturan_admin
    from routers.pengaturan_admin import MODEL_READY
    return {
        "message": "EduSentiment AI Backend",
        "model_ready": MODEL_READY
    }