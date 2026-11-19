"""App entry point. Run with:  uvicorn main:app --reload"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import config
from database import close_mongo, connect_to_mongo
from routes.chat_routes import router as chat_router

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.validate_settings()
    await connect_to_mongo()
    print("Connected to MongoDB. Open http://127.0.0.1:8000")
    yield
    await close_mongo()


app = FastAPI(title="AI Chat Assistant", lifespan=lifespan)
app.include_router(chat_router)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/")
async def index():
    return FileResponse(BASE_DIR / "static" / "index.html")
