import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    User,
    Deposit,
    Withdrawal,
    WalletTransaction,
    DailyCashback,
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
# 🔗 Database Dependency
# --------------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
            balance=0.0
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"✅ [USER CREATED]: DB ID #{user.id} ({orig_tg_id})")
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


# 2️⃣ Get User Profile
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


# 3️⃣ Get All User IDs for Broadcast
@router.get("/all_ids")
def get_all_user_ids(db: Session = Depends(get_db)):
    users = db.query(User.telegram_id).all()
    return [str(u[0]).strip() for u in users if u[0] and str(u[0]).strip().lower() not in INVALID_TG_IDS]


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
            balance=0.0
        )
        db.add(user)
        db.commit()
        db.refresh(user)

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
    
    if not user or user.balance < req.amount:
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
        print(f"⚠️ [ADMIN DEPOSIT ACTION FAILED]: Deposit #{req_id} not found or not pending")
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
        print(f"⚠️ [ADMIN WITHDRAW ACTION FAILED]: Withdrawal #{req_id} not found or not pending")
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

    # -----------------------------------------------------
    # Check if today's cashback was already claimed
    # -----------------------------------------------------
    claimed = db.query(DailyCashback).filter(
        DailyCashback.user_id == user.id,
        DailyCashback.cashback_date == today,
        DailyCashback.status == "claimed"
    ).first()

    # -----------------------------------------------------
    # Calculate today's approved deposits
    # -----------------------------------------------------
    deposits = db.query(Deposit).filter(
        Deposit.user_id == user.id,
        Deposit.status == "approved"
    ).all()

    today_deposit_total = 0.0

    for dep in deposits:
        if dep.created_at:
            dep_date = dep.created_at.astimezone(
                timezone.utc
            ).strftime("%Y-%m-%d")

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

    # -----------------------------------------------------
    # Prevent duplicate claim
    # -----------------------------------------------------
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

    # -----------------------------------------------------
    # Calculate today's approved deposits
    # -----------------------------------------------------
    deposits = db.query(Deposit).filter(
        Deposit.user_id == user.id,
        Deposit.status == "approved"
    ).all()

    today_deposit_total = 0.0

    for dep in deposits:
        if dep.created_at:
            dep_date = dep.created_at.astimezone(
                timezone.utc
            ).strftime("%Y-%m-%d")

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

    # -----------------------------------------------------
    # Add cashback to shared wallet
    # -----------------------------------------------------
    user.balance = float(user.balance or 0) + cashback_amount

    # -----------------------------------------------------
    # Create cashback record
    # -----------------------------------------------------
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

    # -----------------------------------------------------
    # Wallet transaction
    # -----------------------------------------------------
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

    print(
        f"🎁 [DAILY CASHBACK CLAIMED] "
        f"User={user.telegram_id} "
        f"Deposit={today_deposit_total:.2f} "
        f"Cashback={cashback_amount:.2f} "
        f"Balance={user.balance:.2f}"
    )

    # -----------------------------------------------------
    # Telegram notification
    # -----------------------------------------------------
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

class BonusClaimRequest(BaseModel):
    telegram_id: str

@router.post("/bonus/claim-channel")
def claim_channel_bonus(req: BonusClaimRequest, db: Session = Depends(get_db)):
    tg_id = str(req.telegram_id).strip()

    if not tg_id or tg_id.lower() in INVALID_TG_IDS:
        return {"success": False, "message": "ተቀባይነት የሌለው የቴሌግራም ID!"}

    user = db.query(User).filter(User.telegram_id == tg_id).first()
    if not user:
        return {"success": False, "message": "ተጫዋቹ አልተገኘም!"}

    # 1. ቻናሉን መቀላቀሉን በ Telegram Bot API ማረጋገጥ
    channel_username = "@quickbirr_games"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember?chat_id={channel_username}&user_id={tg_id}"
    
    try:
        req_tg = urllib.request.Request(url)
        with urllib.request.urlopen(req_tg, timeout=5) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            
            if res_data.get("ok"):
                status = res_data["result"]["status"]
                # አባል ከሆነ 'creator', 'administrator', ወይም 'member' ይሆናል
                if status not in ['creator', 'administrator', 'member']:
                    return {"success": False, "message": "እባክዎን አስቀድመው ቻናላችንን ይቀላቀሉ!"}
            else:
                return {"success": False, "message": "ቻናሉን መቀላቀልዎን ማረጋገጥ አልተቻለም!"}
    except Exception as e:
        print(f"⚠️ Telegram Member Verification Error: {e}")
        # Telegram API ካልመለሰ ቀጥታ እንዳያግደው ወይም የራሱን ማረጋገጫ መስጠት ይቻላል

    # 2. ቦነሱን ቀደም ብሎ ወስዶ እንደሆነ ማረጋገጥ (ለምሳሌ በ User model ላይ has_claimed_channel_bonus ካለ)
    if getattr(user, "has_claimed_channel_bonus", False):
        return {"success": False, "message": "የቻናል ቦነስን አስቀድመው ወስደዋል!"}

    # 3. +10 BIRR መጨመር
    bonus_amount = 10.0
    user.balance = float(user.balance or 0.0) + bonus_amount
    
    if hasattr(user, "has_claimed_channel_bonus"):
        user.has_claimed_channel_bonus = True

    # የትራንዛክሽን መዝገብ ማስገባት
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

    # ለተጠቃሚው በቴሌግራም መልእክት መላክ
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
