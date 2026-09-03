from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models import User, WalletTransaction

# =========================================================
# CENTRAL SHARED WALLET SERVICES
# =========================================================

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

    user = db.query(User).filter(User.id == user_id).first()
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
        return db.query(User).filter(User.id == user_id).first()

    user = db.query(User).filter(User.id == user_id).first()
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
        transaction_type=f"game_win_{game_name.lower()}",
        description=f"Winnings from {game_name}"
    )
    db.add(txn)
    db.commit()
    db.refresh(user)

    return user
