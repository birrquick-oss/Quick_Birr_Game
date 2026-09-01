from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# =========================================================
# USER
# =========================================================

class UserCreate(BaseModel):
    telegram_id: str = Field(..., min_length=1, max_length=64)
    telegram_username: Optional[str] = None
    first_name: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    telegram_id: str
    telegram_username: Optional[str] = None
    first_name: Optional[str] = None

    # Shared wallet
    balance: float

    is_banned: bool

    created_at: datetime

    class Config:
        from_attributes = True


# =========================================================
# WALLET
# =========================================================

class WalletResponse(BaseModel):
    balance: float


class WalletTransactionResponse(BaseModel):
    id: int
    transaction_type: str
    amount: float
    balance_after: float
    game: Optional[str] = None
    reference: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# =========================================================
# WALLET OPERATIONS (DIRECT DEPOSIT / WITHDRAW)
# =========================================================

class DepositCreate(BaseModel):
    telegram_id: str = Field(..., min_length=1, max_length=64)
    telegram_name: Optional[str] = None
    amount: float = Field(..., gt=0, le=1_000_000)
    bank_name: str = Field(..., min_length=1, max_length=100)
    sms_data: str = Field(..., min_length=1)


class WithdrawCreate(BaseModel):
    telegram_id: str = Field(..., min_length=1, max_length=64)
    amount: float = Field(..., gt=0, le=1_000_000)
    bank_name: str = Field(..., min_length=1, max_length=100)
    account_number: str = Field(..., min_length=1, max_length=255)


class DepositRequest(BaseModel):
    amount: float = Field(
        ...,
        gt=0,
        le=1_000_000
    )


class WithdrawRequest(BaseModel):
    amount: float = Field(
        ...,
        gt=0,
        le=1_000_000
    )


# =========================================================
# GAME WALLET OPERATIONS
# =========================================================

class GameBetRequest(BaseModel):
    amount: float = Field(
        ...,
        gt=0
    )

    game: str = Field(
        ...,
        min_length=1,
        max_length=50
    )

    reference: Optional[str] = Field(
        default=None,
        max_length=255
    )


class GameWinRequest(BaseModel):
    amount: float = Field(
        ...,
        gt=0
    )

    game: str = Field(
        ...,
        min_length=1,
        max_length=50
    )

    reference: Optional[str] = Field(
        default=None,
        max_length=255
    )


# =========================================================
# GAME RESULT
# =========================================================

class GameWalletResponse(BaseModel):
    success: bool
    balance: float
    amount: float
    transaction_type: str
    game: str
    message: Optional[str] = None
