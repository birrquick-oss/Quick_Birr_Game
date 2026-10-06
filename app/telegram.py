import os
import sys
import time
import requests
import threading
from datetime import datetime, timezone
from telebot import TeleBot, types
from telebot.apihelper import ApiTelegramException

# --------------------------------------------------------------------------
# ⚙️ Configuration & Environment Variables
# --------------------------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE"))
BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "QuickBirr_Games_Bot").strip().replace("@", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "123456789")
ADMIN_TELEGRAM_ID = str(os.getenv("ADMIN_TELEGRAM_ID", "")).strip()

# 🔗 Backend & Mini App URL
SERVER_URL = os.getenv("SERVER_URL", "https://web-production-30301.up.railway.app").rstrip('/')
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000" if os.getenv("RAILWAY_ENVIRONMENT") else SERVER_URL).rstrip('/')
MINI_APP_URL = SERVER_URL

# 🖼️ Welcome Image URL
WELCOME_IMAGE_URL = f"{SERVER_URL}/static/images/welcome.jpeg"

# 🛑 Invalid / Dummy Telegram IDs
INVALID_TG_IDS = {"12345678", "null", "undefined", "", "none"}

bot = TeleBot(BOT_TOKEN)

USER_REF_CACHE = {}

print(f"🎰 Quick Birr Games Bot (@{BOT_USERNAME}) is running...")
print(f"⚙️ Configured Admin Telegram ID: '{ADMIN_TELEGRAM_ID}'")


# 👥 Background User Registration Thread
def register_user_background(telegram_id, telegram_name, first_name, phone_number=None, referred_by=None):
    tg_str = str(telegram_id).strip()
    if not tg_str or tg_str.lower() in INVALID_TG_IDS:
        print(f"⚠️ Registration skipped for invalid ID: {tg_str}")
        return

    register_api_url = f"{BACKEND_URL}/api/users/register"
    payload = {
        "telegram_id": tg_str,
        "telegram_username": telegram_name,
        "first_name": first_name,
        "phone_number": str(phone_number) if phone_number else None,
        "referred_by": str(referred_by) if referred_by else None
    }
        
    try:
        response = requests.post(register_api_url, json=payload, timeout=10)
        print(f"📡 Backend Register Response: {response.json()}")
    except Exception as e:
        print(f"❌ Failed to register user in background: {e}")


# 📢 Broadcast Worker Thread
def broadcast_worker(text_message, reply_markup=None):
    print("📢 Starting Broadcast Promotion...")
    
    user_ids = []
    try:
        res = requests.get(f"{BACKEND_URL}/api/users/all_ids", timeout=10)
        if res.status_code == 200:
            data = res.json()
            user_ids = data if isinstance(data, list) else data.get("user_ids", [])
            print(f"📊 Total Users Found: {len(user_ids)}")
    except Exception as e:
        print(f"❌ Backend connection failed: {e}")

    if not user_ids:
        print("⚠️ No users found to broadcast.")
        return

    success_count, fail_count = 0, 0
    for u_id in user_ids:
        u_str = str(u_id).strip()
        if not u_str or u_str.lower() in INVALID_TG_IDS:
            continue
        try:
            bot.send_message(
                u_str, 
                text_message, 
                parse_mode="HTML", 
                reply_markup=reply_markup, 
                disable_web_page_preview=True
            )
            success_count += 1
            time.sleep(0.04)  # Rate limiting protection
        except Exception as e:
            fail_count += 1

    print(f"🎉 Broadcast finished! Success: {success_count}, Failed: {fail_count}")

# =========================================================
# 🎁 BONUS CAMPAIGN BROADCAST
# =========================================================

