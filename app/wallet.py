from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models import User, WalletTransaction

# =========================================================
# CENTRAL SHARED WALLET SERVICES
# =========================================================

def get_user_by_telegram_id(db: Session, telegram_id: str) -> User:
    """ Helper function to fetch user by Telegram ID """
    tg_str = str(telegram_id).strip()
    return db.query(User).filter(User.telegram_id == tg_str).first()


def process_game_stake(db: Session, user_id: int, amount: float, game_name: str) -> User:
    """
    Deducts game stake from user's central balance.
    Throws HTTPException if balance is insufficient.
    """
    if amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stake amount must be greater than zero."
        )

    # 🔒 Race Condition ለመከላከል Row-level locking (with_for_update)
    user = db.query(User).filter(User.id == user_id).with_for_update().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    if user.balance < amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient balance! Your balance is {user.balance} ETB."
        )

    # Balance Deduction
    user.balance -= amount

    # Audit Transaction Log
    txn = WalletTransaction(
        user_id=user.id,
        amount=-amount,
        balance_after=user.balance,
        transaction_type=f"game_stake_{game_name.lower()}",
        description=f"Stake for {game_name}"
    )
    db.add(txn)
    db.commit()
    db.refresh(user)

    return user


def process_game_win(db: Session, user_id: int, amount: float, game_name: str) -> User:
    """
    Adds game winnings to user's central balance.
    """
    if amount <= 0:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )
        return user

    # 🔒 Row-level locking for secure update
    user = db.query(User).filter(User.id == user_id).with_for_update().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    # Add Winnings
    user.balance += amount

    # Audit Transaction Log
    txn = WalletTransaction(
        user_id=user.id,
        amount=amount,
        balance_after=user.balance,
        transaction_type=f"game_win_{game_name.lower()}",
        description=f"Winnings from {game_name}"
    )
    db.add(txn)
    db.commit()
    db.refresh(user)

    return user
