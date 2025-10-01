from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.chatgpt import router as chatgpt_router
from routes.cotacao import router as cotacao_router

app = FastAPI(title="Cotação IA - Vidda Seguros")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar rotas
app.include_router(chatgpt_router, prefix="/api")
app.include_router(cotacao_router, prefix="/api")

@app.get("/api/health")
async def health_check():
    return {
        "service": "Cotação com IA - Vidda Seguros",
        "status": "OK",
        "timestamp": "2025-09-29T01:04:51.232132"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
