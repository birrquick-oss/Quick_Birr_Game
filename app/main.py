import os
import asyncio
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.database import SessionLocal, initialize_database
from app.models import User

# Routerዎች - ትክክለኛው መንገድ (app.routers)
from app.routers.games import router as games_router
from app.routers.cards import router as cards_router
from app.routers.users import router as users_router
from app.routers.transactions import router as transactions_router
from app.websocket import router as websocket_router
from app.game_engine import engine


app = FastAPI(
    title="QUICK_BIRR GAMES",
    description="Quick Birr Games API",
    version="1.0.0",
)


# =========================================================
# CORS CONFIGURATION
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# INCLUDE ROUTERS
# =========================================================

app.include_router(games_router)
app.include_router(cards_router)
app.include_router(users_router)
app.include_router(transactions_router)
app.include_router(websocket_router)


# =========================================================
# MOUNT STATIC FILES
# =========================================================

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


# =========================================================
# DEPENDENCY
# =========================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================================================
# STARTUP (Database Init & Game Engine Background Loop)
# =========================================================

@app.on_event("startup")
async def startup_event():
    # 1. የዳታቤዝ ቴብሎችን ማዘጋጀት
    initialize_database()
    # 2. የቢንጎ ጨዋታ ኢንጂኑን በጀርባ (Background Task) ማስጀመር
    asyncio.create_task(engine.start_game())


# =========================================================
# ROOT ROUTE (Serves Front-end HTML)
# =========================================================

@app.get("/")
def read_root():
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    elif os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"message": "Quick Birr Games Server Running"}


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "QUICK_BIRR GAMES",
        "version": "1.0.0",
    }


# =========================================================
# API ROOT
# =========================================================

@app.get("/api")
def api_root():
    return {
        "message": "QUICK_BIRR GAMES API is running",
        "status": "online",
    }
