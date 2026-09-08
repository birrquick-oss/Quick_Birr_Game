import os
import requests
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import SessionLocal
from app.models import User, Deposit, Withdrawal, WalletTransaction

router = APIRouter(
    prefix="/api",
    tags=["Users"]
)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE"))
ADMIN_TELEGRAM_ID = str(os.getenv("ADMIN_TELEGRAM_ID", "")).strip()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def send_admin_notification(text: str, reply_markup=None):
    if not ADMIN_TELEGRAM_ID:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": ADMIN_TELEGRAM_ID, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"❌ Notification error: {e}")

# Pydantic Schemas
class UserRegisterPayload(BaseModel):
    telegram_id: str
    telegram_username: Optional[str] = None
    first_name: Optional[str] = None
    phone_number: Optional[str] = None
    referred_by: Optional[str] = None

class DepositCreate(BaseModel):
    telegram_id: str
    telegram_name: Optional[str] = None
    amount: float
    method: str
    sms_text: str

class WithdrawCreate(BaseModel):
    telegram_id: str
    amount: float
    method: str
    account_number: str

class AdminAction(BaseModel):
    id: int
    action: str
    admin_telegram_id: Optional[str] = None

# 👤 1. Get User Profile
@router.get("/users/profile/{telegram_id}")
def get_user_profile(telegram_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == str(telegram_id).strip()).first()
    if not user:
        raise HTTPException(status_code=404, detail="ተጠቃሚው አልተገኘም")
    
    return {
        "success": True,
        "profile": {
            "telegram_id": user.telegram_id,
            "telegram_username": user.telegram_username or user.first_name,
            "balance": user.balance,
            "phone_number": user.phone_number
        }
    }

# 📥 2. User Registration
@router.post("/users/register")
def register_user(payload: UserRegisterPayload, db: Session = Depends(get_db)):
    tg_id_str = str(payload.telegram_id).strip()
    existing = db.query(User).filter(User.telegram_id == tg_id_str).first()
    
    if existing:
        if payload.phone_number:
            existing.phone_number = str(payload.phone_number).strip()
        if payload.telegram_username:
            existing.telegram_username = payload.telegram_username
        if payload.first_name:
            existing.first_name = payload.first_name
        db.commit()
        return {"success": True, "message": "መረጃው ዘምኗል።", "user": {"telegram_id": existing.telegram_id, "balance": existing.balance}}

    new_user = User(
        telegram_id=tg_id_str,
        telegram_username=payload.telegram_username,
        first_name=payload.first_name,
        phone_number=payload.phone_number,
        referred_by=payload.referred_by,
        balance=0.0
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"success": True, "message": "ምዝገባው ተጠናቋል", "user": {"telegram_id": new_user.telegram_id, "balance": 0.0}}

# 💰 3. User Deposit Request
@router.post("/users/deposit")
def user_deposit_request(req: DepositCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == str(req.telegram_id).strip()).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_dep = Deposit(
        user_id=user.id,
        telegram_id=user.telegram_id,
        telegram_name=req.telegram_name,
        amount=req.amount,
        method=req.method,
        sms_text=req.sms_text,
        status="pending"
    )
    db.add(new_dep)
    db.commit()
    db.refresh(new_dep)

    inline_keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Approve", "callback_data": f"approve_dep_{new_dep.id}"},
            {"text": "❌ Reject", "callback_data": f"reject_dep_{new_dep.id}"}
        ]]
    }
    msg_text = f"💰 <b>Quick Birr Deposit #{new_dep.id}</b>\n\n👤 {req.telegram_name} ({req.telegram_id})\n💵 {req.amount} ETB\n🏦 {req.method}\n📄 SMS: {req.sms_text}"
    background_tasks.add_task(send_admin_notification, msg_text, inline_keyboard)

    return {"success": True, "message": "የማስገቢያ ጥያቄዎ ለአድሚን ተልኳል!"}

# 📤 4. User Withdraw Request
@router.post("/users/withdraw")
def user_withdraw_request(req: WithdrawCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == str(req.telegram_id).strip()).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.balance < req.amount:
        return {"success": False, "message": "በቂ ባላንስ የሎትም!"}

    # Deduct balance temporarily and log
    user.balance -= req.amount
    
    new_with = Withdrawal(
        user_id=user.id,
        amount=req.amount,
        method=req.method,
        account_number=req.account_number,
        status="pending"
    )
    db.add(new_with)
    db.commit()
    db.refresh(new_with)

    inline_keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Approve", "callback_data": f"approve_with_{new_with.id}"},
            {"text": "❌ Reject", "callback_data": f"reject_with_{new_with.id}"}
        ]]
    }
    msg_text = f"⚠️ <b>Quick Birr Withdraw #{new_with.id}</b>\n\n👤 ID: {user.telegram_id}\n💵 {req.amount} ETB\n🏦 {req.method}\n💳 Acc: {req.account_number}"
    background_tasks.add_task(send_admin_notification, msg_text, inline_keyboard)

    return {"success": True, "message": "የማውጫ ጥያቄዎ ተመዝግቧል!"}

# 👮‍♂️ 5. Admin Approve/Reject Deposit
@router.post("/deposit/admin/approve")
def admin_approve_deposit(payload: AdminAction, db: Session = Depends(get_db)):
    dep = db.query(Deposit).filter(Deposit.id == payload.id).first()
    if not dep or dep.status != "pending":
        return {"success": False, "message": "ጥያቄው አልተገኘም ወይም ውሳኔ አግኝቷል!"}

    user = db.query(User).filter(User.id == dep.user_id).first()
    if payload.action.upper() == "APPROVE":
        dep.status = "approved"
        user.balance += dep.amount
        
        # Add Wallet Transaction
        tx = WalletTransaction(
            user_id=user.id,
            transaction_type="deposit",
            amount=dep.amount,
            balance_after=user.balance,
            reference=f"DEP_{dep.id}",
            description=f"Deposit via {dep.method}"
        )
        db.add(tx)
        db.commit()
        return {"success": True, "message": "ዲፖዚቱ ጸድቋል!"}
    else:
        dep.status = "rejected"
        db.commit()
        return {"success": True, "message": "ዲፖዚቱ ውድቅ ተደርጓል!"}

# 👮‍♂️ 6. Admin Approve/Reject Withdraw
@router.post("/withdraw/admin/approve")
def admin_approve_withdraw(payload: AdminAction, db: Session = Depends(get_db)):
    with_req = db.query(Withdrawal).filter(Withdrawal.id == payload.id).first()
    if not with_req or with_req.status != "pending":
        return {"success": False, "message": "ጥያቄው አልተገኘም ወይም ውሳኔ አግኝቷል!"}

    user = db.query(User).filter(User.id == with_req.user_id).first()
    if payload.action.upper() == "APPROVE":
        with_req.status = "approved"
        
        # Log Wallet Transaction
        tx = WalletTransaction(
            user_id=user.id,
            transaction_type="withdrawal",
            amount=-with_req.amount,
            balance_after=user.balance,
            reference=f"WITH_{with_req.id}",
            description=f"Withdrawal via {with_req.method}"
        )
        db.add(tx)
        db.commit()
        return {"success": True, "message": "ማውጣቱ ጸድቋል!"}
    else:
        with_req.status = "rejected"
        user.balance += with_req.amount  # Refund back
        db.commit()
        return {"success": True, "message": "ማውጣቱ ውድቅ ተደርጎ ብሩ ተመልሷል!"}