def send_bonus_campaign_broadcast(campaign):
    """
    Sends the bonus announcement immediately to all users.
    """
    campaign_id = campaign["id"]
    amount = campaign["amount"]
    max_claims = campaign["max_claims"]

    title = campaign.get("title") or f"🎁 {amount:g} ETB BONUS"
    description = campaign.get("description") or (
        f"First {max_claims} players can claim "
        f"{amount:g} ETB bonus."
    )

    message_text = (
        f"🎁 <b>{title}</b>\n\n"
        f"{description}\n\n"
        f"💰 Bonus: <b>{amount:g} ETB</b>\n"
        f"👥 First: <b>{max_claims} Players</b>\n"
        f"⏰ Limited Time Only!\n\n"
        f"🔥 <b>CLAIM NOW!</b>"
    )

    markup = types.InlineKeyboardMarkup()
    claim_button = types.InlineKeyboardButton(
        text="🎁 CLAIM BONUS",
        callback_data=f"claim_bonus_{campaign_id}"
    )
    markup.add(claim_button)

    print(f"🎁 Sending Bonus Campaign #{campaign_id} broadcast...")

    threading.Thread(
        target=broadcast_worker,
        args=(message_text, markup),
        daemon=True
    ).start()


# =========================================================
# 🎁 ADMIN: INSTANT BONUS CAMPAIGN
# /bonus AMOUNT PLAYERS MINUTES
# Example: /bonus 50 100 30
# =========================================================

