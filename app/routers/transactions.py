import os
import requests
from fastapi import APIRouter, Depends, BackgroundTasks, Request
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models import User, Deposit, Withdrawal
from app.schemas import DepositCreate, WithdrawCreate

router = APIRouter(
    prefix="/api",
    tags=["Transactions"]
)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", os.getenv("BOT_TOKEN", ""))
ADMIN_TELEGRAM_ID = str(os.getenv("ADMIN_TELEGRAM_ID", "")).strip()
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")


# 📢 Telegram Notification Helper
def send_admin_notification(text: str, reply_markup=None):
    if not ADMIN_TELEGRAM_ID or not BOT_TOKEN:
        print("⚠️ ADMIN_TELEGRAM_ID ወይም BOT_TOKEN አልተዋቀረም!")
        return
        
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": ADMIN_TELEGRAM_ID, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"❌ Telegram notify error: {e}")


def _telegram_edit_message_sync(chat_id: str, message_id: int, text: str):
    if not BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id": str(chat_id),
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"❌ Telegram Edit Exception: {e}")


# 💰 1. User Deposit Request
@router.post("/users/deposit")
def user_deposit_request(req: DepositCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    tg_id_str = str(req.telegram_id).strip()
    if not tg_id_str:
        return {"success": False, "message": "Invalid Telegram ID."}
    
    user = db.query(User).filter(User.telegram_id == tg_id_str).first()
    if not user:
        return {"success": False, "message": "ተጠቃሚው አልተገኘም!"}

    try:
        new_deposit = Deposit(
            user_id=user.id,
            amount=req.amount,
            method=req.bank_name,     
            sms_text=req.sms_data,    
            status="pending",
            created_at=datetime.utcnow(),
            telegram_id=tg_id_str,
            telegram_name=req.telegram_name if req.telegram_name else "ተጫዋች"
        )
        db.add(new_deposit)
        db.commit()
        db.refresh(new_deposit)
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"የዲፖዚት ጥያቄ መመዝገብ አልተቻለም፦ {str(e)}"}

    inline_keyboard = {
        "inline_keyboard": [[
            {"text": "✅ APPROVED (አጽድቅ)", "callback_data": f"approve_dep_{new_deposit.id}"},
            {"text": "❌ REJECTED (ሰርዝ)", "callback_data": f"reject_dep_{new_deposit.id}"}
        ]]
    }

    msg_text = (
        f"🔔 <b>አዲስ የገንዘብ ማስገቢያ ጥያቄ!</b>\n\n"
        f"🆔 <b>የጥያቄ ቁጥር፦</b> #{new_deposit.id}\n"
        f"👤 ተጫዋች፦ {new_deposit.telegram_name} (ID: {new_deposit.telegram_id})\n"
        f"🏦 ባንክ፦ {req.bank_name}\n"
        f"💰 የገንዘብ መጠን፦ <b>{req.amount} ETB</b>\n\n"
        f"📝 <b>የባንክ SMS መረጃ፦</b>\n<code>{req.sms_data}</code>"
    )
    
    background_tasks.add_task(send_admin_notification, msg_text, inline_keyboard)
    return {"success": True, "message": "የማስገቢያ ጥያቄዎ በተሳካ ሁኔታ ለአድሚን ተልኳል!"}


# 📤 2. User Withdraw Request
@router.post("/users/withdraw")
def user_withdraw_request(req: WithdrawCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    tg_id_str = str(req.telegram_id).strip()
    user = db.query(User).filter(User.telegram_id == tg_id_str).first()
    if not user:
        return {"success": False, "message": "ተጠቃሚው አልተገኘም!"}

    user_balance = getattr(user, "balance", 0.0) or 0.0
    if user_balance < req.amount:
        return {"success": False, "message": f"ይቅርታ፣ በቂ ባላንስ የሎትም! ያሎት ባላንስ {user_balance} ETB ነው።"}

    try:
        user.balance = user_balance - req.amount
        
        new_withdraw = Withdrawal(
            user_id=user.id,
            amount=req.amount,
            method=req.bank_name,     
            account_number=str(req.account_number), 
            status="pending",
            created_at=datetime.utcnow()
        )
        db.add(new_withdraw)
        db.commit()
        db.refresh(new_withdraw)
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"የማውጫ ጥያቄ መመዝገብ አልተቻለም፦ {str(e)}"}

    inline_keyboard = {
        "inline_keyboard": [[
            {"text": "✅ APPROVED (ከፍያለሁ)", "callback_data": f"approve_with_{new_withdraw.id}"},
            {"text": "❌ REJECTED (ሰርዝ)", "callback_data": f"reject_with_{new_withdraw.id}"}
        ]]
    }

    msg_text = (
        f"⚠️ <b>አዲስ የገንዘብ ማውጫ ጥያቄ!</b>\n\n"
        f"🆔 <b>የጥያቄ ቁጥር፦</b> #{new_withdraw.id}\n"
        f"👤 ተጫዋች ID፦ {tg_id_str}\n"
        f"🏦 ባንክ፦ {req.bank_name}\n"
        f"💳 የባንክ አካውንት፦ <code>{req.account_number}</code>\n"
        f"💰 የገንዘብ መጠን፦ <b>{req.amount} ETB</b>"
    )

    background_tasks.add_task(send_admin_notification, msg_text, inline_keyboard)
    return {"success": True, "message": "የማውጫ ጥያቄዎ ተመዝግቧል!"}


