from sqlalchemy.orm import Session

from app.models import User, WalletTransaction


# =========================================================
# QUICK_BIRR GAMES
# SHARED WALLET SERVICE
# =========================================================


class WalletError(Exception):
    """Base wallet error."""


class UserNotFoundError(WalletError):
    pass


class InsufficientBalanceError(WalletError):
    pass


def get_user_by_telegram_id(
    db: Session,
    telegram_id: str
) -> User:
    user = (
        db.query(User)
        .filter(User.telegram_id == telegram_id)
        .first()
    )

    if not user:
        raise UserNotFoundError(
            "User not found."
        )

    return user


# =========================================================
# GET BALANCE
# =========================================================

def get_balance(
    db: Session,
    telegram_id: str
) -> float:

    user = get_user_by_telegram_id(
        db,
        telegram_id
    )

    return round(user.balance, 2)


# =========================================================
# ADD MONEY
# =========================================================

def credit_wallet(
    db: Session,
    telegram_id: str,
    amount: float,
    transaction_type: str = "deposit",
    game: str | None = None,
    reference: str | None = None,
    description: str | None = None,
) -> User:

    if amount <= 0:
        raise WalletError(
            "Amount must be greater than zero."
        )

    user = get_user_by_telegram_id(
        db,
        telegram_id
    )

    user.balance = round(
        user.balance + amount,
        2
    )

    transaction = WalletTransaction(
        user_id=user.id,
        transaction_type=transaction_type,
        amount=amount,
        balance_after=user.balance,
        game=game,
        reference=reference,
        description=description,
    )

    db.add(transaction)
    db.commit()
    db.refresh(user)

    return user


# =========================================================
# REMOVE MONEY
# =========================================================

def debit_wallet(
    db: Session,
    telegram_id: str,
    amount: float,
    transaction_type: str = "game_bet",
    game: str | None = None,
    reference: str | None = None,
    description: str | None = None,
) -> User:

    if amount <= 0:
        raise WalletError(
            "Amount must be greater than zero."
        )

    user = get_user_by_telegram_id(
        db,
        telegram_id
    )

    if user.balance < amount:
        raise InsufficientBalanceError(
            "Insufficient balance."
        )

    user.balance = round(
        user.balance - amount,
        2
    )

    transaction = WalletTransaction(
        user_id=user.id,
        transaction_type=transaction_type,
        amount=-amount,
        balance_after=user.balance,
        game=game,
        reference=reference,
        description=description,
    )

    db.add(transaction)
    db.commit()
    db.refresh(user)

    return user


# =========================================================
# GAME BET
# =========================================================

def place_bet(
    db: Session,
    telegram_id: str,
    amount: float,
    game: str,
    reference: str | None = None,
) -> User:

    return debit_wallet(
        db=db,
        telegram_id=telegram_id,
        amount=amount,
        transaction_type="game_bet",
        game=game,
        reference=reference,
        description=f"{game} game bet",
    )


# =========================================================
# GAME WIN
# =========================================================

def add_game_win(
    db: Session,
    telegram_id: str,
    amount: float,
    game: str,
    reference: str | None = None,
) -> User:

    return credit_wallet(
        db=db,
        telegram_id=telegram_id,
        amount=amount,
        transaction_type="game_win",
        game=game,
        reference=reference,
        description=f"{game} game win",
    )


# =========================================================
# REFUND
# =========================================================

def refund_bet(
    db: Session,
    telegram_id: str,
    amount: float,
    game: str,
    reference: str | None = None,
) -> User:

    return credit_wallet(
        db=db,
        telegram_id=telegram_id,
        amount=amount,
        transaction_type="refund",
        game=game,
        reference=reference,
        description=f"{game} bet refund",
    )
