import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User, WalletTransaction


router = APIRouter(
    prefix="/api/keno",
    tags=["Keno"]
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

class PlayKenoRequest(BaseModel):
    telegram_id: str
    bet_amount: float = Field(gt=0)
    selected_numbers: list[int] = Field(min_items=1, max_items=10)


ALLOWED_BETS = {10.0, 20.0, 50.0, 100.0}


# =========================================================
# PLAY KENO
# =========================================================

@router.post("/play")
def play_keno(
    request: PlayKenoRequest,
    db: Session = Depends(get_db)
):
    telegram_id = str(request.telegram_id).strip()
    bet_amount = round(float(request.bet_amount), 2)
    selected = request.selected_numbers

    # Validate numbers (1-80)
    if any(n < 1 or n > 80 for n in selected) or len(set(selected)) != len(selected):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid numbers. Select between 1 and 80 without duplicates."
        )

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

    # Draw 20 unique random numbers (1 to 80)
    all_numbers = list(range(1, 81))
    drawn_numbers = secrets.SystemRandom().sample(all_numbers, 20)

    # Calculate hits
    matched = set(selected).intersection(set(drawn_numbers))
    hits = len(matched)

    # Payout multiplier
    multiplier = round(hits * 0.7, 2) if hits > 0 else 0.0
    win_amount = round(bet_amount * multiplier, 2)

    balance_before = current_balance
    balance_after_stake = round(balance_before - bet_amount, 2)
    final_balance = round(balance_after_stake + win_amount, 2)

    user.balance = final_balance
    reference = f"KENO-{uuid.uuid4().hex[:16]}"

    # Stake transaction
    stake_transaction = WalletTransaction(
        user_id=user.id,
        transaction_type="game_stake_keno",
        amount=-bet_amount,
        balance_after=balance_after_stake,
        game="keno",
        reference=reference,
        description="Keno game stake"
    )
    db.add(stake_transaction)

    # Win transaction
    if win_amount > 0:
        win_transaction = WalletTransaction(
            user_id=user.id,
            transaction_type="game_win_keno",
            amount=win_amount,
            balance_after=final_balance,
            game="keno",
            reference=reference,
            description=f"Keno win - {hits} hits ({multiplier}x)"
        )
        db.add(win_transaction)

    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Keno play could not be completed. Please try again."
        )

    message = f"🎉 Matched {hits} numbers! Won {win_amount:.2f} ETB!" if win_amount > 0 else f"Matched {hits} numbers. Try again!"

    return {
        "success": True,
        "drawn_numbers": drawn_numbers,
        "matched_numbers": list(matched),
        "hits": hits,
        "bet_amount": bet_amount,
        "win_amount": win_amount,
        "multiplier": multiplier,
        "balance": round(float(user.balance), 2),
        "message": message,
    }
