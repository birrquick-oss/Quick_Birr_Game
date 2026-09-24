import json
import random
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User, WalletTransaction, MinesGame  # MinesGame Model መጠቀምህ እርግጠኛ ሁን


router = APIRouter(
    prefix="/api/mines",
    tags=["Mines"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


GRID_SIZE = 25
ALLOWED_BETS = {10.0, 20.0, 50.0}
ALLOWED_MINES = {3, 5, 10}


class StartMinesRequest(BaseModel):
    telegram_id: str
    bet_amount: float = Field(gt=0)
    mine_count: int = Field(default=3)  # ከ Frontend የሚመጣውን የቦምብ ብዛት ይቀበላል


class RevealMinesRequest(BaseModel):
    telegram_id: str
    game_id: int | None = None
    tile_index: int = Field(ge=0, le=GRID_SIZE - 1)  # Frontend tile_index ስለሚልክ


class CashoutMinesRequest(BaseModel):
    telegram_id: str
    game_id: int | None = None


def get_user(db: Session, telegram_id: str):
    return (
        db.query(User)
        .filter(User.telegram_id == telegram_id)
        .with_for_update()
        .first()
    )


def get_active_round(db: Session, user_id: int):
    return (
        db.query(MinesGame)
        .filter(
            MinesGame.user_id == user_id,
            MinesGame.status == "playing"
        )
        .order_by(MinesGame.id.desc())
        .first()
    )


def calculate_multiplier(safe_count: int, mine_count: int) -> float:
    if safe_count <= 0:
        return 1.0
    
    total_tiles = 25
    multiplier = 1.0
    for i in range(safe_count):
        multiplier *= (total_tiles - i) / (total_tiles - mine_count - i)
    return round(multiplier * 0.95, 2)  # 5% House edge


# =========================================================
# START GAME
# =========================================================

@router.post("/start")
def start_mines(request: StartMinesRequest, db: Session = Depends(get_db)):
    telegram_id = str(request.telegram_id).strip()
    bet_amount = round(float(request.bet_amount), 2)
    mine_count = int(request.mine_count)

    if bet_amount not in ALLOWED_BETS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="የተሳሳተ የውርርድ መጠን። 10, 20 ወይም 50 ETB ይምረጡ።"
        )

    if mine_count not in ALLOWED_MINES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="የተሳሳተ የቦምብ ብዛት። (3, 5, 10 ይምረጡ)"
        )

    user = get_user(db, telegram_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ተጠቃሚው አልተገኘም።")

    if getattr(user, "is_banned", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="አካውንትዎ ታግዷል።")

    # ያልተጠናቀቀ ጨዋታ ካለ ማረጋገጥ
    existing_round = get_active_round(db, user.id)
    if existing_round:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="እባክዎን አስቀድመው የጀመሩትን ጨዋታ ያጠናቅቁ።")

    current_balance = round(float(user.balance or 0), 2)
    if current_balance < bet_amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="በቂ ባላንስ የለዎትም!")

    # ቦምቦችን በዘደይ መደበቅ
    mine_positions = sorted(random.sample(range(GRID_SIZE), mine_count))

    # ሂሳብ መቀነስ
    balance_after = round(current_balance - bet_amount, 2)
    user.balance = balance_after
    reference = f"MINES-{uuid.uuid4().hex[:16]}"

    stake_tx = WalletTransaction(
        user_id=user.id,
        transaction_type="game_stake_mines",
        amount=-bet_amount,
        balance_after=balance_after,
        game="mines",
        reference=reference,
        description="Mines stake"
    )
    db.add(stake_tx)

    mines_game = MinesGame(
        user_id=user.id,
        bet_amount=bet_amount,
        mine_count=mine_count,
        mine_positions=json.dumps(mine_positions),
        revealed_positions="[]",
        multiplier=1.0,
        payout=0.0,
        balance_after=balance_after,
        status="playing",
        reference=reference
    )
    db.add(mines_game)

    try:
        db.commit()
        db.refresh(mines_game)
        db.refresh(user)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="ጨዋታውን ማስጀመር አልተቻለም።")

    return {
        "success": True,
        "game_id": mines_game.id,
        "mine_count": mine_count,
        "bet_amount": bet_amount,
        "multiplier": 1.0,
        "payout": 0.0,
        "balance": round(float(user.balance), 2),
        "message": "💎 ጨዋታው ተጀምሯል! ሳጥን ይምረጡ።"
    }


