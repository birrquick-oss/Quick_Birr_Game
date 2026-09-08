import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.database import SessionLocal, initialize_database
from app.models import User

# Routerዎች
from app.routers.games import router as games_router
from app.routers.cards import router as cards_router
from app.routers.users import router as users_router
from app.routers.transactions import router as transactions_router
from app.websocket import router as websocket_router, manager
from app.game_engine import engine


# =========================================================
# STARTUP & SHUTDOWN LIFESPAN EVENT
# =========================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. የዳታቤዝ ቴብሎችን ማዘጋጀት
    initialize_database()
    
    # 2. የቢንጎ ጨዋታ ኢንጂኑን በጀርባ (Background Task) ማስጀመር
    engine_task = asyncio.create_task(engine.start_game())
    
    yield  # አፕሊኬሽኑ በስራ ላይ የሚቆይበት ጊዜ
    
    # Shutdown ሲሆን ታስኩን ማቆም (Clean up)
    engine_task.cancel()


app = FastAPI(
    title="QUICK_BIRR GAMES",
    description="Quick Birr Games API & Telegram Mini App Backend",
    version="1.0.0",
    lifespan=lifespan
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
# 🌐 WEBSOCKET ENDPOINT (ለ ቴሌግራም ሚኒ አፕ እና ፍሮንትኤንድ)
# =========================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # ከተጫዋቹ/ከቴሌግራም አፕ የሚመጡ መልእክቶችን መቀበያ
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"⚠️ WebSocket connection error: {e}")
        manager.disconnect(websocket)


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
# HEALTH CHECK & API ROOT
# =========================================================

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "QUICK_BIRR GAMES",
        "version": "1.0.0",
        "game_engine_running": getattr(engine, "running", True)
    }


@app.get("/api")
def api_root():
    return {
        "message": "QUICK_BIRR GAMES API is running",
        "status": "online",
    }