@bot.message_handler(commands=['bonus'])
def handle_bonus_command(message):
    if ADMIN_TELEGRAM_ID and str(message.from_user.id) != str(ADMIN_TELEGRAM_ID):
        bot.reply_to(message, "⛔ ይህንን ትእዛዝ መጠቀም የሚችለው Admin ብቻ ነው!")
        return

    parts = message.text.split()

    if len(parts) != 4:
        bot.reply_to(
            message,
            (
                "⚠️ <b>Bonus Command Format</b>\n\n"
                "<code>/bonus AMOUNT PLAYERS MINUTES</code>\n\n"
                "ምሳሌ፦\n"
                "<code>/bonus 50 100 30</code>\n\n"
                "💰 50 ETB\n"
                "👥 First 100 players\n"
                "⏱️ 30 minutes duration"
            ),
            parse_mode="HTML"
        )
        return

    try:
        amount = float(parts[1])
        max_players = int(parts[2])
        duration_minutes = int(parts[3])
    except Exception:
        bot.reply_to(
            message,
            "❌ የገባው format ትክክል አይደለም።\n\nምሳሌ፦\n<code>/bonus 50 100 30</code>",
            parse_mode="HTML"
        )
        return

    if amount <= 0 or max_players <= 0 or duration_minutes <= 0:
        bot.reply_to(message, "❌ Amount, Players, እና Minutes ከ 0 በላይ መሆን አለባቸው።")
        return

    url = f"{BACKEND_URL}/api/users/bonus/create"
    payload = {
        "amount": amount,
        "max_claims": max_players,
        "duration_minutes": duration_minutes,
        "title": f"🎁 {amount:g} ETB BONUS",
        "description": f"First {max_players} players can claim {amount:g} ETB bonus!",
        "admin_telegram_id": str(message.from_user.id),
        "admin_password": ADMIN_PASSWORD,
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        try:
            data = response.json()
        except Exception:
            data = {}

        if response.status_code == 200 and data.get("success"):
            campaign_id = data["campaign_id"]

            # ወዲያውኑ ማስታወቂያውን (Broadcast) ይልካል
            campaign_obj = {
                "id": campaign_id,
                "amount": amount,
                "max_claims": max_players,
                "title": f"🎁 {amount:g} ETB BONUS",
                "description": f"First {max_players} players can claim {amount:g} ETB bonus!"
            }
            send_bonus_campaign_broadcast(campaign_obj)

            bot.reply_to(
                message,
                (
                    "✅ <b>BONUS CAMPAIGN CREATED & SENDING!</b>\n\n"
                    f"🆔 Campaign: <b>#{campaign_id}</b>\n"
                    f"💰 Bonus: <b>{amount:g} ETB</b>\n"
                    f"👥 Players: <b>{max_players}</b>\n"
                    f"⏱️ Duration: <b>{duration_minutes} minutes</b>\n\n"
                    "🚀 መልእክቱ ወዲያውኑ ለተጠቃሚዎች በሙሉ እየተላከ ነው!"
                ),
                parse_mode="HTML"
            )
        else:
            error_message = data.get("detail", data.get("message", "Unable to create bonus campaign."))
            bot.reply_to(message, f"❌ {error_message}")

    except Exception as e:
        print(f"❌ Bonus creation error: {e}")
        bot.reply_to(message, "⚠️ Backend connection error.")


# 1️⃣ /start Command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    telegram_id = message.from_user.id
    msg_parts = message.text.split()
    
    if len(msg_parts) > 1:
        ref_arg = msg_parts[1]
        referred_by = ref_arg.replace("ref_", "").strip() if ref_arg.startswith("ref_") else ref_arg.strip()
        if str(referred_by) != str(telegram_id) and str(referred_by) not in INVALID_TG_IDS:
            USER_REF_CACHE[telegram_id] = referred_by

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📝 Register Now"))

    welcome_msg = (
        "🎉 እንኳን ወደ Quick Birr Games በሰላም መጡ!\n\n"
        "ለመጫወት እና አሸናፊ ለመሆን ከታች '📝 Register Now' የሚለውን ይጫኑ።"
    )
    bot.send_message(message.chat.id, welcome_msg, reply_markup=markup)


# 2️⃣ Ask Phone
@bot.message_handler(func=lambda message: message.text == "📝 Register Now")
def ask_contact(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📱 Share Contact", request_contact=True))
    bot.send_message(message.chat.id, "📱 ለመመዝገብ ከታች 'Share Contact' የሚለውን ይጫኑ", reply_markup=markup)


# 3️⃣ Contact Received
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    chat_id = message.chat.id
    telegram_id = message.from_user.id
    phone_number = message.contact.phone_number
    user_name = message.from_user.username or f"User_{str(telegram_id)[:5]}"
    first_name = message.from_user.first_name or user_name
    referred_by = USER_REF_CACHE.pop(telegram_id, None)

    threading.Thread(
        target=register_user_background,
        args=(telegram_id, user_name, first_name, phone_number, referred_by),
        daemon=True
    ).start()

    # 🎁 የ 15 ብር ቦነስ እንዳገኘ የሚያሳውቅ መልእክት
    bot.send_message(chat_id, "✅ በስኬት ተመዝግበዋል! 🎁 የ 15.00 ETB የመመዝገቢያ ቦነስ ተሰጥቶዎታል!", reply_markup=types.ReplyKeyboardRemove())

    my_ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{telegram_id}"
    welcome_text = (
        f"👋 ሰላም <b>{first_name}</b>፣ ወደ <b>Quick Birr Games</b> እንኳን መጡ! 🎲\n\n"
        f"🎁 <b>የ 15.00 ETB የመመዝገቢያ ቦነስ ወደ ሂሳብዎ ተጨምሯል!</b>\n"
        "አሁኑኑ የተለያዩ አዝናኝ ጨዋታዎችን በመጫወት ያሸንፉ!\n\n"
        f"🔗 <b>የመጋበዣ ሊንክዎ፦</b>\n<code>{my_ref_link}</code>"
    )

    markup = types.InlineKeyboardMarkup()
    btn_play = types.InlineKeyboardButton(text="🎮 Play Now (ክፈት)", web_app=types.WebAppInfo(url=MINI_APP_URL))
    share_url = f"https://t.me/share/url?url={my_ref_link}&text=Quick%20Birr%20Games%20ተጫውተው%20ያሸንፉ!"
    btn_share = types.InlineKeyboardButton(text="🔗 Share Link", url=share_url)
    markup.add(btn_play, btn_share)

    try:
        bot.send_photo(chat_id, photo=WELCOME_IMAGE_URL, caption=welcome_text, parse_mode="HTML", reply_markup=markup)
    except Exception:
        bot.send_message(chat_id, welcome_text, parse_mode="HTML", reply_markup=markup)


# 4️⃣ ADMIN: /broadcast <message>
@bot.message_handler(commands=['broadcast'])
def handle_broadcast_command(message):
    if ADMIN_TELEGRAM_ID and str(message.from_user.id) != ADMIN_TELEGRAM_ID:
        bot.reply_to(message, "⛔ ይህንን ማድረግ የሚችለው አድሚን ብቻ ነው!")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ እባክዎን የመልእክት ጽሁፍ ያስገቡ!\nምሳሌ፦ `/broadcast ዛሬ የ 50% ቦነስ አዘጋጅተናል!`", parse_mode="Markdown")
        return

    bot.reply_to(message, "🚀 የማስታወቂያ መልእክቱ እየተላከ ነው...")
    threading.Thread(target=broadcast_worker, args=(parts[1], None), daemon=True).start()


# 🛠️ Backend Admin Action Worker
def send_admin_action_to_backend(call, url, payload, headers, target_id, action, tx_type):
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        try:
            res_data = response.json()
        except Exception:
            res_data = {"success": response.ok}

        if response.status_code == 200 and res_data.get("success", True):
            status_emoji = "✅" if action == "approve" else "❌"
            status_text = "APPROVED" if action == "approve" else "REJECTED"
            
            try:
                bot.answer_callback_query(call.id, text=f"{status_emoji} {tx_type.upper()} #{target_id} {status_text}", show_alert=True)
            except Exception:
                pass
            
            current_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')
            new_text = f"{call.message.text}\n\n{status_emoji} <b>{status_text} at {current_time} UTC</b>"
            
            try:
                bot.edit_message_text(
                    chat_id=call.message.chat.id, 
                    message_id=call.message.message_id, 
                    text=new_text, 
                    parse_mode="HTML",
                    reply_markup=None
                )
            except Exception as edit_err:
                print(f"⚠ Telegram message edit issue: {edit_err}")
        else:
            err_msg = res_data.get('detail', res_data.get('message', f'Status Code: {response.status_code}'))
            bot.answer_callback_query(call.id, text=f"❌ ስህተት፦ {err_msg}", show_alert=True)
    except Exception as e:
        print(f"❌ Admin Action Exception Error: {e}")
        bot.answer_callback_query(call.id, text="⚠️ ከሰርቨር ጋር መገናኘት አልተቻለም", show_alert=True)

# =========================================================
# 🎁 CLAIM BONUS BUTTON
# =========================================================

@bot.callback_query_handler(func=lambda call: call.data.startswith("claim_bonus_"))
def handle_bonus_claim(call):
    try:
        campaign_id = int(call.data.replace("claim_bonus_", ""))
    except Exception:
        bot.answer_callback_query(call.id, text="❌ Invalid bonus.", show_alert=True)
        return

    telegram_id = str(call.from_user.id).strip()

    try:
        bot.answer_callback_query(call.id, text="⏳ Checking bonus...", show_alert=False)
    except Exception:
        pass

    url = f"{BACKEND_URL}/api/users/bonus/claim/{campaign_id}/{telegram_id}"

    try:
        response = requests.post(url, timeout=15)
        try:
            data = response.json()
        except Exception:
            data = {}

        if response.status_code == 200 and data.get("success"):
            amount = float(data.get("amount", 0))
            balance = float(data.get("balance", 0))
            claimed_count = int(data.get("claimed_count", 0))

            message = (
                f"🎉 <b>CONGRATULATIONS!</b>\n\n"
                f"🎁 Bonus: <b>{amount:g} ETB</b>\n"
                f"💰 New Balance: <b>{balance:g} ETB</b>\n\n"
                f"👥 Claimed: <b>{claimed_count}</b>\n\n"
                f"🔥 Enjoy Quick Birr Games!"
            )

            try:
                bot.answer_callback_query(call.id, text=f"🎉 {amount:g} ETB BONUS CLAIMED!", show_alert=True)
            except Exception:
                pass

            try:
                bot.send_message(call.message.chat.id, message, parse_mode="HTML")
            except Exception as e:
                print(f"⚠️ Failed sending claim success message: {e}")

        else:
            error_message = data.get("detail", data.get("message", "Bonus cannot be claimed."))
            try:
                bot.answer_callback_query(call.id, text=f"❌ {error_message}", show_alert=True)
            except Exception:
                pass

    except Exception as e:
        print(f"❌ Bonus claim request failed: {e}")
        try:
            bot.answer_callback_query(call.id, text="⚠️ Server connection error. Please try again.", show_alert=True)
        except Exception:
            pass

# =========================================================
# 🎁 ADMIN: BONUS STATUS
# /bonus_status 12
# =========================================================

@bot.message_handler(commands=['bonus_status'])
def handle_bonus_status_command(message):
    if ADMIN_TELEGRAM_ID and str(message.from_user.id) != str(ADMIN_TELEGRAM_ID):
        bot.reply_to(message, "⛔ Admin only.")
        return

    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "ምሳሌ፦ `/bonus_status 12`", parse_mode="Markdown")
        return

    try:
        campaign_id = int(parts[1])
    except Exception:
        bot.reply_to(message, "❌ Invalid campaign ID.")
        return

    url = f"{BACKEND_URL}/api/users/bonus/status/{campaign_id}"

    try:
        response = requests.get(url, timeout=15)
        data = response.json()

        if response.status_code != 200:
            bot.reply_to(message, f"❌ {data.get('detail', 'Campaign not found.')}")
            return

        campaign = data["campaign"]
        bot.reply_to(
            message,
            (
                f"🎁 <b>BONUS #{campaign['id']}</b>\n\n"
                f"💰 Amount: <b>{campaign['amount']:g} ETB</b>\n"
                f"👥 Maximum: <b>{campaign['max_claims']}</b>\n"
                f"✅ Claimed: <b>{campaign['claimed_count']}</b>\n"
                f"🔥 Remaining: <b>{campaign['remaining']}</b>\n"
                f"📌 Status: <b>{campaign['status'].upper()}</b>\n"
                f"📢 Broadcast: <b>{'SENT' if campaign['broadcast_sent'] else 'NOT SENT'}</b>"
            ),
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"❌ Bonus status error: {e}")
        bot.reply_to(message, "⚠️ Backend connection error.")
        
# =========================================================
# 🎁 ADMIN: CANCEL BONUS
# /bonus_cancel 12
# =========================================================

@bot.message_handler(commands=['bonus_cancel'])
def handle_bonus_cancel_command(message):
    if ADMIN_TELEGRAM_ID and str(message.from_user.id) != str(ADMIN_TELEGRAM_ID):
        bot.reply_to(message, "⛔ Admin only.")
        return

    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "ምሳሌ፦ `/bonus_cancel 12`", parse_mode="Markdown")
        return

    try:
        campaign_id = int(parts[1])
    except Exception:
        bot.reply_to(message, "❌ Invalid campaign ID.")
        return

    url = f"{BACKEND_URL}/api/users/bonus/cancel/{campaign_id}"
    payload = {
        "admin_telegram_id": str(message.from_user.id),
        "admin_password": ADMIN_PASSWORD,
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        data = response.json()

        if response.status_code == 200:
            bot.reply_to(message, f"✅ Bonus Campaign <b>#{campaign_id}</b> cancelled.", parse_mode="HTML")
        else:
            bot.reply_to(message, f"❌ {data.get('detail', 'Unable to cancel.')}")

    except Exception as e:
        print(f"❌ Bonus cancel error: {e}")
        bot.reply_to(message, "⚠️ Backend connection error.")
        
# 🛠️ Admin Deposit/Withdraw Approval Callback Handler
@bot.callback_query_handler(func=lambda call: call.data.startswith(('approve_dep_', 'reject_dep_', 'approve_with_', 'reject_with_')))
def handle_admin_actions(call):
    user_id_str = str(call.from_user.id).strip()

    if ADMIN_TELEGRAM_ID and str(user_id_str) != str(ADMIN_TELEGRAM_ID):
        try:
            bot.answer_callback_query(call.id, text="⛔ ይህንን ማድረግ የሚችለው አድሚን ብቻ ነው!", show_alert=True)
        except Exception:
            pass
        return

    try:
        bot.answer_callback_query(call.id, text="⏳ ውሳኔዎ በሂደት ላይ ነው...")
    except Exception:
        pass
    
    parts = call.data.split('_')
    action = parts[0]   # approve or reject
    tx_type = parts[1]  # dep or with
    target_id = int(parts[2])
    
    backend_action = "APPROVE" if action == "approve" else "REJECT"
    endpoint = "deposit" if tx_type == "dep" else "withdraw"
    url = f"{BACKEND_URL}/api/users/admin/{endpoint}/approve"
    
    if tx_type == "dep":
        payload = {
            "deposit_id": target_id,
            "action": backend_action,
            "admin_password": ADMIN_PASSWORD
        }
    else:
        payload = {
            "withdraw_id": target_id,
            "action": backend_action,
            "admin_password": ADMIN_PASSWORD
        }

    threading.Thread(
        target=send_admin_action_to_backend, 
        args=(call, url, payload, {"Content-Type": "application/json"}, target_id, action, tx_type),
        daemon=True
    ).start()


# 🚀 Bot Start Polling Loop
if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True)