# 👮‍♂️ 3. Admin Deposit Approval/Rejection Action
@router.post("/deposit/admin/approve")
def admin_approve_deposit(payload: dict, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    target_id = payload.get("id")
    action = payload.get("action", "").upper()
    admin_id = payload.get("admin_telegram_id", "Admin")
    message_id = payload.get("message_id")

    deposit = db.query(Deposit).filter(Deposit.id == target_id).first()
    if not deposit or deposit.status != "pending":
        return {"success": False, "message": "ጥያቄው አልተገኘም ወይም ቀድሞ ውሳኔ አግኝቷል!"}

    user = db.query(User).filter(User.id == deposit.user_id).first()
    if not user:
        return {"success": False, "message": "ተጫዋቹ አልተገኘም!"}

    if action in ["APPROVE", "APPROVED"]:
        user.balance = (user.balance or 0.0) + deposit.amount
        deposit.status = "approved"
        db.commit()

        if message_id:
            text = (
                f"🟢 <b>የዲፖዚት ጥያቄ #{deposit.id} ጸድቋል!</b>\n\n"
                f"💰 <b>የተጨመረው መጠን፦</b> {deposit.amount} ETB\n"
                f"👤 <b>ተጫዋች ID፦</b> <code>{user.telegram_id}</code>\n"
                f"👮‍♂️ <b>ያጸደቀው አድሚን፦</b> {admin_id}"
            )
            background_tasks.add_task(_telegram_edit_message_sync, ADMIN_TELEGRAM_ID, message_id, text)
        return {"success": True, "message": "ዲፖዚቱ ጸድቋል!"}
    else:
        deposit.status = "rejected"
        db.commit()
        if message_id:
            text = f"🔴 <b>የዲፖዚት ጥያቄ #{deposit.id} ውድቅ ተደርጓል!</b>\n👮‍♂️ <b>የሰረዘው አድሚን፦</b> {admin_id}"
            background_tasks.add_task(_telegram_edit_message_sync, ADMIN_TELEGRAM_ID, message_id, text)
        return {"success": True, "message": "ጥያቄው ውድቅ ተደርጓል!"}


# 👮‍♂️ 4. Admin Withdraw Approval/Rejection Action
@router.post("/withdraw/admin/approve")
def admin_approve_withdraw(payload: dict, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    target_id = payload.get("id")
    action = payload.get("action", "").upper()
    admin_id = payload.get("admin_telegram_id", "Admin")
    message_id = payload.get("message_id")

    withdraw = db.query(Withdrawal).filter(Withdrawal.id == target_id).first()
    if not withdraw or withdraw.status != "pending":
        return {"success": False, "message": "ጥያቄው አልተገኘም ወይም ውሳኔ አግኝቷል!"}

    user = db.query(User).filter(User.id == withdraw.user_id).first()

    if action in ["REJECT", "REJECTED"]:
        if user:
            user.balance = (user.balance or 0.0) + withdraw.amount
        withdraw.status = "rejected"
        db.commit()

        if message_id:
            text = f"🔴 <b>የማውጫ ጥያቄ #{withdraw.id} ተሰርዟል!</b> ብሩ ተመልሷል።"
            background_tasks.add_task(_telegram_edit_message_sync, ADMIN_TELEGRAM_ID, message_id, text)
        return {"success": True, "message": "የማውጫ ጥያቄው ውድቅ ተደርጓል!"}
    else:
        withdraw.status = "approved"
        db.commit()
        if message_id:
            text = f"🟢 <b>የማውጫ ክፍያ #{withdraw.id} መፈጸሙ ተረጋግጧል!</b>"
            background_tasks.add_task(_telegram_edit_message_sync, ADMIN_TELEGRAM_ID, message_id, text)
        return {"success": True, "message": "ክፍያው መፈጸሙ ተረጋግጧል!"}


# 🤖 5. Telegram Webhook Callback Handler
@router.post("/telegram-webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    if "callback_query" in data:
        cb = data["callback_query"]
        callback_data = cb.get("data", "")
        message = cb.get("message", {})
        message_id = message.get("message_id")
        admin_tg_id = str(cb.get("from_user", {}).get("id"))

        if callback_data.startswith(("approve_dep_", "reject_dep_")):
            action = "APPROVE" if callback_data.startswith("approve_dep_") else "REJECT"
            dep_id = int(callback_data.replace("approve_dep_", "").replace("reject_dep_", ""))
            requests.post(f"{BACKEND_URL}/api/deposit/admin/approve", json={
                "id": dep_id, "action": action, "admin_telegram_id": admin_tg_id, "message_id": message_id
            })

        elif callback_data.startswith(("approve_with_", "reject_with_")):
            action = "APPROVE" if callback_data.startswith("approve_with_") else "REJECT"
            with_id = int(callback_data.replace("approve_with_", "").replace("reject_with_", ""))
            requests.post(f"{BACKEND_URL}/api/withdraw/admin/approve", json={
                "id": with_id, "action": action, "admin_telegram_id": admin_tg_id, "message_id": message_id
            })

    return {"status": "ok"}
