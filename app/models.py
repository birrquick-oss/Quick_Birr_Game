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
    UniqueConstraint
)
from sqlalchemy.orm import relationship

# 🆕 Base እዚህ ጋር Import ተደርጓል
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

    phone_number = Column(
        String(50),
        nullable=True
    )

    referred_by = Column(
        String(64),
        nullable=True
    )

    # SHARED WALLET BALANCE
    balance = Column(
        Float,
        default=0.0,
        nullable=False
    )

    # የቻናል ቦነስ መውሰዱን መከታተያ
    has_claimed_channel_bonus = Column(
        Boolean,
        default=False,
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
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationship with Bets
    bets = relationship("Bet", back_populates="user")


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

    transaction_type = Column(
        String(50),
        nullable=False,
        index=True
    )

    amount = Column(
        Float,
        nullable=False
    )

    balance_after = Column(
        Float,
        nullable=False
    )

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
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

# =========================================================
# 🎁 BONUS CAMPAIGN
# =========================================================

class BonusCampaign(Base):
    __tablename__ = "bonus_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    max_claims = Column(Integer, nullable=False)
    claimed_count = Column(Integer, default=0, nullable=False)

    # 🛠️ እዚህ ጋር DateTime(timezone=True) ተደርጓል
    start_at = Column(DateTime(timezone=True), nullable=False, index=True)
    end_at = Column(DateTime(timezone=True), nullable=False, index=True)

    status = Column(
        String(30),
        default="scheduled",
        nullable=False,
        index=True
    )

    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    created_by = Column(String(64), nullable=True)
    broadcast_sent = Column(Boolean, default=False, nullable=False)

    # 🛠️ እዚህም ጋር DateTime(timezone=True) ተደርጓል
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

# =========================================================
# 🎁 BONUS CLAIM
# =========================================================

class BonusClaim(Base):
    __tablename__ = "bonus_claims"

    __table_args__ = (
        UniqueConstraint(
            "campaign_id",
            "user_id",
            name="uq_bonus_campaign_user"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    campaign_id = Column(
        Integer,
        ForeignKey("bonus_campaigns.id"),
        nullable=False,
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
        nullable=False,
        index=True
    )

    amount = Column(Float, nullable=False)

    balance_after = Column(Float, nullable=False)

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
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

    bank_name = Column(
        String(100),
        nullable=True
    )

    method = Column(
        String(100),
        default="Bank Transfer",
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
        default=lambda: datetime.now(timezone.utc),
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

    bank_name = Column(
        String(100),
        nullable=True
    )

    method = Column(
        String(100),
        default="Bank Transfer",
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
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )


# =========================================================
# BINGO GAME MODELS
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


# =========================================================
# ROULETTE GAME
# =========================================================

class RouletteSpin(Base):
    __tablename__ = "roulette_spins"

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

    bet_amount = Column(
        Float,
        nullable=False
    )

    bet_type = Column(
        String(50),
        nullable=False,
        index=True
    )

    bet_value = Column(
        Integer,
        nullable=True
    )

    winning_number = Column(
        Integer,
        nullable=False
    )

    winning_color = Column(
        String(20),
        nullable=False
    )

    multiplier = Column(
        Float,
        default=0.0,
        nullable=False
    )

    payout = Column(
        Float,
        default=0.0,
        nullable=False
    )

    balance_after = Column(
        Float,
        nullable=False
    )

    reference = Column(
        String(255),
        nullable=True,
        index=True
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )


# =========================================================
# BLACKJACK GAME
# =========================================================

class BlackjackGame(Base):
    __tablename__ = "blackjack_games"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    bet_amount = Column(
        Float,
        nullable=False
    )

    player_cards = Column(
        Text,
        nullable=False
    )

    dealer_cards = Column(
        Text,
        nullable=False
    )

    deck = Column(
        Text,
        nullable=False
    )

    status = Column(
        String(20),
        default="playing",
        nullable=False,
        index=True
    )

    result = Column(
        String(30),
        nullable=True
    )

    payout = Column(
        Float,
        default=0.0,
        nullable=False
    )

    balance_after = Column(
        Float,
        nullable=False
    )

    reference = Column(
        String(255),
        nullable=True,
        index=True
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    completed_at = Column(
        DateTime,
        nullable=True
    )


# =========================================================
# MINES GAME
# =========================================================

class MinesGame(Base):
    __tablename__ = "mines_games"

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

    bet_amount = Column(
        Float,
        nullable=False
    )

    mines_count = Column(
        Integer,
        nullable=False
    )

    mine_positions = Column(
        Text,
        nullable=False
    )

    revealed_tiles = Column(
        Text,
        nullable=False,
        default="[]"
    )

    multiplier = Column(
        Float,
        nullable=False,
        default=1.0
    )

    status = Column(
        String(20),
        nullable=False,
        default="playing",
        index=True
    )

    result = Column(
        String(30),
        nullable=True
    )

    payout = Column(
        Float,
        nullable=False,
        default=0.0
    )

    balance_after = Column(
        Float,
        nullable=False
    )

    reference = Column(
        String(255),
        nullable=True,
        index=True
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    completed_at = Column(
        DateTime,
        nullable=True
    )


# =========================================================
# DAILY CASHBACK
# =========================================================

class DailyCashback(Base):
    __tablename__ = "daily_cashbacks"

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

    cashback_date = Column(
        String(20),
        nullable=False,
        index=True
    )

    deposit_amount = Column(
        Float,
        default=0.0,
        nullable=False
    )

    cashback_amount = Column(
        Float,
        default=0.0,
        nullable=False
    )

    status = Column(
        String(20),
        default="pending",
        nullable=False,
        index=True
    )

    balance_after = Column(
        Float,
        default=0.0,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    claimed_at = Column(
        DateTime,
        nullable=True
    )


# =========================================================
# SPORTS BETTING MODELS
# =========================================================

class Match(Base):
    __tablename__ = "matches"

    id = Column(
        String(255),
        primary_key=True,
        index=True
    )

    sport_key = Column(
        String(100),
        nullable=False,
        index=True
    )

    league_name = Column(
        String(255),
        nullable=False
    )

    home_team = Column(
        String(255),
        nullable=False
    )

    away_team = Column(
        String(255),
        nullable=False
    )

    commence_time = Column(
        DateTime,
        nullable=True
    )

    home_odds = Column(
        Float,
        default=1.0,
        nullable=False
    )

    draw_odds = Column(
        Float,
        default=1.0,
        nullable=False
    )

    away_odds = Column(
        Float,
        default=1.0,
        nullable=False
    )

    status = Column(
        String(50),
        default="upcoming",
        nullable=False,
        index=True
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationship with Bets
    bets = relationship("Bet", back_populates="match")


class Bet(Base):
    __tablename__ = "bets"

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

    match_id = Column(
        String(255),
        ForeignKey("matches.id"),
        nullable=False,
        index=True
    )

    selection = Column(
        String(20),
        nullable=False
    )

    odds = Column(
        Float,
        nullable=False
    )

    stake = Column(
        Float,
        nullable=False
    )

    potential_payout = Column(
        Float,
        nullable=False
    )

    status = Column(
        String(20),
        default="pending",
        nullable=False,
        index=True
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    # Relationships
    user = relationship("User", back_populates="bets")
    match = relationship("Match", back_populates="bets")
