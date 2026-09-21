import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User, WalletTransaction


router = APIRouter(
    prefix="/api/slots",
    tags=["Lucky Slots"]
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

class SpinRequest(BaseModel):
    telegram_id: str
    bet_amount: float = Field(gt=0)


# =========================================================
# SLOT CONFIGURATION
# =========================================================

SLOT_SYMBOLS = [
    "🍒",
    "🍋",
    "🔔",
    "⭐",
    "💎",
    "7️⃣",
]


# Triple-match payout multipliers
SLOT_PAYOUTS = {
    "🍒": 3,
    "🍋": 4,
    "🔔": 5,
    "⭐": 8,
    "💎": 12,
    "7️⃣": 20,
}


ALLOWED_BETS = {
    10.0,
    20.0,
    50.0,
}


# =========================================================
# SPIN
# =========================================================

@router.post("/spin")
def spin_slots(
    request: SpinRequest,
    db: Session = Depends(get_db)
):
    telegram_id = str(request.telegram_id).strip()
    bet_amount = round(float(request.bet_amount), 2)

    # -----------------------------------------------------
    # Validate bet
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Lock user row
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Check banned user
    # -----------------------------------------------------

    if getattr(user, "is_banned", 0):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is currently restricted."
        )

    # -----------------------------------------------------
    # Check balance
    # -----------------------------------------------------

    current_balance = round(float(user.balance or 0), 2)

    if current_balance < bet_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Insufficient balance! "
                f"Your balance is {current_balance:.2f} ETB."
            )
        )

    # -----------------------------------------------------
    # Generate slot result
    # -----------------------------------------------------

    symbols = [
        secrets.choice(SLOT_SYMBOLS),
        secrets.choice(SLOT_SYMBOLS),
        secrets.choice(SLOT_SYMBOLS),
    ]

    win_amount = 0.0
    multiplier = 0

    # Triple match
    if symbols[0] == symbols[1] == symbols[2]:
        winning_symbol = symbols[0]
        multiplier = SLOT_PAYOUTS[winning_symbol]
        win_amount = round(bet_amount * multiplier, 2)

    # -----------------------------------------------------
    # Atomic wallet calculation
    # -----------------------------------------------------

    balance_before = current_balance

    # First take the stake
    balance_after_stake = round(
        balance_before - bet_amount,
        2
    )

    # Then add winnings
    final_balance = round(
        balance_after_stake + win_amount,
        2
    )

    user.balance = final_balance

    reference = f"SLOTS-{uuid.uuid4().hex[:16]}"

    # -----------------------------------------------------
    # Stake transaction
    # -----------------------------------------------------

    stake_transaction = WalletTransaction(
        user_id=user.id,
        transaction_type="game_stake_slots",
        amount=-bet_amount,
        balance_after=balance_after_stake,
        game="slots",
        reference=reference,
        description="Lucky Slots stake"
    )

    db.add(stake_transaction)

    # -----------------------------------------------------
    # Win transaction
    # -----------------------------------------------------

    if win_amount > 0:
        win_transaction = WalletTransaction(
            user_id=user.id,
            transaction_type="game_win_slots",
            amount=win_amount,
            balance_after=final_balance,
            game="slots",
            reference=reference,
            description=f"Lucky Slots win - {multiplier}x"
        )

        db.add(win_transaction)

    # -----------------------------------------------------
    # ONE COMMIT
    # -----------------------------------------------------

    try:
        db.commit()
        db.refresh(user)

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Spin could not be completed. Please try again."
        )

    # -----------------------------------------------------
    # Result message
    # -----------------------------------------------------

    if win_amount > 0:
        message = (
            f"🎉 Congratulations! "
            f"You won {win_amount:.2f} ETB ({multiplier}x)"
        )
    else:
        message = "Try again! Better luck next spin 🎰"

    return {
        "success": True,
        "symbols": symbols,
        "bet_amount": bet_amount,
        "win_amount": win_amount,
        "multiplier": multiplier,
        "balance": round(float(user.balance), 2),
        "message": message,
    }
