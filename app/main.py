import os
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.database import get_db, initialize_database
from app.models import User
from app.routers.transactions import router as transactions_router


# =========================================================
# QUICK_BIRR GAMES MAIN APPLICATION
# =========================================================

app = FastAPI(
    title="QUICK_BIRR GAMES",
    description="Quick Birr Games API",
    version="1.0.0",
)


# =========================================================
# INCLUDE ROUTERS
# =========================================================

app.include_router(transactions_router)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# MOUNT STATIC FILES (ይህ እንዳይበላሽ /static አቃፊን ብቻ ማየት አለበት)
# =========================================================

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


# =========================================================
# STARTUP (Tables በ PostgreSQL ላይ መፈጠራቸውን ያረጋግጣል)
# =========================================================

@app.on_event("startup")
def startup_event():
    initialize_database()


# =========================================================
# ROOT ROUTE (Serves Front-end HTML)
# =========================================================

@app.get("/")
def read_root():
    return FileResponse("index.html")


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
# ROOT API
# =========================================================

@app.get("/api")
def api_root():
    return {
        "message": "QUICK_BIRR GAMES API is running",
        "status": "online",
    }


# =========================================================
# GET USER
# =========================================================

@app.get("/api/users/{telegram_id}")
def get_user(
    telegram_id: str,
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(User.telegram_id == str(telegram_id))
        .first()
    )

    if not user:
        return {
            "success": False,
            "message": "User not found",
        }

    return {
        "success": True,
        "user": {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "telegram_username": user.telegram_username,
            "first_name": user.first_name,
            "balance": round(user.balance or 0.0, 2),
            "is_banned": bool(getattr(user, "is_banned", False)),
        },
    }


# =========================================================
# CREATE / GET USER
# =========================================================

@app.post("/api/users")
def create_user(
    telegram_id: str,
    telegram_username: str | None = None,
    first_name: str | None = None,
    db: Session = Depends(get_db),
):
    existing_user = (
        db.query(User)
        .filter(User.telegram_id == str(telegram_id))
        .first()
    )

    if existing_user:
        return {
            "success": True,
            "created": False,
            "message": "User already exists",
            "user": {
                "id": existing_user.id,
                "telegram_id": existing_user.telegram_id,
                "telegram_username": existing_user.telegram_username,
                "first_name": existing_user.first_name,
                "balance": round(existing_user.balance or 0.0, 2),
            },
        }

    user = User(
        telegram_id=str(telegram_id),
        telegram_username=telegram_username,
        first_name=first_name,
        balance=0.0,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "created": True,
        "message": "User created",
        "user": {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "telegram_username": user.telegram_username,
            "first_name": user.first_name,
            "balance": round(user.balance or 0.0, 2),
        },
    }
