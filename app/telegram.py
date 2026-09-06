import os
import sys
import time
import requests
import threading
from datetime import datetime
from telebot import TeleBot, types
from telebot.apihelper import ApiTelegramException

# --------------------------------------------------------------------------
# ⚙️ የቅንብር ክፍሎች (Configurations)
# --------------------------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE"))
BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "QuickBirrGamesBot").strip().replace("@", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "123456789")
ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID", "").strip()

# 🔗 የባክኤንድ አድራሻ (Quick Birr Games)
SERVER_URL = os.getenv("SERVER_URL", "https://web-production-30301.up.railway.app").rstrip('/')
BACKEND_URL = SERVER_URL
MINI_APP_URL = SERVER_URL

# 🖼️ የማቀባበያ ምስል ሊንክ
WELCOME_IMAGE_URL = f"{SERVER_URL}/static/images/welcome.jpeg"

bot = TeleBot(BOT_TOKEN)

USER_REF_CACHE = {}

print(f"🎰 የ Quick Birr Games ቦት (@{BOT_USERNAME}) ስራ ጀምሯል...")

# 👥 ጀርባ ላይ አዲስ ተጫዋች የሚመዘግብ Thread
def register_user_background(telegram_id, telegram_name, first_name, phone_number=None, referred_by=None):
    register_api_url = f"{BACKEND_URL}/api/users"
    payload = {
        "telegram_id": str(telegram_id),
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

# 📢 ማስታወቂያ ለሁሉም ተጠቃሚዎች መላኪያ ፋንክሽን
def broadcast_worker(text_message, reply_markup=None):
    print("📢 የማስታወቂያ ፕሮሞሽን ለተጠቃሚዎች መላክ ተጀምሯል...")
    
    user_ids = []
    try:
        res = requests.get(f"{BACKEND_URL}/api/users/all_ids", timeout=10)
        if res.status_code == 200:
            data = res.json()
            user_ids = data if isinstance(data, list) else data.get("user_ids", [])
            print(f"📊 በአጠቃላይ {len(user_ids)} ተጠቃሚዎች ተገኝተዋል")
    except Exception as e:
        print(f"❌ ከባክኤንድ ጋር መገናኘት አልተቻለም፦ {e}")

    if not user_ids:
        print("⚠️ ምንም የሚላክላቸው ተጠቃሚዎች አልተገኙም!")
        return

    success_count, fail_count = 0, 0
    for u_id in user_ids:
        if not u_id:
            continue
        try:
            bot.send_message(
                str(u_id).strip(), 
                text_message, 
                parse_mode="HTML", 
                reply_markup=reply_markup, 
                disable_web_page_preview=True
            )
            success_count += 1
            time.sleep(0.04)  # Rate limit
        except Exception:
            fail_count += 1

    print(f"🎉 ማስታወቂያ ተጠናቋል! ስኬታማ፦ {success_count}፣ ያልተላኩ፦ {fail_count}")

# 1️⃣ /start Command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    telegram_id = message.from_user.id
    msg_parts = message.text.split()
    
    if len(msg_parts) > 1:
        ref_arg = msg_parts[1]
        referred_by = ref_arg.replace("ref_", "").strip() if ref_arg.startswith("ref_") else ref_arg.strip()
        if str(referred_by) != str(telegram_id):
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

    bot.send_message(chat_id, "✅ በስኬት ተመዝግበዋል!", reply_markup=types.ReplyKeyboardRemove())

    my_ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{telegram_id}"
    welcome_text = (
        f"👋 ሰላም <b>{first_name}</b>፣ ወደ <b>Quick Birr Games</b> እንኳን መጡ! 🎲\n\n"
        "የተለያዩ አዝናኝ ጨዋታዎችን በመጫወት ያሸንፉ!\n\n"
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

# 📢 4️⃣ ADMIN: /broadcast <message>
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
        res_data = response.json() if response.headers.get('content-type') == 'application/json' else {"success": response.ok}

        if response.status_code == 200 and res_data.get("success", True):
            status_emoji = "✅" if action == "approve" else "❌"
            status_text = "APPROVED" if action == "approve" else "REJECTED"
            bot.answer_callback_query(call.id, text=f"{status_emoji} {tx_type.upper()} #{target_id} {status_text}", show_alert=True)
            
            new_text = f"{call.message.text}\n\n{status_emoji} <b>{status_text} at {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC</b>"
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=new_text, parse_mode="HTML")
        else:
            bot.answer_callback_query(call.id, text=f"❌ ስህተት፦ {res_data.get('message', 'Failed')}", show_alert=True)
    except Exception as e:
        bot.answer_callback_query(call.id, text="⚠️ ከሰርቨር ጋር መገናኘት አልተቻለም", show_alert=True)

# 🛠️ Admin Deposit/Withdraw Approval Handlers
@bot.callback_query_handler(func=lambda call: call.data.startswith(('approve_dep_', 'reject_dep_', 'approve_with_', 'reject_with_')))
def handle_admin_actions(call):
    bot.answer_callback_query(call.id, text="⏳ ውሳኔዎ በሂደት ላይ ነው...")
    
    parts = call.data.split('_')
    action, tx_type, target_id = parts[0], parts[1], int(parts[2])
    backend_action = "APPROVE" if action == "approve" else "REJECT"

    endpoint = "deposit" if tx_type == "dep" else "withdraw"
    url = f"{BACKEND_URL}/api/users/admin/{endpoint}/approve"
    payload = {
        "request_id": target_id, 
        "action": backend_action,
        "admin_telegram_id": str(call.from_user.id),
        "admin_password": ADMIN_PASSWORD
    }

    threading.Thread(
        target=send_admin_action_to_backend, 
        args=(call, url, payload, {"Content-Type": "application/json"}, target_id, action, tx_type),
        daemon=True
    ).start()
