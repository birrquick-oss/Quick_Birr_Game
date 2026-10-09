import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    User,
    Deposit,
    Withdrawal,
    WalletTransaction,
    DailyCashback,
    BonusCampaign,
    BonusClaim,
)

router = APIRouter(
    prefix="/api/users",
    tags=["Users & Wallet"]
)

# --------------------------------------------------------------------------
# ⚙️ Configuration & Environment Variables
# --------------------------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN", ""))
ADMIN_TELEGRAM_ID = str(os.getenv("ADMIN_TELEGRAM_ID", "")).strip()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "123456789")

# 🛑 ወደ ባክኤንድ እንዳይገቡ የተከለከሉ ተቀባይነት የሌላቸው/የሞከራ Telegram IDዎች
INVALID_TG_IDS = {"12345678", "null", "undefined", "", "none"}


# --------------------------------------------------------------------------
# 🔗 Database Dependency & Timezone Helper
# --------------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """ማንኛውንም DateTime ወደ UTC Timezone Aware ይቀይራል።"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# --------------------------------------------------------------------------
# 📢 Telegram Notification Helpers
# --------------------------------------------------------------------------
def send_telegram_request(url: str, payload: dict):
    """ከማንኛውም የውጭ ላይብረሪ ነፃ በሆነው urllib ጥያቄዎችን የሚልክ ተግባር"""
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url, 
            data=data, 
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            pass
    except Exception as e:
        print(f"⚠️ Telegram HTTP request error: {e}")

def notify_admin(text: str, reply_markup: dict = None):
    if not BOT_TOKEN or not ADMIN_TELEGRAM_ID:
        print("⚠️ Admin notification skipped: Missing BOT_TOKEN or ADMIN_TELEGRAM_ID")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": ADMIN_TELEGRAM_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    send_telegram_request(url, payload)

def notify_user(telegram_id: str, text: str):
    if not BOT_TOKEN or not telegram_id or str(telegram_id).lower() in INVALID_TG_IDS:
        print(f"⚠️ User notification skipped for ID: {telegram_id}")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": str(telegram_id),
        "text": text,
        "parse_mode": "HTML"
    }
    send_telegram_request(url, payload)


# --------------------------------------------------------------------------
# 📝 Pydantic Schemas
# --------------------------------------------------------------------------
class UserSync(BaseModel):
    telegram_id: str
    telegram_username: Optional[str] = None
    first_name: Optional[str] = None
    phone_number: Optional[str] = None
    referred_by: Optional[str] = None

class DepositRequest(BaseModel):
    telegram_id: str
    telegram_name: Optional[str] = "ተጫዋች"
    amount: float
    bank_name: str
    sms_data: str

class WithdrawRequest(BaseModel):
    telegram_id: str
    amount: float
    bank_name: str
    account_number: str

class AdminApproveAction(BaseModel):
    request_id: Optional[int] = None
    deposit_id: Optional[int] = None
    withdraw_id: Optional[int] = None
    action: str  # "APPROVE" or "REJECT"
    admin_telegram_id: Optional[str] = None
    admin_password: Optional[str] = None

class BonusCampaignCreate(BaseModel):
    amount: float
    max_claims: int
    duration_minutes: int
    start_at: Optional[str] = None

    title: Optional[str] = None
    description: Optional[str] = None

    admin_telegram_id: Optional[str] = None
    admin_password: Optional[str] = None

class BonusAdminRequest(BaseModel):
    admin_telegram_id: Optional[str] = None
    admin_password: Optional[str] = None

class BonusClaimRequest(BaseModel):
    telegram_id: str

# --------------------------------------------------------------------------
# 🚀 API Endpoints
# --------------------------------------------------------------------------

