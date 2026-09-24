import json
import secrets
import uuid

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    User,
    WalletTransaction,
    MinesGame,
)


router = APIRouter(
    prefix="/api/mines",
    tags=["Mines"]
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

class MinesStartRequest(BaseModel):

    telegram_id: str

    bet_amount: float = Field(
        gt=0
    )

    mine_count: int


class MinesRevealRequest(BaseModel):

    telegram_id: str

    game_id: int

    tile_index: int


class MinesCashoutRequest(BaseModel):

    telegram_id: str

    game_id: int


# =========================================================
# CONSTANTS
# =========================================================

ALLOWED_BETS = {
    10.0,
    20.0,
    50.0
}

ALLOWED_MINE_COUNTS = {
    3,
    5,
    10
}

TOTAL_TILES = 25


# =========================================================
# MULTIPLIER TABLE
# =========================================================
#
# Multiplier is applied after each SAFE tile.
#
# The values are intentionally stored server-side.
#
# Index:
# 0 = before first safe tile
# 1 = after first safe tile
# 2 = after second safe tile
# etc.
#
# Separate table for 3, 5 and 10 mines.
# =========================================================

MULTIPLIERS = {

    3: [
        1.00,
        1.15,
        1.35,
        1.60,
        1.95,
        2.40,
        3.00,
        3.80,
        4.80,
        6.20,
        8.20,
        11.00,
        15.00,
        21.00,
        30.00,
        45.00,
        70.00,
        120.00,
        220.00,
        500.00,
        1000.00,
        2000.00,
        5000.00
    ],

    5: [
        1.00,
        1.25,
        1.55,
        1.95,
        2.50,
        3.25,
        4.30,
        5.80,
        8.00,
        11.50,
        17.00,
        26.00,
        42.00,
        70.00,
        125.00,
        250.00,
        550.00,
        1500.00,
        5000.00,
        15000.00,
        50000.00
    ],

    10: [
        1.00,
        1.45,
        2.15,
        3.30,
        5.20,
        8.50,
        14.00,
        24.00,
        42.00,
        78.00,
        150.00,
        300.00,
        650.00,
        1500.00,
        4000.00,
        12000.00
    ]
}


# =========================================================
# HELPERS
# =========================================================

def get_multiplier(
    mine_count: int,
    safe_count: int
) -> float:

    table = MULTIPLIERS.get(
        mine_count
    )

    if not table:
        return 1.0

    if safe_count < 0:
        return 1.0

    if safe_count >= len(table):
        return float(table[-1])

    return float(
        table[safe_count]
    )


def make_reference() -> str:

    return (
        f"MINES-"
        f"{uuid.uuid4().hex[:16]}"
    )


def get_user(
    db: Session,
    telegram_id: str
):

    return (
        db.query(User)
        .filter(
            User.telegram_id == telegram_id
        )
        .with_for_update()
        .first()
    )


def get_active_game(
    db: Session,
    user_id: int
):

    return (
        db.query(MinesGame)
        .filter(
            MinesGame.user_id == user_id,
            MinesGame.status == "playing"
        )
        .order_by(
            MinesGame.id.desc()
        )
        .first()
    )


def load_json_list(
    value: str
):

    try:

        result = json.loads(
            value or "[]"
        )

        if isinstance(result, list):
            return result

    except Exception:
        pass

    return []


def save_json_list(
    value
):

    return json.dumps(
        value,
        separators=(",", ":")
    )


# =========================================================
# START GAME
# =========================================================

@router.post("/start")
def start_mines(
    request: MinesStartRequest,
    db: Session = Depends(get_db)
):

    telegram_id = str(
        request.telegram_id
    ).strip()

    bet_amount = round(
        float(request.bet_amount),
        2
    )

    mine_count = int(
        request.mine_count
    )


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
            detail=(
                "Invalid bet amount. "
                "Choose 10, 20 or 50 ETB."
            )
        )


    # -----------------------------------------------------
    # VALIDATE MINE COUNT
    # -----------------------------------------------------

    if mine_count not in ALLOWED_MINE_COUNTS:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid mine count. "
                "Choose 3, 5 or 10 mines."
            )
        )


    # -----------------------------------------------------
    # FIND USER
    # -----------------------------------------------------

    user = get_user(
        db,
        telegram_id
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
            detail=(
                "Your account is currently restricted."
            )
        )


    # -----------------------------------------------------
    # CHECK ACTIVE GAME
    # -----------------------------------------------------

    active_game = get_active_game(
        db,
        user.id
    )


    if active_game:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "You already have an active "
                "Mines game."
            )
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
    # GENERATE MINE POSITIONS
    # =====================================================

    mine_positions = sorted(
        secrets.SystemRandom().sample(
            range(TOTAL_TILES),
            mine_count
        )
    )


    # =====================================================
    # CALCULATE BALANCE AFTER STAKE
    # =====================================================

    balance_before = current_balance

    balance_after_stake = round(
        balance_before - bet_amount,
        2
    )


    # =====================================================
    # UPDATE USER BALANCE
    # =====================================================

    user.balance = balance_after_stake


    reference = make_reference()


    # =====================================================
    # CREATE MINES GAME
    # =====================================================

    mines_game = MinesGame(

        user_id=user.id,

        bet_amount=bet_amount,

        mine_count=mine_count,

        mine_positions=save_json_list(
            mine_positions
        ),

        revealed_positions="[]",

        multiplier=1.0,

        status="playing",

        result=None,

        payout=0.0,

        balance_after=balance_after_stake,

        reference=reference
    )


    db.add(
        mines_game
    )


    # =====================================================
    # WALLET STAKE TRANSACTION
    # =====================================================

    stake_transaction = WalletTransaction(

        user_id=user.id,

        transaction_type=
        "game_stake_mines",

        amount=-bet_amount,

        balance_after=
        balance_after_stake,

        game="mines",

        reference=reference,

        description=
        "Mines game stake"
    )


    db.add(
        stake_transaction
    )


    # =====================================================
    # COMMIT
    # =====================================================

    try:

        db.commit()

        db.refresh(
            mines_game
        )

        db.refresh(
            user
        )

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=
            status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail=
            "Mines game could not be started. "
            "Please try again."
        )


    # =====================================================
    # RESPONSE
    # =====================================================

    return {

        "success": True,

        "game_id":
        mines_game.id,

        "bet_amount":
        bet_amount,

        "mine_count":
        mine_count,

        "multiplier":
        1.0,

        "balance":
        round(
            float(user.balance),
            2
        ),

        "status":
        "playing",

        "message":
        (
            f"💣 Mines started! "
            f"Find the safe tiles."
        )
    }


