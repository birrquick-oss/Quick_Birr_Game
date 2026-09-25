import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User, WalletTransaction


router = APIRouter(
    prefix="/api/crash",
    tags=["Crash / Aviator"]
)


# =========================================================
# DATABASE
# =========================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================================================
# REQUEST MODELS
# =========================================================

class PlayCrashRequest(BaseModel):
    telegram_id: str
    bet_amount: float = Field(gt=0)
    cashout_multiplier: float = Field(gt=1.0)


ALLOWED_BETS = {10.0, 20.0, 50.0, 100.0}


# =========================================================
# PLAY CRASH
# =========================================================

@router.post("/play")
def play_crash(
    request: PlayCrashRequest,
    db: Session = Depends(get_db)
):
    telegram_id = str(request.telegram_id).strip()
    bet_amount = round(float(request.bet_amount), 2)
    user_multiplier = round(float(request.cashout_multiplier), 2)

    if bet_amount not in ALLOWED_BETS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid bet amount."
        )

    if not telegram_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram ID is required."
        )

    # Lock user row
    user = (
        db.query(User)
        .filter(User.telegram_id == telegram_id)
        .with_for_update()
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    if getattr(user, "is_banned", 0):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is currently restricted."
        )

    current_balance = round(float(user.balance or 0), 2)

    if current_balance < bet_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient balance! Your balance is {current_balance:.2f} ETB."
        )

    # Generate Crash Point (between 1.00x and 10.00x)
    crash_point = round(secrets.SystemRandom().uniform(1.00, 10.00), 2)

    won = user_multiplier <= crash_point
    win_amount = round(bet_amount * user_multiplier, 2) if won else 0.0

    balance_before = current_balance
    balance_after_stake = round(balance_before - bet_amount, 2)
    final_balance = round(balance_after_stake + win_amount, 2)

    user.balance = final_balance
    reference = f"CRASH-{uuid.uuid4().hex[:16]}"

    # Stake transaction
    stake_transaction = WalletTransaction(
        user_id=user.id,
        transaction_type="game_stake_crash",
        amount=-bet_amount,
        balance_after=balance_after_stake,
        game="crash",
        reference=reference,
        description="Crash game stake"
    )
    db.add(stake_transaction)

    # Win transaction
    if won and win_amount > 0:
        win_transaction = WalletTransaction(
            user_id=user.id,
            transaction_type="game_win_crash",
            amount=win_amount,
            balance_after=final_balance,
            game="crash",
            reference=reference,
            description=f"Crash game win - {user_multiplier}x"
        )
        db.add(win_transaction)

    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Game could not be completed. Please try again."
        )

    message = f"🎉 Won {win_amount:.2f} ETB!" if won else f"💥 Crashed at {crash_point:.2f}x!"

    return {
        "success": True,
        "won": won,
        "crash_point": crash_point,
        "cashed_out_at": user_multiplier,
        "bet_amount": bet_amount,
        "win_amount": win_amount,
        "balance": round(float(user.balance), 2),
        "message": message,
    }
