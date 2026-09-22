import random
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User, WalletTransaction


router = APIRouter(
    prefix="/api/plinko",
    tags=["Plinko"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class PlinkoRequest(BaseModel):
    telegram_id: str
    bet_amount: float = Field(gt=0)


# Available bets
ALLOWED_BETS = {10.0, 20.0, 50.0}


# Multipliers from left → right
MULTIPLIERS = [
    0.0,
    0.5,
    1.0,
    2.0,
    5.0,
    10.0,
    5.0,
    2.0,
    1.0,
    0.5,
    0.0,
]


@router.post("/drop")
def drop_plinko(
    request: PlinkoRequest,
    db: Session = Depends(get_db)
):
    telegram_id = str(request.telegram_id).strip()
    bet_amount = round(float(request.bet_amount), 2)

    # Validate bet
    if bet_amount not in ALLOWED_BETS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid bet amount. Choose 10, 20 or 50 ETB."
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

    # Banned user
    if getattr(user, "is_banned", 0):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is currently restricted."
        )

    current_balance = round(
        float(user.balance or 0),
        2
    )

    # Insufficient balance
    if current_balance < bet_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Insufficient balance! "
                f"Your balance is {current_balance:.2f} ETB."
            )
        )

    # -------------------------------------------------
    # PLINKO RESULT
    # -------------------------------------------------

    # Random slot
    result_index = random.randrange(
        len(MULTIPLIERS)
    )

    multiplier = MULTIPLIERS[result_index]

    # Gross payout
    win_amount = round(
        bet_amount * multiplier,
        2
    )

    # Balance calculation
    balance_before = current_balance

    balance_after_stake = round(
        balance_before - bet_amount,
        2
    )

    final_balance = round(
        balance_after_stake + win_amount,
        2
    )

    # Update wallet
    user.balance = final_balance

    reference = (
        f"PLINKO-{uuid.uuid4().hex[:16]}"
    )

    # -------------------------------------------------
    # STAKE TRANSACTION
    # -------------------------------------------------

    stake_transaction = WalletTransaction(
        user_id=user.id,
        transaction_type="game_stake_plinko",
        amount=-bet_amount,
        balance_after=balance_after_stake,
        game="plinko",
        reference=reference,
        description="Plinko stake"
    )

    db.add(stake_transaction)

    # -------------------------------------------------
    # WIN TRANSACTION
    # -------------------------------------------------

    if win_amount > 0:

        win_transaction = WalletTransaction(
            user_id=user.id,
            transaction_type="game_win_plinko",
            amount=win_amount,
            balance_after=final_balance,
            game="plinko",
            reference=reference,
            description=(
                f"Plinko win - {multiplier}x"
            )
        )

        db.add(win_transaction)

    # -------------------------------------------------
    # COMMIT
    # -------------------------------------------------

    try:
        db.commit()
        db.refresh(user)

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Plinko game could not be completed. Please try again."
        )

    # -------------------------------------------------
    # RESPONSE
    # -------------------------------------------------

    if multiplier >= 1:
        message = (
            f"🎉 Congratulations! "
            f"You won {win_amount:.2f} ETB "
            f"({multiplier}x)"
        )

    elif multiplier > 0:
        message = (
            f"💰 You received "
            f"{win_amount:.2f} ETB "
            f"({multiplier}x)"
        )

    else:
        message = (
            "😢 No prize this time. "
            "Try again!"
        )

    return {
        "success": True,
        "bet_amount": bet_amount,
        "multiplier": multiplier,
        "result_index": result_index,
        "win_amount": win_amount,
        "balance": round(
            float(user.balance),
            2
        ),
        "message": message,
    }
