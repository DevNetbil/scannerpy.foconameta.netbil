"""
Script para executar a API FastAPI
"""
import uvicorn
from src.api import app

if __name__ == "__main__":
    uvicorn.run(
        "src.api:app",
        host="0.0.0.0",
        port=80,
        reload=True,
        log_level="info"
    )
