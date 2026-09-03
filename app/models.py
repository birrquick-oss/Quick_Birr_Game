from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
)

from app.database import Base


# =========================================================
# USER
# =========================================================

class User(Base):
    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    telegram_id = Column(
        String(64),
        unique=True,
        index=True,
        nullable=False
    )

    telegram_username = Column(
        String(255),
        nullable=True
    )

    first_name = Column(
        String(255),
        nullable=True
    )

    # SHARED WALLET BALANCE
    balance = Column(
        Float,
        default=0.0,
        nullable=False
    )

    # Account status
    is_banned = Column(
        Integer,
        default=0,
        nullable=False
    )

    is_bot = Column(
        Boolean,
        default=False,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )


# =========================================================
# WALLET TRANSACTION
# =========================================================

class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    # deposit / withdrawal / game_bet / game_win / refund
    transaction_type = Column(
        String(50),
        nullable=False,
        index=True
    )

    # Positive or negative amount
    amount = Column(
        Float,
        nullable=False
    )

    # Balance after this transaction
    balance_after = Column(
        Float,
        nullable=False
    )

    # Which game caused the transaction
    game = Column(
        String(50),
        nullable=True,
        index=True
    )

    reference = Column(
        String(255),
        nullable=True,
        index=True
    )

    description = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )


# =========================================================
# DEPOSIT REQUESTS
# =========================================================

class Deposit(Base):
    __tablename__ = "deposits"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    telegram_id = Column(
        String(64),
        nullable=True
    )

    telegram_name = Column(
        String(255),
        nullable=True
    )

    amount = Column(
        Float,
        nullable=False
    )

    method = Column(
        String(100),
        nullable=False
    )

    sms_text = Column(
        Text,
        nullable=False
    )

    status = Column(
        String(50),
        default="pending",
        nullable=False,
        index=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


# =========================================================
# WITHDRAWAL REQUESTS
# =========================================================

class Withdrawal(Base):
    __tablename__ = "withdrawals"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    amount = Column(
        Float,
        nullable=False
    )

    method = Column(
        String(100),
        nullable=False
    )

    account_number = Column(
        String(255),
        nullable=False
    )

    status = Column(
        String(50),
        default="pending",
        nullable=False,
        index=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


# =========================================================
# BINGO GAME MODELS (ADDED FOR BINGO ENGINE)
# =========================================================

class Game(Base):
    __tablename__ = "games"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    status = Column(
        String(50),
        default="waiting",
        nullable=False,
        index=True
    )

    started_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    finished_at = Column(
        DateTime,
        nullable=True
    )

    taken_cards = Column(
        Text,
        default="[]"
    )

    drawn_balls = Column(
        Text,
        default="[]"
    )

    winning_card = Column(
        String(255),
        nullable=True
    )

    winner_id = Column(
        Integer,
        nullable=True
    )

    prize = Column(
        Float,
        default=0.0
    )

    winners_info = Column(
        Text,
        default="[]"
    )


class Setting(Base):
    __tablename__ = "settings"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    draw_interval = Column(
        Float,
        default=4.0
    )

    game_commission_percent = Column(
        Float,
        default=20.0
    )

    house_win_ratio = Column(
        Integer,
        default=3
    )


class AdminStats(Base):
    __tablename__ = "admin_stats"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    house_balance = Column(
        Float,
        default=0.0
    )

    total_commission = Column(
        Float,
        default=0.0
    )


class Card(Base):
    __tablename__ = "cards"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    card_number = Column(
        Integer,
        unique=True,
        index=True,
        nullable=False
    )

    data = Column(
        Text,
        nullable=False
    )

    is_taken = Column(
        Boolean,
        default=False
    )

    reserved_by = Column(
        Integer,
        nullable=True
    )

    current_game_id = Column(
        Integer,
        nullable=True
    )


class PlayerCard(Base):
    __tablename__ = "player_cards"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    game_id = Column(
        Integer,
        ForeignKey("games.id"),
        nullable=False,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    card_number = Column(
        Integer,
        nullable=False
    )

    bet_amount = Column(
        Float,
        default=10.0,
        nullable=False
    )