# =========================================================
# REVEAL TILE
# =========================================================

@router.post("/reveal")
def reveal_mines_tile(
    request: MinesRevealRequest,
    db: Session = Depends(get_db)
):

    telegram_id = str(
        request.telegram_id
    ).strip()

    game_id = int(
        request.game_id
    )

    tile_index = int(
        request.tile_index
    )


    # -----------------------------------------------------
    # VALIDATE TELEGRAM ID
    # -----------------------------------------------------

    if not telegram_id:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram ID is required."
        )


    # -----------------------------------------------------
    # VALIDATE TILE
    # -----------------------------------------------------

    if not 0 <= tile_index < TOTAL_TILES:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid tile. "
                "Tile must be between 0 and 24."
            )
        )


    # -----------------------------------------------------
    # FIND USER
    # -----------------------------------------------------

    user = get_user(
        db,
        telegram_id
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
            detail=(
                "Your account is currently restricted."
            )
        )


    # -----------------------------------------------------
    # FIND GAME
    # -----------------------------------------------------

    game = (
        db.query(MinesGame)
        .filter(
            MinesGame.id == game_id,
            MinesGame.user_id == user.id
        )
        .with_for_update()
        .first()
    )


    if not game:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mines game not found."
        )


    # -----------------------------------------------------
    # CHECK GAME STATUS
    # -----------------------------------------------------

    if game.status != "playing":

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This Mines game is already finished."
        )


    # -----------------------------------------------------
    # LOAD POSITIONS
    # -----------------------------------------------------

    mine_positions = load_json_list(
        game.mine_positions
    )

    revealed_positions = load_json_list(
        game.revealed_positions
    )


    # -----------------------------------------------------
    # PREVENT DOUBLE REVEAL
    # -----------------------------------------------------

    if tile_index in revealed_positions:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This tile has already been revealed."
        )


    # =====================================================
    # MINE HIT
    # =====================================================

    if tile_index in mine_positions:

        revealed_positions.append(
            tile_index
        )

        game.revealed_positions = save_json_list(
            revealed_positions
        )

        game.status = "finished"

        game.result = "mine"

        game.multiplier = 0.0

        game.payout = 0.0

        game.balance_after = round(
            float(user.balance or 0),
            2
        )

        game.completed_at = datetime.now(
            timezone.utc
        )


        try:

            db.commit()

            db.refresh(
                user
            )

        except Exception:

            db.rollback()

            raise HTTPException(
                status_code=
                status.HTTP_500_INTERNAL_SERVER_ERROR,

                detail=
                "Mines result could not be saved."
            )


        # -------------------------------------------------
        # RESPONSE
        # -------------------------------------------------

        return {

            "success": True,

            "game_id":
            game.id,

            "is_mine":
            True,

            "tile_index":
            tile_index,

            "multiplier":
            0.0,

            "payout":
            0.0,

            "balance":
            round(
                float(user.balance),
                2
            ),

            "status":
            "finished",

            "result":
            "mine",

            "mine_positions":
            mine_positions,

            "message":
            "💣 BOOM! You hit a mine!"
        }


    # =====================================================
    # SAFE TILE
    # =====================================================

    revealed_positions.append(
        tile_index
    )

    game.revealed_positions = save_json_list(
        revealed_positions
    )


    safe_count = len(
        [
            position
            for position in revealed_positions
            if position not in mine_positions
        ]
    )


    # =====================================================
    # CALCULATE MULTIPLIER
    # =====================================================

    multiplier = get_multiplier(
        game.mine_count,
        safe_count
    )


    game.multiplier = round(
        multiplier,
        2
    )


    game.balance_after = round(
        float(user.balance or 0),
        2
    )


    # =====================================================
    # CHECK BOARD COMPLETION
    # =====================================================

    safe_tiles_total = (
        TOTAL_TILES -
        game.mine_count
    )


    if safe_count >= safe_tiles_total:

        payout = round(
            game.bet_amount *
            game.multiplier,
            2
        )


        current_balance = round(
            float(user.balance or 0),
            2
        )


        final_balance = round(
            current_balance + payout,
            2
        )


        user.balance = final_balance

        game.status = "finished"

        game.result = "win"

        game.payout = payout

        game.balance_after = final_balance

        game.completed_at = datetime.now(
            timezone.utc
        )


        win_transaction = WalletTransaction(

            user_id=user.id,

            transaction_type=
            "game_win_mines",

            amount=payout,

            balance_after=
            final_balance,

            game="mines",

            reference=game.reference,

            description=
            (
                f"Mines automatic win - "
                f"{game.multiplier}x"
            )
        )


        db.add(
            win_transaction
        )


        try:

            db.commit()

            db.refresh(
                user
            )

        except Exception:

            db.rollback()

            raise HTTPException(
                status_code=
                status.HTTP_500_INTERNAL_SERVER_ERROR,

                detail=
                "Mines winnings could not be completed."
            )


        return {

            "success": True,

            "game_id":
            game.id,

            "is_mine":
            False,

            "tile_index":
            tile_index,

            "multiplier":
            game.multiplier,

            "payout":
            payout,

            "balance":
            round(
                float(user.balance),
                2
            ),

            "status":
            "finished",

            "result":
            "win",

            "message":
            (
                f"🎉 You cleared the board! "
                f"You won {payout:.2f} ETB!"
            )
        }


    # =====================================================
    # SAVE SAFE TILE
    # =====================================================

    try:

        db.commit()

        db.refresh(
            user
        )

        db.refresh(
            game
        )

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=
            status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail=
            "Mines tile could not be saved."
        )


    # =====================================================
    # SAFE RESPONSE
    # =====================================================

    potential_payout = round(
        game.bet_amount *
        game.multiplier,
        2
    )


    return {

        "success": True,

        "game_id":
        game.id,

        "is_mine":
        False,

        "tile_index":
        tile_index,

        "multiplier":
        game.multiplier,

        "payout":
        potential_payout,

        "balance":
        round(
            float(user.balance),
            2
        ),

        "status":
        "playing",

        "result":
        None,

        "message":
        (
            f"💎 SAFE! "
            f"Multiplier is "
            f"{game.multiplier:.2f}x"
        )
    }


