from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
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

    # =====================================================
    # SHARED WALLET BALANCE
    # =====================================================

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
    # Example: bingo, slots, roulette
    game = Column(
        String(50),
        nullable=True,
        index=True
    )

    # Optional reference
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
