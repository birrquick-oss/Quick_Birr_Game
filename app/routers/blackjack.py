# =========================================================
# 🃏 QUICK_BIRR GAMES - BLACKJACK
# Backend Blackjack Game
# =========================================================

import json
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, BlackjackGame
from app.wallet import (
    get_user_by_telegram_id,
    process_game_stake,
    process_game_win,
)


router = APIRouter(
    prefix="/api/blackjack",
    tags=["Blackjack"]
)


# =========================================================
# SETTINGS
# =========================================================

ALLOWED_BETS = [10.0, 20.0, 50.0]


# =========================================================
# CARD DECK
# =========================================================

SUITS = ["♠", "♥", "♦", "♣"]

RANKS = [
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "J",
    "Q",
    "K",
    "A"
]


def create_deck():
    deck = []

    for suit in SUITS:
        for rank in RANKS:
            deck.append({
                "rank": rank,
                "suit": suit
            })

    secrets.SystemRandom().shuffle(deck)

    return deck


# =========================================================
# CARD VALUE
# =========================================================

def calculate_hand_value(cards):

    total = 0
    aces = 0

    for card in cards:

        rank = card["rank"]

        if rank in ["J", "Q", "K"]:
            total += 10

        elif rank == "A":
            total += 11
            aces += 1

        else:
            total += int(rank)

    while total > 21 and aces > 0:
        total -= 10
        aces -= 1

    return total


def is_blackjack(cards):
    return (
        len(cards) == 2
        and calculate_hand_value(cards) == 21
    )


# =========================================================
# HELPERS
# =========================================================

def draw_card(deck):
    if not deck:
        raise HTTPException(
            status_code=500,
            detail="Deck is empty."
        )

    return deck.pop()


def serialize_cards(cards):
    return json.dumps(cards)


def deserialize_cards(value):
    try:
        return json.loads(value)
    except Exception:
        return []


def serialize_deck(deck):
    return json.dumps(deck)


def deserialize_deck(value):
    try:
        return json.loads(value)
    except Exception:
        return []


def get_active_game(db, user_id):
    return (
        db.query(BlackjackGame)
        .filter(
            BlackjackGame.user_id == user_id,
            BlackjackGame.status == "playing"
        )
        .order_by(BlackjackGame.id.desc())
        .first()
    )


def game_response(game, user, message=None):

    player_cards = deserialize_cards(
        game.player_cards
    )

    dealer_cards = deserialize_cards(
        game.dealer_cards
    )

    return {
        "success": True,
        "game_id": game.id,
        "bet_amount": game.bet_amount,

        "player_cards": player_cards,
        "dealer_cards": dealer_cards,

        "player_value":
            calculate_hand_value(player_cards),

        "dealer_value":
            calculate_hand_value(dealer_cards),

        "status": game.status,
        "result": game.result,

        "payout": game.payout,

        "balance":
            round(float(user.balance), 2),

        "message":
            message or "Blackjack game"
    }


# =========================================================
# REQUEST MODELS
# =========================================================

class BlackjackStartRequest(BaseModel):
    telegram_id: str
    bet_amount: float


class BlackjackActionRequest(BaseModel):
    telegram_id: str


# =========================================================
# START GAME
# =========================================================

