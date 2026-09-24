import json
import secrets
import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User, WalletTransaction, MinesGame  # ሟሟላቱን ያረጋግጡ

router = APIRouter(
    prefix="/api/mines",
    tags=["Mines Game"]
)


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
    mine_count: int = Field(default=3)


class RevealTileRequest(BaseModel):
    telegram_id: str
    game_id: int
    tile_index: int = Field(ge=0, le=24)


class CashoutRequest(BaseModel):
    telegram_id: str
    game_id: int


def calculate_multiplier(gems_found: int, mine_count: int) -> float:
    total_tiles = 25
    multiplier = 1.0
    for i in range(gems_found):
        multiplier *= (total_tiles - i) / (total_tiles - mine_count - i)
    return round(multiplier * 0.95, 2)  # 5% House Edge


# =========================================================
# START GAME
# =========================================================
@router.post("/start")
def start_mines(request: StartMinesRequest, db: Session = Depends(get_db)):
    telegram_id = str(request.telegram_id).strip()
    bet_amount = round(float(request.bet_amount), 2)
    mine_count = int(request.mine_count)

    if bet_amount not in ALLOWED_BETS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="የተሳሳተ የውርርድ መጠን።")

    if mine_count not in ALLOWED_MINES:
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

    # Pick Random Mine Positions (0-24)
    all_indices = list(range(25))
    mine_positions = secrets.SystemRandom().sample(all_indices, mine_count)

    # Create Game Record in DB using MinesGame Model
    new_game = MinesGame(
        user_id=user.id,
        bet_amount=bet_amount,
        mine_count=mine_count,
        mine_positions=json.dumps(mine_positions),
        revealed_positions=json.dumps([]),
        multiplier=1.0,
        status="playing",
        payout=0.0,
        balance_after=balance_after_stake,
        reference=reference
    )
    db.add(new_game)

    try:
        db.commit()
        db.refresh(user)
        db.refresh(new_game)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="ጨዋታውን ማስጀመር አልተቻለም።")

    return {
        "success": True,
        "game_id": new_game.id,
        "message": "💎 Choose a tile!",
        "balance": balance_after_stake,
        "bet_amount": bet_amount,
        "mine_count": mine_count,
        "multiplier": 1.0
    }


# =========================================================
# REVEAL TILE
# =========================================================
@router.post("/reveal")
def reveal_tile(request: RevealTileRequest, db: Session = Depends(get_db)):
    telegram_id = str(request.telegram_id).strip()
    tile_index = request.tile_index

    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ተጠቃሚው አልተገኘም።")

    # Fetch active game from Database
    game = db.query(MinesGame).filter(
        MinesGame.id == request.game_id,
        MinesGame.user_id == user.id,
        MinesGame.status == "playing"
    ).first()

    if not game:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ምንም የነቃ ጨዋታ አልተገኘም።")

    mine_positions = json.loads(game.mine_positions)
    revealed_positions = json.loads(game.revealed_positions)

    if tile_index in revealed_positions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ይህ ሳጥን ቀደም ብሎ ተከፍቷል።")

    # Hit Mine? (Loss)
    if tile_index in mine_positions:
        game.status = "completed"
        game.result = "loss"
        game.payout = 0.0
        game.completed_at = datetime.now(timezone.utc)
        
        db.commit()

        return {
            "success": True,
            "is_mine": True,
            "message": "💣 ቦምቡ ፈነዳ! ተሸንፈዋል።",
            "mine_positions": mine_positions
        }

    # Hit Gem! (Safe Tile)
    revealed_positions.append(tile_index)
    game.revealed_positions = json.dumps(revealed_positions)

    gems_found = len(revealed_positions)
    current_multiplier = calculate_multiplier(gems_found, game.mine_count)
    game.multiplier = current_multiplier

    db.commit()

    return {
        "success": True,
        "is_mine": False,
        "gems_found": gems_found,
        "multiplier": current_multiplier,
        "message": f"💎 SAFE! Multiplier: {current_multiplier}x"
    }


# =========================================================
# CASHOUT
# =========================================================
@router.post("/cashout")
def cashout_mines(request: CashoutRequest, db: Session = Depends(get_db)):
    telegram_id = str(request.telegram_id).strip()

    user = db.query(User).filter(User.telegram_id == telegram_id).with_for_update().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ተጠቃሚው አልተገኘም።")

    # Fetch active game from Database
    game = db.query(MinesGame).filter(
        MinesGame.id == request.game_id,
        MinesGame.user_id == user.id,
        MinesGame.status == "playing"
    ).first()

    if not game:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ምንም የነቃ ጨዋታ አልተገኘም።")

    revealed_positions = json.loads(game.revealed_positions)
    gems_found = len(revealed_positions)

    if gems_found == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ወደ ገንዘብ ለመቀየር ቢያንስ 1 ሳጥን መክፈት አለብዎት።")

    multiplier = calculate_multiplier(gems_found, game.mine_count)
    win_amount = round(game.bet_amount * multiplier, 2)

    final_balance = round(float(user.balance or 0) + win_amount, 2)
    user.balance = final_balance

    # Update Game state in DB
    game.status = "completed"
    game.result = "win"
    game.payout = win_amount
    game.balance_after = final_balance
    game.completed_at = datetime.now(timezone.utc)

    # Record Win Transaction
    win_tx = WalletTransaction(
        user_id=user.id,
        transaction_type="game_win_mines",
        amount=win_amount,
        balance_after=final_balance,
        game="mines",
        reference=game.reference,
        description=f"Mines Cashout - {multiplier}x ({gems_found} gems)"
    )
    db.add(win_tx)

    mine_positions = json.loads(game.mine_positions)

    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Cashout ማድረግ አልተቻለም።")

    return {
        "success": True,
        "payout": win_amount,
        "multiplier": multiplier,
        "balance": final_balance,
        "mine_positions": mine_positions,
        "message": f"💰 CASH OUT: {win_amount:.2f} ETB"
    }
