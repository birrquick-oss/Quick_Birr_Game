import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User, WalletTransaction


router = APIRouter(
    prefix="/api/chicken",
    tags=["Chicken Road"]
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
# REQUEST MODEL
# =========================================================

class PlayChickenRequest(BaseModel):
    telegram_id: str
    bet_amount: float = Field(gt=0)
    steps_cleared: int = Field(ge=1, le=5)


ALLOWED_BETS = {10.0, 20.0, 50.0, 100.0}

# Step multipliers (Step 1 to 5)
STEP_MULTIPLIERS = {
    1: 1.40,
    2: 1.80,
    3: 2.30,
    4: 3.00,
    5: 4.20
}


# =========================================================
# PLAY CHICKEN ROAD
# =========================================================

@router.post("/play")
def play_chicken(
    request: PlayChickenRequest,
    db: Session = Depends(get_db)
):
    telegram_id = str(request.telegram_id).strip()
    bet_amount = round(float(request.bet_amount), 2)
    steps = request.steps_cleared

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

    # Calculate success probability based on steps (Each step has 70% survival chance)
    survival_chance = 0.70 ** steps
    safe = secrets.SystemRandom().random() < survival_chance

    multiplier = STEP_MULTIPLIERS.get(steps, 1.0) if safe else 0.0
    win_amount = round(bet_amount * multiplier, 2) if safe else 0.0

    balance_before = current_balance
    balance_after_stake = round(balance_before - bet_amount, 2)
    final_balance = round(balance_after_stake + win_amount, 2)

    user.balance = final_balance
    reference = f"CHICKEN-{uuid.uuid4().hex[:16]}"

    # Stake transaction
    stake_transaction = WalletTransaction(
        user_id=user.id,
        transaction_type="game_stake_chicken",
        amount=-bet_amount,
        balance_after=balance_after_stake,
        game="chicken",
        reference=reference,
        description="Chicken Road game stake"
    )
    db.add(stake_transaction)

    # Win transaction
    if safe and win_amount > 0:
        win_transaction = WalletTransaction(
            user_id=user.id,
            transaction_type="game_win_chicken",
            amount=win_amount,
            balance_after=final_balance,
            game="chicken",
            reference=reference,
            description=f"Chicken Road win - Step {steps} ({multiplier}x)"
        )
        db.add(win_transaction)

    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chicken Road play could not be completed. Please try again."
        )

    message = f"🎉 Safe crossing! Won {win_amount:.2f} ETB ({multiplier}x)!" if safe else "💥 ROASTED! The chicken caught fire."

    return {
        "success": True,
        "safe": safe,
        "steps_cleared": steps,
        "bet_amount": bet_amount,
        "win_amount": win_amount,
        "multiplier": multiplier,
        "balance": round(float(user.balance), 2),
        "message": message,
    }