@router.post("/start")
def start_blackjack(
    request: BlackjackStartRequest,
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # Validate bet
    # -----------------------------------------------------

    bet = float(request.bet_amount)

    if bet not in ALLOWED_BETS:
        raise HTTPException(
            status_code=400,
            detail="Allowed bets are 10, 20 and 50 ETB."
        )

    # -----------------------------------------------------
    # Find user
    # -----------------------------------------------------

    user = get_user_by_telegram_id(
        db,
        str(request.telegram_id)
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found."
        )

    # -----------------------------------------------------
    # Check active game
    # -----------------------------------------------------

    active_game = get_active_game(
        db,
        user.id
    )

    if active_game:

        return game_response(
            active_game,
            user,
            "You already have an active Blackjack game."
        )

    # -----------------------------------------------------
    # Check balance
    # -----------------------------------------------------

    if user.balance < bet:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Insufficient balance! "
                f"Your balance is "
                f"{user.balance:.2f} ETB."
            )
        )

    # -----------------------------------------------------
    # Deduct stake
    # -----------------------------------------------------

    user = process_game_stake(
        db,
        user.id,
        bet,
        "Blackjack"
    )

    # -----------------------------------------------------
    # Create deck
    # -----------------------------------------------------

    deck = create_deck()

    # -----------------------------------------------------
    # Initial deal
    # -----------------------------------------------------

    player_cards = [
        draw_card(deck),
        draw_card(deck)
    ]

    dealer_cards = [
        draw_card(deck),
        draw_card(deck)
    ]

    # -----------------------------------------------------
    # Create game
    # -----------------------------------------------------

    game = BlackjackGame(
        user_id=user.id,
        bet_amount=bet,

        player_cards=
            serialize_cards(player_cards),

        dealer_cards=
            serialize_cards(dealer_cards),

        deck=
            serialize_deck(deck),

        status="playing",
        result=None,
        payout=0.0,

        balance_after=
            float(user.balance),

        reference=
            f"BJ-{int(datetime.now(timezone.utc).timestamp())}-{user.id}"
    )

    db.add(game)
    db.commit()
    db.refresh(game)

    # -----------------------------------------------------
    # NATURAL BLACKJACK
    # -----------------------------------------------------

    player_blackjack = is_blackjack(
        player_cards
    )

    dealer_blackjack = is_blackjack(
        dealer_cards
    )

    if player_blackjack or dealer_blackjack:

        # Both blackjack = PUSH
        if player_blackjack and dealer_blackjack:

            payout = bet
            result = "push"
            message = "🤝 Both have Blackjack — Push!"

        # Player blackjack
        elif player_blackjack:

            payout = bet * 2.5
            result = "blackjack"
            message = (
                f"🎉 BLACKJACK! "
                f"You won {payout:.2f} ETB!"
            )

        # Dealer blackjack
        else:

            payout = 0.0
            result = "dealer_blackjack"
            message = (
                "😔 Dealer has Blackjack."
            )

        # -------------------------------------------------
        # Add payout
        # -------------------------------------------------

        if payout > 0:

            user = process_game_win(
                db,
                user.id,
                payout,
                "Blackjack"
            )

        else:

            user = (
                db.query(User)
                .filter(User.id == user.id)
                .first()
            )

        game.status = "finished"
        game.result = result
        game.payout = payout
        game.balance_after = float(
            user.balance
        )
        game.completed_at = datetime.now(
            timezone.utc
        )

        db.commit()

        return game_response(
            game,
            user,
            message
        )

    # -----------------------------------------------------
    # NORMAL GAME
    # -----------------------------------------------------

    db.refresh(user)

    return game_response(
        game,
        user,
        "🃏 Your cards are ready. Hit or Stand?"
    )


# =========================================================
# HIT
# =========================================================

