from fastapi import APIRouter

router = APIRouter(prefix="/datasets", tags=["Manajemen Dataset"])

# Di sini bisa dibuat endpoint untuk CRUD dataset (misal GET /datasets, POST /datasets, dll)
# Untuk sementara, siapkan kerangka saja
@router.get("")
def list_datasets():
    # Return list dataset dari Supabase (tabel datasets)
    pass