# =========================================================
# REVEAL TILE
# =========================================================

@router.post("/reveal")
def reveal_mines_tile(request: RevealMinesRequest, db: Session = Depends(get_db)):
    telegram_id = str(request.telegram_id).strip()
    position = int(request.tile_index)

    user = get_user(db, telegram_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ተጠቃሚው አልተገኘም።")

    mines_game = get_active_round(db, user.id)
    if not mines_game:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ምንም የነቃ ጨዋታ አልተገኘም።")

    mine_positions = json.loads(mines_game.mine_positions)
    revealed_positions = json.loads(mines_game.revealed_positions or "[]")

    if position in revealed_positions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ይህ ሳጥን ቀደም ብሎ ተከፍቷል።")

    # ቦምብ ከተነካ (ተሸነፈ)
    if position in mine_positions:
        mines_game.status = "completed"
        mines_game.result = "loss"
        mines_game.completed_at = datetime.now(timezone.utc)
        mines_game.multiplier = 0.0
        mines_game.payout = 0.0
        db.commit()

        return {
            "success": True,
            "is_mine": True,
            "mine_positions": mine_positions,
            "multiplier": 0.0,
            "payout": 0.0,
            "balance": round(float(user.balance), 2),
            "message": "💣 ቦምቡ ፈነዳ! ተሸንፈዋል።"
        }

    # 💎 ትክክለኛ ሳጥን ከተከፈተ
    revealed_positions.append(position)
    safe_count = len(revealed_positions)
    multiplier = calculate_multiplier(safe_count, mines_game.mine_count)
    payout = round(mines_game.bet_amount * multiplier, 2)

    mines_game.revealed_positions = json.dumps(revealed_positions)
    mines_game.multiplier = multiplier
    mines_game.payout = payout
    db.commit()

    return {
        "success": True,
        "is_mine": False,
        "position": position,
        "multiplier": multiplier,
        "payout": payout,
        "balance": round(float(user.balance), 2),
        "message": f"💎 SAFE! Multiplier: {multiplier}x"
    }


# =========================================================
# CASHOUT
# =========================================================

@router.post("/cashout")
def cashout_mines(request: CashoutMinesRequest, db: Session = Depends(get_db)):
    telegram_id = str(request.telegram_id).strip()

    user = get_user(db, telegram_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ተጠቃሚው አልተገኘም።")

    mines_game = get_active_round(db, user.id)
    if not mines_game:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ምንም የነቃ ጨዋታ አልተገኘም።")

    revealed_positions = json.loads(mines_game.revealed_positions or "[]")
    if not revealed_positions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ወደ ገንዘብ ለመቀየር ቢያንስ 1 ሳጥን መክፈት አለብዎት።")

    payout = round(float(mines_game.payout or 0), 2)
    multiplier = float(mines_game.multiplier or 1)

    # ጨዋታውን ማጠናቀቅ እና ገንዘብ መጨመር
    mines_game.status = "completed"
    mines_game.result = "win"
    mines_game.completed_at = datetime.now(timezone.utc)

    user.balance = round(float(user.balance) + payout, 2)
    mines_game.balance_after = user.balance

    win_tx = WalletTransaction(
        user_id=user.id,
        transaction_type="game_win_mines",
        amount=payout,
        balance_after=user.balance,
        game="mines",
        reference=f"MINES-CASH-{uuid.uuid4().hex[:12]}",
        description=f"Mines cashout - {multiplier}x"
    )
    db.add(win_tx)

    mine_positions = json.loads(mines_game.mine_positions)

    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Cashout ማድረግ አልተቻለም።")

    return {
        "success": True,
        "payout": payout,
        "multiplier": multiplier,
        "balance": round(float(user.balance), 2),
        "mine_positions": mine_positions,
        "message": f"💰 CASH OUT: {payout:.2f} ETB"
    }
