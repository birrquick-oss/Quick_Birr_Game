import secrets
import uuid
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User, WalletTransaction

router = APIRouter(
    prefix="/api/mines",
    tags=["Mines Game"]
)

# Active games stored in-memory
ACTIVE_MINES_GAMES: Dict[str, dict] = {}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


ALLOWED_BETS = {10.0, 20.0, 50.0}
ALLOWED_MINES = {1, 3, 5, 10}


class StartMinesRequest(BaseModel):
    telegram_id: str
    bet_amount: float = Field(gt=0)
    mines_count: int = Field(default=3)


class RevealTileRequest(BaseModel):
    telegram_id: str
    tile_index: int = Field(ge=0, le=24)


class CashoutRequest(BaseModel):
    telegram_id: str


def calculate_multiplier(gems_found: int, mines_count: int) -> float:
    total_tiles = 25
    multiplier = 1.0
    for i in range(gems_found):
        multiplier *= (total_tiles - i) / (total_tiles - mines_count - i)
    return round(multiplier * 0.95, 2)  # 5% House Edge


# =========================================================
# START GAME
# =========================================================
@router.post("/start")
def start_mines(request: StartMinesRequest, db: Session = Depends(get_db)):
    telegram_id = str(request.telegram_id).strip()
    bet_amount = round(float(request.bet_amount), 2)
    mines_count = int(request.mines_count)

    if bet_amount not in ALLOWED_BETS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="የተሳሳተ የውርርድ መጠን።")

    if mines_count not in ALLOWED_MINES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="የተሳሳተ የቦምብ ብዛት።")

    user = db.query(User).filter(User.telegram_id == telegram_id).with_for_update().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ተጠቃሚው አልተገኘም።")

    if getattr(user, "is_banned", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="አካውንትዎ ታግዷል።")

    current_balance = round(float(user.balance or 0), 2)
    if current_balance < bet_amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"በቂ ባላንስ የለዎትም! ({current_balance:.2f} ETB)")

    # Deduct Stake
    balance_after_stake = round(current_balance - bet_amount, 2)
    user.balance = balance_after_stake
    reference = f"MINES-{uuid.uuid4().hex[:16]}"

    stake_tx = WalletTransaction(
        user_id=user.id,
        transaction_type="game_stake_mines",
        amount=-bet_amount,
        balance_after=balance_after_stake,
        game="mines",
        reference=reference,
        description="Mines game stake"
    )
    db.add(stake_tx)

    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="ጨዋታውን ማስጀመር አልተቻለም።")

    # Pick Random Mine Positions (0-24)
    all_indices = list(range(25))
    mine_positions = secrets.SystemRandom().sample(all_indices, mines_count)

    # Save State
    ACTIVE_MINES_GAMES[telegram_id] = {
        "user_id": user.id,
        "bet_amount": bet_amount,
        "mines_count": mines_count,
        "mine_positions": mine_positions,
        "revealed_tiles": [],
        "reference": reference,
        "is_active": True
    }

    return {
        "success": True,
        "message": "ጨዋታው ተጀምሯል!",
        "balance": balance_after_stake,
        "bet_amount": bet_amount,
        "mines_count": mines_count
    }


# =========================================================
# REVEAL TILE
# =========================================================
@router.post("/reveal")
def reveal_tile(request: RevealTileRequest, db: Session = Depends(get_db)):
    telegram_id = str(request.telegram_id).strip()
    tile_index = request.tile_index

    game = ACTIVE_MINES_GAMES.get(telegram_id)
    if not game or not game["is_active"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ምንም የነቃ ጨዋታ አልተገኘም።")

    if tile_index in game["revealed_tiles"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ይህ ሳጥን ቀደም ብሎ ተከፍቷል።")

    # Hit Mine?
    if tile_index in game["mine_positions"]:
        mine_positions = game["mine_positions"]
        del ACTIVE_MINES_GAMES[telegram_id]  # End Game

        return {
            "success": True,
            "is_mine": True,
            "message": "💣 ቦምቡ ፈነዳ! ተሸንፈዋል።",
            "mine_positions": mine_positions
        }

    # Hit Gem!
    game["revealed_tiles"].append(tile_index)
    gems_found = len(game["revealed_tiles"])
    current_multiplier = calculate_multiplier(gems_found, game["mines_count"])
    next_multiplier = calculate_multiplier(gems_found + 1, game["mines_count"])

    return {
        "success": True,
        "is_mine": False,
        "gems_found": gems_found,
        "current_multiplier": current_multiplier,
        "next_multiplier": next_multiplier,
        "message": f"💎 ጌም አግኝተዋል! ብዛቱ: {current_multiplier}x"
    }


# =========================================================
# CASHOUT
# =========================================================
@router.post("/cashout")
def cashout_mines(request: CashoutRequest, db: Session = Depends(get_db)):
    telegram_id = str(request.telegram_id).strip()

    game = ACTIVE_MINES_GAMES.get(telegram_id)
    if not game or not game["is_active"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ምንም የነቃ ጨዋታ አልተገኘም።")

    gems_found = len(game["revealed_tiles"])
    if gems_found == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ወደ ገንዘብ ለመቀየር ቢያንስ 1 ሳጥን መክፈት አለብዎት።")

    multiplier = calculate_multiplier(gems_found, game["mines_count"])
    win_amount = round(game["bet_amount"] * multiplier, 2)

    user = db.query(User).filter(User.telegram_id == telegram_id).with_for_update().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ተጠቃሚው አልተገኘም።")

    final_balance = round(float(user.balance or 0) + win_amount, 2)
    user.balance = final_balance

    win_tx = WalletTransaction(
        user_id=user.id,
        transaction_type="game_win_mines",
        amount=win_amount,
        balance_after=final_balance,
        game="mines",
        reference=game["reference"],
        description=f"Mines Cashout - {multiplier}x ({gems_found} gems)"
    )
    db.add(win_tx)

    mine_positions = game["mine_positions"]
    del ACTIVE_MINES_GAMES[telegram_id]

    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Cashout ማድረግ አልተቻለም።")

    return {
        "success": True,
        "win_amount": win_amount,
        "multiplier": multiplier,
        "balance": final_balance,
        "mine_positions": mine_positions,
        "message": f"🎉 እንኳን ደስ አለዎት! {win_amount:.2f} ETB አሸንፈዋል"
    }