# 1️⃣ User Registration / Sync
@router.post("")
@router.post("/register")
def sync_or_register_user(data: UserSync, db: Session = Depends(get_db)):
    print(f"📥 [USER SYNC REQUEST]: {data.model_dump()}")
    tg_id = str(data.telegram_id).strip().lower()

    if not tg_id or tg_id in INVALID_TG_IDS:
        print(f"❌ [USER SYNC REJECTED]: Invalid Telegram ID '{tg_id}'")
        return {"success": False, "message": "Invalid Telegram ID"}

    orig_tg_id = str(data.telegram_id).strip()
    user = db.query(User).filter(User.telegram_id == orig_tg_id).first()
    
    if not user:
        user = User(
            telegram_id=orig_tg_id,
            telegram_username=data.telegram_username,
            first_name=data.first_name,
            balance=15.0  # 👈 15 ብር የመመዝገቢያ ቦነስ
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # የ 15 ብር ቦነስ Transaction ታሪክ መመዝገቢያ
        tx = WalletTransaction(
            user_id=user.id,
            transaction_type="bonus",
            amount=15.0,
            balance_after=user.balance,
            description="Welcome Registration Bonus (+15 ETB)"
        )
        db.add(tx)
        db.commit()

        print(f"✅ [USER CREATED WITH 15 ETB BONUS]: DB ID #{user.id} ({orig_tg_id})")

    else:
        if data.first_name:
            user.first_name = data.first_name
        if data.telegram_username:
            user.telegram_username = data.telegram_username
        db.commit()

    return {
        "success": True, 
        "user": {
            "id": user.id, 
            "telegram_id": user.telegram_id, 
            "balance": user.balance
        }
    }


# 2️⃣ Get All User IDs for Broadcast
@router.get("/all_ids")
def get_all_user_ids(db: Session = Depends(get_db)):
    users = db.query(User.telegram_id).all()
    return [str(u[0]).strip() for u in users if u[0] and str(u[0]).strip().lower() not in INVALID_TG_IDS]


# 🏆 2️⃣.1️⃣ LEADERBOARD API (Top 20 Depositors)
@router.get("/leaderboard")
def get_top_depositors(db: Session = Depends(get_db)):
    top_users = (
        db.query(
            User.telegram_id,
            User.first_name,
            User.telegram_username,
            func.sum(Deposit.amount).label("total_deposited")
        )
        .join(Deposit, User.id == Deposit.user_id)
        .filter(Deposit.status == "approved")
        .group_by(User.id)
        .order_by(func.sum(Deposit.amount).desc())
        .limit(20)
        .all()
    )

    result = []
    for rank, (tg_id, first_name, username, total_deposited) in enumerate(top_users, start=1):
        name = first_name or username or f"Player_{str(tg_id)[-4:]}"
        masked_id = str(tg_id)[:3] + "***" + str(tg_id)[-2:] if len(str(tg_id)) > 5 else str(tg_id)
        
        result.append({
            "rank": rank,
            "name": name,
            "telegram_id": masked_id,
            "total_deposited": round(float(total_deposited or 0), 2)
        })

    return {"success": True, "leaderboard": result}


# 3️⃣ Get User Profile
@router.get("/{telegram_id}")
def get_user_profile(telegram_id: str, db: Session = Depends(get_db)):
    tg_id = str(telegram_id).strip()
    if not tg_id or tg_id.lower() in INVALID_TG_IDS:
        raise HTTPException(status_code=400, detail="Invalid Telegram ID")

    user = db.query(User).filter(User.telegram_id == tg_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "success": True,
        "user": {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "first_name": user.first_name,
            "balance": user.balance
        }
    }


# 4️⃣ Request Deposit
@router.post("/deposit")
def request_deposit(req: DepositRequest, db: Session = Depends(get_db)):
    print(f"📥 [DEPOSIT REQUEST RECEIVED]: {req.model_dump()}")
    tg_id = str(req.telegram_id).strip()

    if not tg_id or tg_id.lower() in INVALID_TG_IDS:
        print(f"❌ [DEPOSIT FAILED]: Invalid Telegram ID '{tg_id}'")
        return {"success": False, "message": "የቴሌግራም ማንነት ማረጋገጥ አልተቻለም! እባክዎን አፑን በቦቱ በኩል ይክፈቱት።"}

    user = db.query(User).filter(User.telegram_id == tg_id).first()
    
    if not user:
        user = User(
            telegram_id=tg_id, 
            first_name=req.telegram_name, 
            balance=15.0  # 👈 15 ብር የመመዝገቢያ ቦነስ
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        tx = WalletTransaction(
            user_id=user.id,
            transaction_type="bonus",
            amount=15.0,
            balance_after=user.balance,
            description="Welcome Registration Bonus (+15 ETB)"
        )
        db.add(tx)
        db.commit()

    dep = Deposit(
        user_id=user.id, 
        telegram_id=user.telegram_id,
        telegram_name=req.telegram_name,
        amount=req.amount, 
        method=req.bank_name, 
        sms_text=req.sms_data, 
        status="pending"
    )
    db.add(dep)
    db.commit()
    db.refresh(dep)

    print(f"✅ [DEPOSIT CREATED IN DB]: ID #{dep.id} for User {user.telegram_id}")

    # Admin Notification
    msg = (
        f"💰 <b>NEW DEPOSIT REQUEST #{dep.id}</b>\n\n"
        f"👤 <b>User:</b> {req.telegram_name} ({req.telegram_id})\n"
        f"💵 <b>Amount:</b> {req.amount} ETB\n"
        f"🏦 <b>Bank:</b> {req.bank_name}\n"
        f"📄 <b>SMS Data:</b>\n<code>{req.sms_data}</code>"
    )
    buttons = {
        "inline_keyboard": [[
            {"text": "✅ Approve", "callback_data": f"approve_dep_{dep.id}"},
            {"text": "❌ Reject", "callback_data": f"reject_dep_{dep.id}"}
        ]]
    }
    notify_admin(msg, buttons)
    
    return {"success": True, "message": "የዲፖዚት ጥያቄዎ ለአድሚን ተልኳል!"}

# 5️⃣ Request Withdrawal
@router.post("/withdraw")
def request_withdraw(req: WithdrawRequest, db: Session = Depends(get_db)):
    print(f"📥 [WITHDRAWAL REQUEST RECEIVED]: {req.model_dump()}")
    tg_id = str(req.telegram_id).strip()

    if not tg_id or tg_id.lower() in INVALID_TG_IDS:
        print(f"❌ [WITHDRAWAL FAILED]: Invalid Telegram ID '{tg_id}'")
        return {"success": False, "message": "የቴሌግራም ማንነት ማረጋገጥ አልተቻለም! እባክዎን አፑን በቦቱ በኩል ይክፈቱት።"}

    user = db.query(User).filter(User.telegram_id == tg_id).first()
    
    if not user:
        print(f"❌ [WITHDRAWAL FAILED]: User Not Found ({tg_id})")
        return {"success": False, "message": "ተጫዋቹ አልተገኘም!"}

    # 🛑 ተጫዋቹ ያደረጋቸውን አጠቃላይ Approved የሆኑ Deposits መደመር
    total_approved_deposit = db.query(func.sum(Deposit.amount)).filter(
        Deposit.user_id == user.id,
        Deposit.status == "approved"
    ).scalar() or 0.0

    # 🛑 ቢያንስ 200 ETB Deposit ያላደረገ ከሆነ ማገድ
    MIN_REQUIRED_DEPOSIT = 200.0
    if total_approved_deposit < MIN_REQUIRED_DEPOSIT:
        print(f"❌ [WITHDRAWAL BLOCKED]: User {tg_id} deposited only {total_approved_deposit} ETB (Required: {MIN_REQUIRED_DEPOSIT} ETB)")
        return {
            "success": False, 
            "message": f"ገንዘብ ለማውጣት ቢያንስ {MIN_REQUIRED_DEPOSIT:g} ETB Deposit ማድረግ አለብዎት! (እስካሁን ያደረጉት: {total_approved_deposit:g} ETB)"
        }

    if user.balance < req.amount:
        print(f"❌ [WITHDRAWAL FAILED]: Insufficient Balance for User {tg_id}")
        return {"success": False, "message": "በቂ ባላንስ የሎትም!"}

    user.balance -= req.amount
    
    withd = Withdrawal(
        user_id=user.id, 
        amount=req.amount, 
        method=req.bank_name, 
        account_number=req.account_number, 
        status="pending"
    )
    db.add(withd)
    db.commit()
    db.refresh(withd)

    tx = WalletTransaction(
        user_id=user.id,
        transaction_type="withdrawal",
        amount=-req.amount,
        balance_after=user.balance,
        description=f"Withdrawal request via {req.bank_name} ({req.account_number})"
    )
    db.add(tx)
    db.commit()

    print(f"✅ [WITHDRAWAL CREATED IN DB]: ID #{withd.id} for User {user.telegram_id}")

    msg = (
        f"🔻 <b>NEW WITHDRAWAL REQUEST #{withd.id}</b>\n\n"
        f"👤 <b>User Telegram ID:</b> {req.telegram_id}\n"
        f"💵 <b>Amount:</b> {req.amount} ETB\n"
        f"🏦 <b>Bank:</b> {req.bank_name}\n"
        f"💳 <b>Account:</b> <code>{req.account_number}</code>"
    )
    buttons = {
        "inline_keyboard": [[
            {"text": "✅ Approve", "callback_data": f"approve_with_{withd.id}"},
            {"text": "❌ Reject", "callback_data": f"reject_with_{withd.id}"}
        ]]
    }
    notify_admin(msg, buttons)
    
    return {"success": True, "message": "የማውጫ ጥያቄዎ ተመዝግቧል!"}

# 6️⃣ Admin Deposit Action
@router.post("/admin/deposit/approve")
def admin_approve_deposit(data: AdminApproveAction, db: Session = Depends(get_db)):
    print(f"📥 [ADMIN DEPOSIT ACTION RECEIVED]: {data.model_dump()}")
    req_id = data.request_id or data.deposit_id
    if not req_id:
        print("❌ [ADMIN DEPOSIT ACTION FAILED]: Missing request_id/deposit_id")
        return {"success": False, "message": "Deposit ID is missing"}

    dep = db.query(Deposit).filter(Deposit.id == req_id).first()
    if not dep or str(dep.status).lower() != "pending":
        print(f"⚠ [ADMIN DEPOSIT ACTION FAILED]: Deposit #{req_id} not found or not pending")
        return {"success": False, "message": "ጥያቄው አልተገኘም ወይም አስቀድሞ ውሳኔ አግኝቷል!"}

    user = db.query(User).filter(User.id == dep.user_id).first()
    if not user:
        print(f"❌ [ADMIN DEPOSIT ACTION FAILED]: Associated User #{dep.user_id} not found")
        return {"success": False, "message": "ተጫዋቹ አልተገኘም!"}

    if str(data.action).upper() == "APPROVE":
        dep.status = "approved"
        user.balance = float(user.balance or 0.0) + float(dep.amount)
        
        tx = WalletTransaction(
            user_id=user.id,
            transaction_type="deposit",
            amount=dep.amount,
            balance_after=user.balance,
            description=f"Approved deposit #{dep.id} via {dep.method}"
        )
        db.add(tx)
        db.commit()
        db.refresh(user)
        print(f"🎉 [DEPOSIT #{dep.id} APPROVED]: New Balance = {user.balance} ETB for User {user.telegram_id}")
        notify_user(user.telegram_id, f"✅ የ {dep.amount} ETB ዲፖዚት ጥያቄዎ ጸድቋል! አዲሱ ባላንስዎ: {user.balance} ETB")
    else:
        dep.status = "rejected"
        db.commit()
        print(f"🚫 [DEPOSIT #{dep.id} REJECTED]")
        notify_user(user.telegram_id, f"❌ የ {dep.amount} ETB ዲፖዚት ጥያቄዎ ውድቅ ተደርጓል።")

    return {"success": True, "message": f"Deposit #{dep.id} marked as {dep.status}"}

# 7️⃣ Admin Withdrawal Action
@router.post("/admin/withdraw/approve")
def admin_approve_withdraw(data: AdminApproveAction, db: Session = Depends(get_db)):
    print(f"📥 [ADMIN WITHDRAW ACTION RECEIVED]: {data.model_dump()}")
    req_id = data.request_id or data.withdraw_id
    if not req_id:
        print("❌ [ADMIN WITHDRAW ACTION FAILED]: Missing request_id/withdraw_id")
        return {"success": False, "message": "Withdrawal ID is missing"}

    withd = db.query(Withdrawal).filter(Withdrawal.id == req_id).first()
    if not withd or str(withd.status).lower() != "pending":
        print(f"⚠ [ADMIN WITHDRAW ACTION FAILED]: Withdrawal #{req_id} not found or not pending")
        return {"success": False, "message": "ጥያቄው አልተገኘም ወይም አስቀድሞ ውሳኔ አግኝቷል!"}

    user = db.query(User).filter(User.id == withd.user_id).first()
    if not user:
        print(f"❌ [ADMIN WITHDRAW ACTION FAILED]: Associated User #{withd.user_id} not found")
        return {"success": False, "message": "ተጫዋቹ አልተገኘም!"}

    if str(data.action).upper() == "APPROVE":
        withd.status = "approved"
        db.commit()
        print(f"🎉 [WITHDRAWAL #{withd.id} APPROVED] for User {user.telegram_id}")
        notify_user(user.telegram_id, f"✅ የ {withd.amount} ETB ማውጫ ጥያቄዎ ተፈጽሟል።")
    else:
        withd.status = "rejected"
        user.balance = float(user.balance or 0.0) + float(withd.amount)
        
        tx = WalletTransaction(
            user_id=user.id,
            transaction_type="refund",
            amount=withd.amount,
            balance_after=user.balance,
            description=f"Refunded rejected withdrawal #{withd.id}"
        )
        db.add(tx)
        db.commit()
        db.refresh(user)
        print(f"🚫 [WITHDRAWAL #{withd.id} REJECTED & REFUNDED]: Balance = {user.balance} ETB")
        notify_user(user.telegram_id, f"❌ የ {withd.amount} ETB ማውጫ ጥያቄዎ ውድቅ ተደርጓል፣ ገንዘቡ ወደ ባላንስዎ ተመልሷል።")

    return {"success": True, "message": f"Withdrawal #{withd.id} marked as {withd.status}"}

# =========================================================
# 🔄 DAILY CASHBACK
# =========================================================

CASHBACK_PERCENT = 10.0


def get_today_utc_date():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


@router.get("/cashback/status/{telegram_id}")
def get_cashback_status(
    telegram_id: str,
    db: Session = Depends(get_db)
):
    tg_id = str(telegram_id).strip()

    if not tg_id or tg_id.lower() in INVALID_TG_IDS:
        raise HTTPException(
            status_code=400,
            detail="Invalid Telegram ID"
        )

    user = db.query(User).filter(
        User.telegram_id == tg_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    today = get_today_utc_date()

    claimed = db.query(DailyCashback).filter(
        DailyCashback.user_id == user.id,
        DailyCashback.cashback_date == today,
        DailyCashback.status == "claimed"
    ).first()

    deposits = db.query(Deposit).filter(
        Deposit.user_id == user.id,
        Deposit.status == "approved"
    ).all()

    today_deposit_total = 0.0

    for dep in deposits:
        if dep.created_at:
            dep_date = ensure_utc(dep.created_at).strftime("%Y-%m-%d")
            if dep_date == today:
                today_deposit_total += float(dep.amount or 0)

    cashback_amount = round(
        today_deposit_total * CASHBACK_PERCENT / 100,
        2
    )

    return {
        "success": True,
        "cashback": {
            "date": today,
            "percentage": CASHBACK_PERCENT,
            "deposit_amount": round(today_deposit_total, 2),
            "cashback_amount": cashback_amount,
            "claimed": claimed is not None,
            "can_claim": (
                claimed is None
                and cashback_amount > 0
            )
        },
        "balance": round(float(user.balance or 0), 2)
    }


# =========================================================
# 🎁 CLAIM DAILY CASHBACK
# =========================================================

@router.post("/cashback/claim/{telegram_id}")
def claim_daily_cashback(
    telegram_id: str,
    db: Session = Depends(get_db)
):
    tg_id = str(telegram_id).strip()

    if not tg_id or tg_id.lower() in INVALID_TG_IDS:
        raise HTTPException(
            status_code=400,
            detail="Invalid Telegram ID"
        )

    user = db.query(User).filter(
        User.telegram_id == tg_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    today = get_today_utc_date()

    existing_claim = db.query(DailyCashback).filter(
        DailyCashback.user_id == user.id,
        DailyCashback.cashback_date == today
    ).first()

    if existing_claim:
        if existing_claim.status == "claimed":
            return {
                "success": False,
                "claimed": True,
                "message": "የዛሬን Cashback አስቀድመው ወስደዋል።",
                "balance": round(float(user.balance or 0), 2)
            }

    deposits = db.query(Deposit).filter(
        Deposit.user_id == user.id,
        Deposit.status == "approved"
    ).all()

    today_deposit_total = 0.0

    for dep in deposits:
        if dep.created_at:
            dep_date = ensure_utc(dep.created_at).strftime("%Y-%m-%d")
            if dep_date == today:
                today_deposit_total += float(dep.amount or 0)

    cashback_amount = round(
        today_deposit_total * CASHBACK_PERCENT / 100,
        2
    )

    if cashback_amount <= 0:
        return {
            "success": False,
            "claimed": False,
            "message": "ዛሬ የተፈቀደ Deposit ስለሌለ የCashback መጠን የለዎትም።",
            "balance": round(float(user.balance or 0), 2)
        }

    user.balance = float(user.balance or 0) + cashback_amount

    cashback = DailyCashback(
        user_id=user.id,
        cashback_date=today,
        deposit_amount=today_deposit_total,
        cashback_amount=cashback_amount,
        status="claimed",
        balance_after=user.balance,
        claimed_at=datetime.now(timezone.utc)
    )

    db.add(cashback)

    tx = WalletTransaction(
        user_id=user.id,
        transaction_type="cashback",
        amount=cashback_amount,
        balance_after=user.balance,
        description=(
            f"Daily {CASHBACK_PERCENT}% cashback "
            f"for {today} on approved deposits "
            f"of {today_deposit_total:.2f} ETB"
        )
    )

    db.add(tx)
    db.commit()
    db.refresh(user)
    db.refresh(cashback)

    notify_user(
        user.telegram_id,
        (
            f"🎁 <b>Daily Cashback</b>\n\n"
            f"💰 Today's Deposit: "
            f"<b>{today_deposit_total:.2f} ETB</b>\n"
            f"🎁 Cashback: "
            f"<b>{cashback_amount:.2f} ETB</b>\n\n"
            f"💳 New Balance: "
            f"<b>{user.balance:.2f} ETB</b>"
        )
    )

    return {
        "success": True,
        "claimed": True,
        "message": "Daily Cashback በተሳካ ሁኔታ ተጨምሯል!",
        "cashback": {
            "date": today,
            "percentage": CASHBACK_PERCENT,
            "deposit_amount": round(today_deposit_total, 2),
            "cashback_amount": cashback_amount
        },
        "balance": round(float(user.balance or 0), 2)
    }

# =========================================================
# 🎁 CLAIM CHANNEL BONUS (+10 BIRR)
# =========================================================

@router.post("/bonus/claim-channel")
def claim_channel_bonus(req: BonusClaimRequest, db: Session = Depends(get_db)):
    tg_id = str(req.telegram_id).strip()

    if not tg_id or tg_id.lower() in INVALID_TG_IDS:
        return {"success": False, "message": "ተቀባይነት የሌለው የቴሌግራም ID!"}

    user = db.query(User).filter(User.telegram_id == tg_id).first()
    if not user:
        return {"success": False, "message": "ተጫዋቹ አልተገኘም!"}

    channel_username = "@quickbirr_games"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember?chat_id={channel_username}&user_id={tg_id}"
    
    try:
        req_tg = urllib.request.Request(url)
        with urllib.request.urlopen(req_tg, timeout=5) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            
            if res_data.get("ok"):
                status = res_data["result"]["status"]
                if status not in ['creator', 'administrator', 'member']:
                    return {"success": False, "message": "እባክዎን አስቀድመው ቻናላችንን ይቀላቀሉ!"}
            else:
                return {"success": False, "message": "ቻናሉን መቀላቀልዎን ማረጋገጥ አልተቻለም!"}
    except Exception as e:
        print(f"⚠️ Telegram Member Verification Error: {e}")

    if getattr(user, "has_claimed_channel_bonus", False):
        return {"success": False, "message": "የቻናል ቦነስን አስቀድመው ወስደዋል!"}

    bonus_amount = 10.0
    user.balance = float(user.balance or 0.0) + bonus_amount
    
    if hasattr(user, "has_claimed_channel_bonus"):
        user.has_claimed_channel_bonus = True

    tx = WalletTransaction(
        user_id=user.id,
        transaction_type="bonus",
        amount=bonus_amount,
        balance_after=user.balance,
        description="Channel Join Bonus (+10 ETB)"
    )
    db.add(tx)

    db.commit()
    db.refresh(user)

    notify_user(
        user.telegram_id,
        f"🎉 <b>Channel Join Bonus!</b>\n\n"
        f"ወደ ቻናላችን ስለተቀላቀሉ የ <b>10.00 ETB</b> ቦነስ ተጨምሮልዎታል።\n"
        f"💳 አዲሱ ባላንስዎ: <b>{user.balance:.2f} ETB</b>"
    )

    return {
        "success": True,
        "message": "🎉 +10 BIRR ቦነስ በተሳካ ሁኔታ ወደ ባላንስዎ ተጨምሯል!",
        "balance": round(float(user.balance), 2)
    }

# =========================================================
# 🎁 BONUS CAMPAIGN SYSTEM
# =========================================================

ADDIS_ABABA_TZ = ZoneInfo("Africa/Addis_Ababa")


def _check_bonus_admin(data):
    if ADMIN_TELEGRAM_ID:
        if str(data.admin_telegram_id or "").strip() != str(ADMIN_TELEGRAM_ID).strip():
            raise HTTPException(
                status_code=403,
                detail="Admin Telegram ID is not authorized."
            )

    if str(data.admin_password or "") != str(ADMIN_PASSWORD):
        raise HTTPException(
            status_code=403,
            detail="Invalid admin password."
        )


# =========================================================
# CREATE BONUS CAMPAIGN (Instant Support)
# =========================================================

@router.post("/bonus/create")
def create_bonus_campaign(
    data: BonusCampaignCreate,
    db: Session = Depends(get_db)
):
    _check_bonus_admin(data)

    if data.amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Bonus amount must be greater than 0."
        )

    if data.max_claims <= 0:
        raise HTTPException(
            status_code=400,
            detail="Maximum players must be greater than 0."
        )

    if data.duration_minutes <= 0:
        raise HTTPException(
            status_code=400,
            detail="Duration must be greater than 0 minutes."
        )

    now_utc = datetime.now(timezone.utc)

    # ⏱️ start_at ካልተላከ ወዲያውኑ አሁን ይጀምራል
    if data.start_at:
        try:
            local_dt = datetime.strptime(data.start_at.strip(), "%Y-%m-%d %H:%M")
            local_dt = local_dt.replace(tzinfo=ADDIS_ABABA_TZ)
            start_utc = local_dt.astimezone(timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD HH:MM")
    else:
        start_utc = now_utc

    end_utc = start_utc + timedelta(minutes=data.duration_minutes)

    title = data.title.strip() if data.title else f"🎁 {data.amount:g} ETB BONUS"
    description = (
        data.description.strip()
        if data.description
        else f"First {data.max_claims} players can claim {data.amount:g} ETB bonus."
    )

    campaign = BonusCampaign(
        amount=float(data.amount),
        max_claims=int(data.max_claims),
        claimed_count=0,
        start_at=start_utc,
        end_at=end_utc,
        status="active" if start_utc <= now_utc else "scheduled",
        title=title,
        description=description,
        created_by=str(data.admin_telegram_id or ADMIN_TELEGRAM_ID),
        broadcast_sent=True
    )

    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    print(
        f"🎁 BONUS CAMPAIGN CREATED | "
        f"ID={campaign.id} | "
        f"Amount={campaign.amount} | "
        f"Max={campaign.max_claims} | "
        f"Start={campaign.start_at} | "
        f"End={campaign.end_at}"
    )

    return {
        "success": True,
        "campaign_id": campaign.id,
        "amount": campaign.amount,
        "max_claims": campaign.max_claims,
        "claimed_count": campaign.claimed_count,
        "start_at_utc": campaign.start_at.isoformat(),
        "end_at_utc": campaign.end_at.isoformat(),
        "status": campaign.status,
    }


# =========================================================
# GET ACTIVE / UPCOMING BONUS
# =========================================================

@router.get("/bonus/active")
def get_active_bonus(
    db: Session = Depends(get_db)
):
    now = datetime.now(timezone.utc)

    campaigns = (
        db.query(BonusCampaign)
        .filter(BonusCampaign.status.in_(["scheduled", "active"]))
        .order_by(BonusCampaign.start_at.asc())
        .all()
    )

    campaign = None
    for c in campaigns:
        start_at = ensure_utc(c.start_at)
        end_at = ensure_utc(c.end_at)
        if start_at and end_at and start_at <= now < end_at and c.claimed_count < c.max_claims:
            campaign = c
            break

    if not campaign:
        return {
            "success": True,
            "active": False,
            "campaign": None,
        }

    if campaign.status == "scheduled":
        campaign.status = "active"
        db.commit()

    start_at = ensure_utc(campaign.start_at)
    end_at = ensure_utc(campaign.end_at)

    return {
        "success": True,
        "active": True,
        "campaign": {
            "id": campaign.id,
            "amount": campaign.amount,
            "max_claims": campaign.max_claims,
            "claimed_count": campaign.claimed_count,
            "remaining": max(0, campaign.max_claims - campaign.claimed_count),
            "start_at": start_at.isoformat() if start_at else None,
            "end_at": end_at.isoformat() if end_at else None,
            "status": campaign.status,
            "title": campaign.title,
            "description": campaign.description,
        },
    }


# =========================================================
# CLAIM BONUS
# =========================================================

@router.post("/bonus/claim/{campaign_id}/{telegram_id}")
def claim_bonus_campaign(
    campaign_id: int,
    telegram_id: str,
    db: Session = Depends(get_db)
):
    telegram_id = str(telegram_id).strip()

    if not telegram_id or telegram_id in INVALID_TG_IDS:
        raise HTTPException(status_code=400, detail="Invalid Telegram ID.")

    user = (
        db.query(User)
        .filter(User.telegram_id == telegram_id)
        .with_for_update()
        .first()
    )

    if not user:
        raise HTTPException(status_code=404, detail="User is not registered.")

    campaign = (
        db.query(BonusCampaign)
        .filter(BonusCampaign.id == campaign_id)
        .with_for_update()
        .first()
    )

    if not campaign:
        raise HTTPException(status_code=404, detail="Bonus campaign not found.")

    now = datetime.now(timezone.utc)
    start_at = ensure_utc(campaign.start_at)
    end_at = ensure_utc(campaign.end_at)

    if start_at and now < start_at:
        raise HTTPException(status_code=400, detail="This bonus is not available yet.")

    if end_at and now >= end_at:
        campaign.status = "ended"
        db.commit()
        raise HTTPException(status_code=400, detail="This bonus campaign has ended.")

    if campaign.claimed_count >= campaign.max_claims:
        campaign.status = "sold_out"
        db.commit()
        raise HTTPException(status_code=400, detail="This bonus is SOLD OUT.")

    existing_claim = (
        db.query(BonusClaim)
        .filter(
            BonusClaim.campaign_id == campaign_id,
            BonusClaim.user_id == user.id,
        )
        .first()
    )

    if existing_claim:
        raise HTTPException(status_code=400, detail="You already claimed this bonus.")

    campaign.claimed_count += 1
    campaign.status = "active"

    bonus_amount = float(campaign.amount)
    current_balance = float(user.balance or 0.0)
    user.balance = current_balance + bonus_amount

    wallet_transaction = WalletTransaction(
        user_id=user.id,
        transaction_type="bonus_campaign",
        amount=bonus_amount,
        balance_after=user.balance,
        game="bonus",
        reference=f"BONUS_CAMPAIGN_{campaign.id}",
        description=f"Bonus Campaign #{campaign.id} claim - {bonus_amount:g} ETB",
        created_at=datetime.now(timezone.utc),
    )
    db.add(wallet_transaction)

    claim = BonusClaim(
        campaign_id=campaign.id,
        user_id=user.id,
        telegram_id=telegram_id,
        amount=bonus_amount,
        balance_after=user.balance,
        created_at=datetime.now(timezone.utc),
    )
    db.add(claim)

    if campaign.claimed_count >= campaign.max_claims:
        campaign.status = "sold_out"

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"❌ Bonus claim failed for {telegram_id}: {e}")
        raise HTTPException(status_code=400, detail="Bonus could not be claimed. Please try again.")

    db.refresh(user)

    return {
        "success": True,
        "message": f"{bonus_amount:g} ETB bonus added successfully!",
        "campaign_id": campaign.id,
        "amount": bonus_amount,
        "balance": user.balance,
        "claimed_count": campaign.claimed_count,
        "remaining": max(0, campaign.max_claims - campaign.claimed_count),
    }


# =========================================================
# BONUS CAMPAIGN STATUS
# =========================================================

@router.get("/bonus/status/{campaign_id}")
def bonus_campaign_status(
    campaign_id: int,
    db: Session = Depends(get_db)
):
    campaign = db.query(BonusCampaign).filter(BonusCampaign.id == campaign_id).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Bonus campaign not found.")

    now = datetime.now(timezone.utc)
    current_status = campaign.status
    end_at = ensure_utc(campaign.end_at)
    start_at = ensure_utc(campaign.start_at)

    if campaign.status not in ["cancelled", "sold_out"] and end_at and now >= end_at:
        campaign.status = "ended"
        db.commit()

    return {
        "success": True,
        "campaign": {
            "id": campaign.id,
            "amount": campaign.amount,
            "max_claims": campaign.max_claims,
            "claimed_count": campaign.claimed_count,
            "remaining": max(0, campaign.max_claims - campaign.claimed_count),
            "start_at": start_at.isoformat() if start_at else None,
            "end_at": end_at.isoformat() if end_at else None,
            "status": campaign.status,
            "previous_status": current_status,
            "broadcast_sent": campaign.broadcast_sent,
            "title": campaign.title,
            "description": campaign.description,
        },
    }


# =========================================================
# CANCEL BONUS CAMPAIGN
# =========================================================

@router.post("/bonus/cancel/{campaign_id}")
def cancel_bonus_campaign(
    campaign_id: int,
    req: Optional[BonusAdminRequest] = None,
    db: Session = Depends(get_db),
):
    admin_tg = req.admin_telegram_id if req else None
    admin_pass = req.admin_password if req else None

    if ADMIN_TELEGRAM_ID and str(admin_tg or "").strip() != str(ADMIN_TELEGRAM_ID).strip():
        raise HTTPException(status_code=403, detail="Admin Telegram ID is not authorized.")

    if str(admin_pass or "") != str(ADMIN_PASSWORD):
        raise HTTPException(status_code=403, detail="Invalid admin password.")

    campaign = db.query(BonusCampaign).filter(BonusCampaign.id == campaign_id).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Bonus campaign not found.")

    if campaign.status in ["sold_out", "ended"]:
        raise HTTPException(status_code=400, detail=f"Campaign is already {campaign.status}.")

    campaign.status = "cancelled"
    db.commit()

    return {
        "success": True,
        "message": f"Bonus campaign #{campaign_id} cancelled.",
        "campaign_id": campaign_id,
        "status": campaign.status,
    }


@router.post("/bonus/due-broadcasts")
def get_due_bonus_broadcasts(
    data: BonusAdminRequest,
    db: Session = Depends(get_db),
):
    if ADMIN_TELEGRAM_ID and str(data.admin_telegram_id or "").strip() != str(ADMIN_TELEGRAM_ID).strip():
        raise HTTPException(status_code=403, detail="Admin Telegram ID is not authorized.")

    if str(data.admin_password or "") != str(ADMIN_PASSWORD):
        raise HTTPException(status_code=403, detail="Invalid admin password.")

    now = datetime.now(timezone.utc)

    all_campaigns = (
        db.query(BonusCampaign)
        .filter(
            BonusCampaign.status.in_(["scheduled", "active"]),
            BonusCampaign.broadcast_sent == False,
        )
        .all()
    )

    result = []
    for campaign in all_campaigns:
        start_at = ensure_utc(campaign.start_at)
        end_at = ensure_utc(campaign.end_at)
        if start_at and start_at <= now:
            campaign.status = "active"
            campaign.broadcast_sent = True
            result.append({
                "id": campaign.id,
                "amount": campaign.amount,
                "max_claims": campaign.max_claims,
                "claimed_count": campaign.claimed_count,
                "start_at": start_at.isoformat() if start_at else None,
                "end_at": end_at.isoformat() if end_at else None,
                "title": campaign.title,
                "description": campaign.description,
            })

    if result:
        db.commit()

    return {
        "success": True,
        "campaigns": result,
    }