# =========================================================
# CASH OUT
# =========================================================

@router.post("/cashout")
def cashout_mines(
    request: MinesCashoutRequest,
    db: Session = Depends(get_db)
):

    telegram_id = str(
        request.telegram_id
    ).strip()

    game_id = int(
        request.game_id
    )


    # -----------------------------------------------------
    # VALIDATE TELEGRAM ID
    # -----------------------------------------------------

    if not telegram_id:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram ID is required."
        )


    # -----------------------------------------------------
    # FIND USER
    # -----------------------------------------------------

    user = get_user(
        db,
        telegram_id
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
            detail=(
                "Your account is currently restricted."
            )
        )


    # -----------------------------------------------------
    # FIND GAME
    # -----------------------------------------------------

    game = (
        db.query(MinesGame)
        .filter(
            MinesGame.id == game_id,
            MinesGame.user_id == user.id
        )
        .with_for_update()
        .first()
    )


    if not game:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mines game not found."
        )


    # -----------------------------------------------------
    # CHECK GAME STATUS
    # -----------------------------------------------------

    if game.status != "playing":

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This Mines game is already finished."
        )


    # -----------------------------------------------------
    # LOAD REVEALED POSITIONS
    # -----------------------------------------------------

    revealed_positions = load_json_list(
        game.revealed_positions
    )


    safe_count = len(
        revealed_positions
    )


    if safe_count <= 0:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Reveal at least one safe tile "
                "before cashing out."
            )
        )


    # =====================================================
    # CALCULATE PAYOUT
    # =====================================================

    multiplier = get_multiplier(
        game.mine_count,
        safe_count
    )


    game.multiplier = round(
        multiplier,
        2
    )


    payout = round(
        game.bet_amount *
        game.multiplier,
        2
    )


    # -----------------------------------------------------
    # CURRENT BALANCE
    # -----------------------------------------------------

    current_balance = round(
        float(user.balance or 0),
        2
    )


    # =====================================================
    # ADD WINNINGS
    # =====================================================

    final_balance = round(
        current_balance + payout,
        2
    )


    user.balance = final_balance


    # =====================================================
    # FINISH GAME
    # =====================================================

    game.status = "finished"

    game.result = "cashout"

    game.payout = payout

    game.balance_after = final_balance

    game.completed_at = datetime.now(
        timezone.utc
    )


    # =====================================================
    # WALLET WIN TRANSACTION
    # =====================================================

    win_transaction = WalletTransaction(

        user_id=user.id,

        transaction_type=
        "game_win_mines",

        amount=payout,

        balance_after=
        final_balance,

        game="mines",

        reference=game.reference,

        description=
        (
            f"Mines cash out - "
            f"{game.multiplier}x"
        )
    )


    db.add(
        win_transaction
    )


    # =====================================================
    # COMMIT
    # =====================================================

    try:

        db.commit()

        db.refresh(
            user
        )

        db.refresh(
            game
        )

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=
            status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail=
            "Mines cash out could not be completed. "
            "Please try again."
        )


    # =====================================================
    # RESPONSE
    # =====================================================

    return {

        "success": True,

        "game_id":
        game.id,

        "multiplier":
        game.multiplier,

        "payout":
        payout,

        "balance":
        round(
            float(user.balance),
            2
        ),

        "status":
        "finished",

        "result":
        "cashout",

        "message":
        (
            f"💰 CASH OUT! "
            f"You collected "
            f"{payout:.2f} ETB "
            f"at {game.multiplier:.2f}x!"
        )
    }
