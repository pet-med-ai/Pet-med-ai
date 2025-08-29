from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
@app.get("/healthz")
def healthz():
    return {"status": "ok"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/ping")
def ping():
    return {"ok": True}
