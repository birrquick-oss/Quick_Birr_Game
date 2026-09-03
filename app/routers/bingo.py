from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.wallet import process_game_stake, process_game_win

router = APIRouter(prefix="/api/bingo", tags=["Bingo Game"])

class PlayBingoRequest(BaseModel):
    user_id: int
    stake: float = 10.0  # Default stake 10 ETB
    won: bool = False
    win_amount: float = 0.0

@router.post("/play")
def play_bingo(request: PlayBingoRequest, db: Session = Depends(get_db)):
    # 1. Deduct Stake from Central Wallet
    user = process_game_stake(
        db=db,
        user_id=request.user_id,
        amount=request.stake,
        game_name="Bingo"
    )

    # 2. Add Winnings if player won
    if request.won and request.win_amount > 0:
        user = process_game_win(
            db=db,
            user_id=request.user_id,
            amount=request.win_amount,
            game_name="Bingo"
        )

    return {
        "status": "success",
        "game": "Bingo",
        "current_balance": user.balance,
        "message": f"Played Bingo with {request.stake} ETB stake."
    }
