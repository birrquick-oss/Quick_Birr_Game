import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User, WalletTransaction, RouletteSpin


router = APIRouter(
    prefix="/api/roulette",
    tags=["European Roulette"]
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

class RouletteSpinRequest(BaseModel):

    telegram_id: str

    bet_amount: float = Field(
        gt=0
    )

    bet_type: str

    bet_value: int | None = None


# =========================================================
# ROULETTE CONSTANTS
# =========================================================

ALLOWED_BETS = {
    10.0,
    20.0,
    50.0
}


RED_NUMBERS = {
    1, 3, 5, 7, 9,
    12, 14, 16, 18,
    19, 21, 23, 25,
    27, 30, 32, 34, 36
}


BLACK_NUMBERS = {
    2, 4, 6, 8, 10,
    11, 13, 15, 17,
    20, 22, 24, 26,
    28, 29, 31, 33, 35
}


# =========================================================
# HELPERS
# =========================================================

def get_roulette_color(number: int) -> str:

    if number == 0:
        return "green"

    if number in RED_NUMBERS:
        return "red"

    return "black"


# =========================================================
# SPIN
# =========================================================

@router.post("/spin")
def spin_roulette(
    request: RouletteSpinRequest,
    db: Session = Depends(get_db)
):

    telegram_id = str(
        request.telegram_id
    ).strip()

    bet_amount = round(
        float(request.bet_amount),
        2
    )

    bet_type = str(
        request.bet_type
    ).strip().lower()

    bet_value = request.bet_value


    # -----------------------------------------------------
    # VALIDATE TELEGRAM ID
    # -----------------------------------------------------

    if not telegram_id:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram ID is required."
        )


    # -----------------------------------------------------
    # VALIDATE BET
    # -----------------------------------------------------

    if bet_amount not in ALLOWED_BETS:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid bet amount. Choose 10, 20 or 50 ETB."
        )


    # -----------------------------------------------------
    # VALIDATE BET TYPE
    # -----------------------------------------------------

    allowed_bet_types = {
        "red",
        "black",
        "green",
        "number"
    }

    if bet_type not in allowed_bet_types:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid roulette bet type."
        )


    # -----------------------------------------------------
    # VALIDATE NUMBER BET
    # -----------------------------------------------------

    if bet_type == "number":

        if bet_value is None:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please select a roulette number."
            )

        if not 0 <= int(bet_value) <= 36:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Roulette number must be between 0 and 36."
            )

        bet_value = int(bet_value)

    else:

        bet_value = None


    # -----------------------------------------------------
    # FIND USER
    # -----------------------------------------------------

    user = (
        db.query(User)
        .filter(
            User.telegram_id == telegram_id
        )
        .with_for_update()
        .first()
    )


    if not user:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )


    # -----------------------------------------------------
    # CHECK BAN
    # -----------------------------------------------------

    if getattr(
        user,
        "is_banned",
        0
    ):

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is currently restricted."
        )


    # -----------------------------------------------------
    # CHECK BALANCE
    # -----------------------------------------------------

    current_balance = round(
        float(user.balance or 0),
        2
    )


    if current_balance < bet_amount:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Insufficient balance! "
                f"Your balance is "
                f"{current_balance:.2f} ETB."
            )
        )


    # =====================================================
    # GENERATE ROULETTE RESULT
    # =====================================================

    winning_number = secrets.randbelow(37)

    winning_color = get_roulette_color(
        winning_number
    )


    # =====================================================
    # DETERMINE PAYOUT
    # =====================================================

    multiplier = 0.0


    # NUMBER BET
    if bet_type == "number":

        if bet_value == winning_number:

            multiplier = 35.0


    # RED BET
    elif bet_type == "red":

        if winning_color == "red":

            multiplier = 2.0


    # BLACK BET
    elif bet_type == "black":

        if winning_color == "black":

            multiplier = 2.0


    # GREEN / ZERO BET
    elif bet_type == "green":

        if winning_number == 0:

            multiplier = 35.0


    # =====================================================
    # CALCULATE PAYOUT
    # =====================================================

    payout = round(
        bet_amount * multiplier,
        2
    )


    balance_before = current_balance

    balance_after_stake = round(
        balance_before - bet_amount,
        2
    )

    final_balance = round(
        balance_after_stake + payout,
        2
    )


    # =====================================================
    # UPDATE USER BALANCE
    # =====================================================

    user.balance = final_balance


    reference = (
        f"ROULETTE-"
        f"{uuid.uuid4().hex[:16]}"
    )


    # =====================================================
    # WALLET STAKE TRANSACTION
    # =====================================================

    stake_transaction = WalletTransaction(

        user_id=user.id,

        transaction_type=
        "game_stake_roulette",

        amount=-bet_amount,

        balance_after=
        balance_after_stake,

        game="roulette",

        reference=reference,

        description=
        "European Roulette stake"
    )


    db.add(
        stake_transaction
    )


    # =====================================================
    # WALLET WIN TRANSACTION
    # =====================================================

    if payout > 0:

        win_transaction = WalletTransaction(

            user_id=user.id,

            transaction_type=
            "game_win_roulette",

            amount=payout,

            balance_after=
            final_balance,

            game="roulette",

            reference=reference,

            description=
            f"European Roulette win - "
            f"{multiplier}x"
        )

        db.add(
            win_transaction
        )


    # =====================================================
    # SAVE SPIN HISTORY
    # =====================================================

    roulette_spin = RouletteSpin(

        user_id=user.id,

        bet_amount=bet_amount,

        bet_type=bet_type,

        bet_value=bet_value,

        winning_number=winning_number,

        winning_color=winning_color,

        multiplier=multiplier,

        payout=payout,

        balance_after=final_balance,

        reference=reference
    )


    db.add(
        roulette_spin
    )


    # =====================================================
    # COMMIT
    # =====================================================

    try:

        db.commit()

        db.refresh(user)

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=
            status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail=
            "Roulette spin could not be completed. "
            "Please try again."
        )


    # =====================================================
    # RESULT MESSAGE
    # =====================================================

    if payout > 0:

        if multiplier >= 35:

            message = (
                f"🎉 JACKPOT! "
                f"{winning_number} "
                f"won {payout:.2f} ETB!"
            )

        else:

            message = (
                f"🎉 You won "
                f"{payout:.2f} ETB!"
            )

    else:

        message = (
            f"🎡 {winning_number} "
            f"{winning_color.upper()} — "
            f"Better luck next spin!"
        )


    # =====================================================
    # RESPONSE
    # =====================================================

    return {

        "success": True,

        "winning_number":
        winning_number,

        "winning_color":
        winning_color,

        "bet_type":
        bet_type,

        "bet_value":
        bet_value,

        "bet_amount":
        bet_amount,

        "multiplier":
        multiplier,

        "payout":
        payout,

        "balance":
        round(
            float(user.balance),
            2
        ),

        "message":
        message
    }