@router.post("/hit")
def blackjack_hit(
    request: BlackjackActionRequest,
    db: Session = Depends(get_db)
):

    user = get_user_by_telegram_id(
        db,
        str(request.telegram_id)
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found."
        )

    game = get_active_game(
        db,
        user.id
    )

    if not game:
        raise HTTPException(
            status_code=400,
            detail="No active Blackjack game."
        )

    # -----------------------------------------------------
    # Load game
    # -----------------------------------------------------

    player_cards = deserialize_cards(
        game.player_cards
    )

    dealer_cards = deserialize_cards(
        game.dealer_cards
    )

    deck = deserialize_deck(
        game.deck
    )

    # -----------------------------------------------------
    # Draw card
    # -----------------------------------------------------

    player_cards.append(
        draw_card(deck)
    )

    player_value = calculate_hand_value(
        player_cards
    )

    # -----------------------------------------------------
    # Save cards
    # -----------------------------------------------------

    game.player_cards = serialize_cards(
        player_cards
    )

    game.deck = serialize_deck(
        deck
    )

    # -----------------------------------------------------
    # PLAYER BUST
    # -----------------------------------------------------

    if player_value > 21:

        game.status = "finished"
        game.result = "bust"
        game.payout = 0.0
        game.balance_after = float(
            user.balance
        )
        game.completed_at = datetime.now(
            timezone.utc
        )

        db.commit()

        return game_response(
            game,
            user,
            f"💥 Bust! Your hand is {player_value}."
        )

    # -----------------------------------------------------
    # PLAYER 21
    # -----------------------------------------------------

    if player_value == 21:

        # Automatically stand
        while calculate_hand_value(
            dealer_cards
        ) < 17:

            dealer_cards.append(
                draw_card(deck)
            )

        dealer_value = calculate_hand_value(
            dealer_cards
        )

        game.dealer_cards = serialize_cards(
            dealer_cards
        )

        game.deck = serialize_deck(
            deck
        )

        if dealer_value > 21:
            result = "win"
            payout = game.bet_amount * 2
            message = (
                f"🎉 Dealer busts! "
                f"You won {payout:.2f} ETB!"
            )

        elif player_value > dealer_value:
            result = "win"
            payout = game.bet_amount * 2
            message = (
                f"🎉 You won {payout:.2f} ETB!"
            )

        elif player_value < dealer_value:
            result = "lose"
            payout = 0.0
            message = "😔 Dealer wins."

        else:
            result = "push"
            payout = game.bet_amount
            message = "🤝 Push — your bet is returned."

        if payout > 0:

            user = process_game_win(
                db,
                user.id,
                payout,
                "Blackjack"
            )

        game.status = "finished"
        game.result = result
        game.payout = payout
        game.balance_after = float(
            user.balance
        )
        game.completed_at = datetime.now(
            timezone.utc
        )

        db.commit()

        return game_response(
            game,
            user,
            message
        )

    # -----------------------------------------------------
    # GAME CONTINUES
    # -----------------------------------------------------

    db.commit()

    return game_response(
        game,
        user,
        f"🃏 You drew a card. Total: {player_value}. Hit or Stand?"
    )


# =========================================================
# STAND
# =========================================================

@router.post("/stand")
def blackjack_stand(
    request: BlackjackActionRequest,
    db: Session = Depends(get_db)
):

    user = get_user_by_telegram_id(
        db,
        str(request.telegram_id)
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found."
        )

    game = get_active_game(
        db,
        user.id
    )

    if not game:
        raise HTTPException(
            status_code=400,
            detail="No active Blackjack game."
        )

    player_cards = deserialize_cards(
        game.player_cards
    )

    dealer_cards = deserialize_cards(
        game.dealer_cards
    )

    deck = deserialize_deck(
        game.deck
    )

    player_value = calculate_hand_value(
        player_cards
    )

    # -----------------------------------------------------
    # Dealer draws until 17+
    # -----------------------------------------------------

    while calculate_hand_value(
        dealer_cards
    ) < 17:

        dealer_cards.append(
            draw_card(deck)
        )

    dealer_value = calculate_hand_value(
        dealer_cards
    )

    # -----------------------------------------------------
    # Determine result
    # -----------------------------------------------------

    if dealer_value > 21:

        result = "win"
        payout = game.bet_amount * 2

        message = (
            f"🎉 Dealer busts! "
            f"You won {payout:.2f} ETB!"
        )

    elif player_value > dealer_value:

        result = "win"
        payout = game.bet_amount * 2

        message = (
            f"🎉 You won {payout:.2f} ETB!"
        )

    elif player_value < dealer_value:

        result = "lose"
        payout = 0.0

        message = "😔 Dealer wins."

    else:

        result = "push"
        payout = game.bet_amount

        message = (
            "🤝 Push — your bet is returned."
        )

    # -----------------------------------------------------
    # Add winnings
    # -----------------------------------------------------

    if payout > 0:

        user = process_game_win(
            db,
            user.id,
            payout,
            "Blackjack"
        )

    # -----------------------------------------------------
    # Save game
    # -----------------------------------------------------

    game.dealer_cards = serialize_cards(
        dealer_cards
    )

    game.deck = serialize_deck(
        deck
    )

    game.status = "finished"
    game.result = result
    game.payout = payout
    game.balance_after = float(
        user.balance
    )

    game.completed_at = datetime.now(
        timezone.utc
    )

    db.commit()

    return game_response(
        game,
        user,
        message
    )
