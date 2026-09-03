import random
import asyncio
import json
import inspect
import sys
from datetime import datetime, timezone
from typing import List
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

from app.database import SessionLocal, get_db
from app.models import Game, Setting, User, AdminStats, PlayerCard, Card
from app.wallet import process_game_stake, process_game_win

# =========================================================
# WEBSOCKET CONNECTION MANAGER (Inline Export to prevent ImportError)
# =========================================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

# ሌላ ፋይል ላይ 'from app.websocket_manager import manager' ከተባለ እንዳይበላሽ ማስተካከያ
class DummyModule:
    def __init__(self, mgr):
        self.manager = mgr

sys.modules["app.websocket_manager"] = DummyModule(manager)

# =========================================================
# ROUTER & CONFIGURATIONS (QUICK BIRR BRANDING)
# =========================================================

router = APIRouter(prefix="/api/bingo", tags=["Bingo Game Engine"])

BOT_NAMES = [
    "quick_45456", "birr_MUTD", "quick_Dereje16", "birr_65788", "quick_Gadissa", "birr_43688",  
    "quick_89856", "birr_56488", "quick_Finfine", "birr_88786", "quick_Abeti", "birr_54321",
    "quick_Shegaw16", "birr_78646", "quick_Abenu888", "birr_56787", "quick_Berihun19", "birr_32743",
    "quick_Kaka", "birr_Forever", "quick_Tarekegni", "birr_77633", "quick_Chuchu", "birr_55894",
    "quick_36648", "birr_93121", "quick_Temu19", "birr_48539", "quick_የማሪያምልጅ21", "birr_89175",
    "quick_53929", "birr_79348", "quick_Abdissa", "birr_91976", "quick_Obssa21", "birr_Degu22",
    "quick_48271", "birr_Bekele", "quick_73924", "birr_Miki22", "quick_74583", "birr_Habte"
]

BOT_PHONE_NUMBERS = [
    "2519****2244", "2519****3478", "2519****5589", "2519****8990", "2519****0901", "አልተመዘገበም",
    "2519****6702", "2519****2313", "2519****4424", "2519****4535", "2519****8246", "አልተመዘገበም",
    "2517****5444", "2517****3478", "2517****4589", "2517****9555", "2517****8685", "አልተመዘገበም"
]

SUPPORTED_FEES = [10.0]
BOT_ALLOWED_FEES = [10.0]
CARD_COUNT_LIMIT = 1000

# =========================================================
# HELPER: GENERATE 5x5 BINGO CARD MATRIX
# =========================================================

def generate_5x5_bingo_card():
    col_b = random.sample(range(1, 16), 5)
    col_i = random.sample(range(16, 31), 5)
    col_n = random.sample(range(31, 46), 5)
    col_g = random.sample(range(46, 61), 5)
    col_o = random.sample(range(61, 76), 5)
    
    col_n[2] = "FREE"

    matrix = []
    for r in range(5):
        row = [col_b[r], col_i[r], col_n[r], col_g[r], col_o[r]]
        matrix.append(row)
    return matrix

def ensure_initial_cards_populated(db: Session):
    count = db.query(Card).count()
    if count < CARD_COUNT_LIMIT:
        print(f"⚙️ Populating 1000 Bingo Cards into database...")
        for i in range(1, CARD_COUNT_LIMIT + 1):
            existing = db.query(Card).filter(Card.card_number == i).first()
            if not existing:
                card_matrix = generate_5x5_bingo_card()
                c = Card(
                    card_number=i,
                    data=json.dumps(card_matrix),
                    is_taken=False
                )
                db.add(c)
        db.commit()

# =========================================================
# GAME ENGINE CLASS
# =========================================================

class GameEngine:

    def __init__(self):
        self.running = False
        self.called_numbers = []
        self.current_game = None
        self.house_counters = {10.0: 0}

    def get_bot_user(self, db: Session):
        bot = db.query(User).filter(User.telegram_id == "QUICK_BIRR_BOT_PLAYER").first()
        if not bot:
            default_bot_name = random.choice(BOT_NAMES)
            bot = User(
                telegram_id="QUICK_BIRR_BOT_PLAYER",
                telegram_username=default_bot_name,
                first_name=default_bot_name,
                balance=9999999.0
            )
            if hasattr(bot, "is_bot"):
                bot.is_bot = True
            db.add(bot)
            db.commit()
            db.refresh(bot)
        return bot

    def get_target_bot_card_count(self) -> int:
        now = datetime.now(timezone.utc)
        hour = (now.hour + 3) % 24

        if 6 <= hour < 13:
            return random.randint(50, 100)
        elif 13 <= hour <= 23:
            return random.randint(100, 150)
        elif 0 <= hour < 3:
            return random.randint(40, 80)
        else:
            return random.randint(30, 60)

    async def auto_buy_bot_cards(self, game_id: int):
        db: Session = None
        try:
            db = SessionLocal()
            game = db.query(Game).filter(Game.id == game_id, Game.status.in_(["running", "waiting"])).first()
            if not game:
                return

            bot_user = self.get_bot_user(db)
            target_count = self.get_target_bot_card_count()

            for fee in BOT_ALLOWED_FEES:
                taken_cards = db.query(PlayerCard).filter(
                    PlayerCard.game_id == game_id,
                    PlayerCard.bet_amount == fee
                ).all()
                taken_numbers = {c.card_number for c in taken_cards}

                bot_current_count = sum(1 for c in taken_cards if c.user_id == bot_user.id)
                needed = target_count - bot_current_count

                if needed > 0:
                    available_numbers = [num for num in range(1, CARD_COUNT_LIMIT + 1) if num not in taken_numbers]
                    if available_numbers:
                        cards_to_buy_count = min(needed, len(available_numbers))
                        cards_to_buy = random.sample(available_numbers, cards_to_buy_count)
                        
                        for c_num in cards_to_buy:
                            active_check = db.query(Game).filter(Game.id == game_id, Game.status.in_(["running", "waiting"])).first()
                            if not active_check:
                                break

                            # Double check if card was taken by real player during sleep
                            already_taken = db.query(PlayerCard).filter(
                                PlayerCard.game_id == game_id,
                                PlayerCard.card_number == c_num
                            ).first()
                            if already_taken:
                                continue

                            p_card = PlayerCard(
                                game_id=game_id,
                                user_id=bot_user.id,
                                card_number=c_num,
                                bet_amount=fee
                            )
                            db.add(p_card)

                            main_card = db.query(Card).filter(Card.card_number == c_num).first()
                            if main_card:
                                main_card.is_taken = True
                                main_card.reserved_by = bot_user.id
                                main_card.current_game_id = game_id

                            db.commit()

                            all_taken = db.query(PlayerCard).filter(
                                PlayerCard.game_id == game_id,
                                PlayerCard.bet_amount == fee
                            ).all()
                            taken_list = [c.card_number for c in all_taken]

                            await self.safe_broadcast({
                                "type": "taken_cards_update",
                                "bet_amount": fee,
                                "taken_cards": taken_list
                            })

                            await asyncio.sleep(random.uniform(0.05, 0.15))

            print(f"🤖 QUICK BIRR Auto-bought bot cards completed for Game ID {game_id}.")
        except Exception as e:
            if db:
                db.rollback()
            print(f"❌ Error in auto_buy_bot_cards: {e}")
        finally:
            if db:
                db.close()

    async def safe_broadcast(self, payload):
        try:
            maybe = manager.broadcast(payload)
            if inspect.isawaitable(maybe):
                await maybe
            return True
        except Exception as e:
            print(f"❌ safe_broadcast error: {e}")
            return False

    async def start_game(self):
        if self.running:
            return

        self.running = True
        print("🎯 QUICK BIRR Bingo Game Engine ጀምሯል...")

        # Ensure cards exist in Database
        db_init = SessionLocal()
        try:
            ensure_initial_cards_populated(db_init)
        finally:
            db_init.close()

        while self.running:
            db: Session = None
            saved_game_id = None
            game_display_no = "0"
            try:
                db = SessionLocal()
                settings = db.query(Setting).first()

                countdown_seconds = 60
                draw_interval = settings.draw_interval if (settings and hasattr(settings, 'draw_interval')) else 4.0

                game = Game(
                    status="running",
                    started_at=datetime.now(timezone.utc),
                    taken_cards="[]",
                    drawn_balls="[]"
                )
                db.add(game)
                db.commit()
                db.refresh(game)
                
                saved_game_id = game.id
                game_display_no = str(100000 + saved_game_id)
                db.close()

                asyncio.create_task(self.auto_buy_bot_cards(saved_game_id))
                
                has_bought_cards = await self.countdown(countdown_seconds, game_display_no, saved_game_id)

                if self.running and has_bought_cards:
                    await self.draw_numbers(draw_interval, game_display_no, saved_game_id)
                else:
                    db = SessionLocal()
                    game_record = db.query(Game).filter(Game.id == saved_game_id).first()
                    if game_record:
                        game_record.status = "cancelled"
                        db.commit()
                    db.close()

                await asyncio.sleep(2)

            except Exception as e:
                print(f"❌ Error in game loop iteration: {e}")
                await asyncio.sleep(1)
            finally:
                if saved_game_id:
                    db_cleanup = SessionLocal()
                    try:
                        db_cleanup.query(Card).filter(Card.current_game_id == saved_game_id).update({
                            Card.is_taken: False, 
                            Card.reserved_by: None, 
                            Card.current_game_id: None
                        })
                        db_cleanup.commit()
                    except Exception as e:
                        print(f"❌ Error resetting context assets: {e}")
                    finally:
                        db_cleanup.close()

    async def countdown(self, seconds, game_display_no, saved_game_id):
        while seconds >= 0 and self.running:
            current_taken_list = []
            comm_percent = 20.0
            player_counts = {fee: 0 for fee in SUPPORTED_FEES}
            total_players_all_rooms = 0
            
            db: Session = None
            try:
                db = SessionLocal()
                taken_cards = db.query(Card.card_number).filter(Card.is_taken == True).all()
                current_taken_list = [c[0] for c in taken_cards]

                for fee in SUPPORTED_FEES:
                    count = db.query(PlayerCard).filter(
                        PlayerCard.game_id == saved_game_id, 
                        PlayerCard.bet_amount == fee
                    ).count()
                    player_counts[fee] = count

                if saved_game_id:
                    game_record = db.query(Game).filter(Game.id == saved_game_id).first()
                    if game_record:
                        game_record.taken_cards = json.dumps(current_taken_list)
                        db.commit()
            except Exception as e:
                print(f"❌ Countdown error: {e}")
            finally:
                if db:
                    db.close()

            derash_amounts = {}
            for fee, count in player_counts.items():
                total_players_all_rooms += count
                total_pool = count * fee
                derash_ratio = (100.0 - comm_percent) / 100.0
                derash_amounts[str(int(fee))] = int(total_pool * derash_ratio)

            payload = {
                "type": "countdown",
                "seconds": seconds,
                "time": seconds,
                "phase": "PICK",
                "game_no": game_display_no,
                "game_id": saved_game_id,
                "taken_cards": current_taken_list,
                "derash_rooms": derash_amounts, 
                "player_counts": player_counts,
                "player_count": total_players_all_rooms
            }
            await self.safe_broadcast(payload)
            await asyncio.sleep(1)
            seconds -= 1
            
        return True

    # =========================================================
    # 1-75 BALL DRAWING & WINNER ANNOUNCEMENT ENGINE
    # =========================================================

    async def draw_numbers(self, interval, game_display_no, saved_game_id):
        if not saved_game_id:
            return

        draw_interval = max(4.0, float(interval))
        numbers = list(range(1, 76))
        random.shuffle(numbers)
        self.called_numbers = []

        db: Session = None
        try:
            db = SessionLocal()
            bought_cards = {}
            for pc in db.query(PlayerCard).filter(PlayerCard.game_id == saved_game_id).all():
                bought_cards[pc.card_number] = {"user_id": pc.user_id, "bet_amount": pc.bet_amount}

            all_1000_cards = {}
            for c in db.query(Card).all():
                card_data = json.loads(c.data) if isinstance(c.data, str) else c.data
                all_1000_cards[str(c.card_number)] = card_data

            settings = db.query(Setting).first()
            comm_percent = settings.game_commission_percent if (settings and hasattr(settings, 'game_commission_percent')) else 20.0
            target_house_wins = settings.house_win_ratio if (settings and hasattr(settings, 'house_win_ratio')) else 3

            pools_by_fee = {}
            derash_by_fee = {}
            active_rooms = []
            
            for fee in SUPPORTED_FEES:
                count = sum(1 for c in bought_cards.values() if c["bet_amount"] == fee)
                pools_by_fee[fee] = count * fee
                derash_by_fee[str(int(fee))] = int(pools_by_fee[fee] * ((100.0 - comm_percent) / 100.0))
                if count > 0:
                    active_rooms.append(fee)

            room_status = {}
            if target_house_wins == 0:
                for fee in SUPPORTED_FEES:
                    room_status[fee] = "ALLOW_PLAYER"
                max_draw_balls = 75 
            else:
                for fee in SUPPORTED_FEES:
                    if self.house_counters.get(fee, 0) >= target_house_wins:
                        room_status[fee] = "ALLOW_PLAYER"
                    else:
                        room_status[fee] = "FORCE_HOUSE"

                max_draw_balls = random.randint(13, 16)

            await self.safe_broadcast({
                "type": "phase_change",
                "phase": "DRAW",
                "game_no": game_display_no,
                "derash_rooms": derash_by_fee
            })

            call_count = 0
            remaining_numbers = list(numbers)

            while remaining_numbers and self.running:
                number = remaining_numbers.pop(0)
                call_count += 1
                self.called_numbers.append(number)

                game_record = db.query(Game).filter(Game.id == saved_game_id).first()
                if game_record:
                    game_record.drawn_balls = json.dumps(self.called_numbers)
                    db.commit()

                letter = "B" if number <= 15 else "I" if number <= 30 else "N" if number <= 45 else "G" if number <= 60 else "O"

                await self.safe_broadcast({
                   "type": "ball",
                   "letter": letter,
                   "number": number,
                   "label": f"{letter}{number}",
                   "call_count": call_count,
                   "game_no": game_display_no,
                   "derash_rooms": derash_by_fee
                })

                result = self.process_drawn_ball_and_check_winner_v3(
                    db, saved_game_id, self.called_numbers, pools_by_fee, bought_cards, all_1000_cards, room_status
                )

                if result["status"] == "WINNER_FOUND":
                    winners_list = result["winners"]
                    bot_user = self.get_bot_user(db)
                    
                    for w in winners_list:
                        fee = w["bet_amount"]
                        if w["winner_id"] != bot_user.id:
                            self.house_counters[fee] = 0

                    winners_data = []
                    raw_winners_to_save = []
                    for w in winners_list:
                        if w["winner_id"] == bot_user.id:
                            telegram_name = random.choice(BOT_NAMES)
                            phone_number = random.choice(BOT_PHONE_NUMBERS)
                        else:
                            user_record = db.query(User).filter(User.id == w["winner_id"]).first()
                            telegram_name = user_record.telegram_username if user_record and user_record.telegram_username else f"user_{w['winner_id']}"
                            phone_number = "አልተመዘገበም"

                        winner_payload = {
                            "winner_id": w["winner_id"],
                            "telegram_name": telegram_name,
                            "winner_name": telegram_name,
                            "phone_number": phone_number,
                            "card_number": w["card_number"],
                            "winning_card_number": w["card_number"],
                            "room_fee": w["bet_amount"],
                            "prize": round(w["prize_share"], 2),
                            "winning_numbers": w["winning_numbers"],
                            "card_numbers": w["card_numbers"],
                            "winning_reason": w["winning_pattern"]
                        }
                        winners_data.append(winner_payload)
                        raw_winners_to_save.append(winner_payload)

                    game_record = db.query(Game).filter(Game.id == saved_game_id).first()
                    if game_record:
                        game_record.winners_info = json.dumps(raw_winners_to_save)
                        db.commit()

                    primary_winner = winners_data[0]
                    display_winner_name = primary_winner["telegram_name"]

                    await self.safe_broadcast({
                        "type": "game_over",
                        "status": "WINNER_FOUND",
                        "result": "BINGO",
                        "winner_name": display_winner_name,
                        "telegram_name": primary_winner["telegram_name"],
                        "phone_number": primary_winner["phone_number"],
                        "winning_card": primary_winner["card_number"],
                        "prize": primary_winner["prize"],
                        "room_fee": primary_winner["room_fee"],
                        "message": f"🎉 አሸናፊ፦ {display_winner_name} (ካርቴላ #{primary_winner['card_number']})!",
                        "card_number": primary_winner["card_number"],
                        "winner_id": primary_winner["winner_id"],
                        "winning_numbers": primary_winner["winning_numbers"], 
                        "card_numbers": primary_winner["card_numbers"],       
                        "winning_reason": primary_winner["winning_reason"],
                        "winners": winners_data
                    })
                    break

                if call_count >= max_draw_balls and target_house_wins > 0:
                    bot_win_info = self.find_best_bot_trigger_ball(bought_cards, all_1000_cards, self.called_numbers, remaining_numbers)
                    if bot_win_info:
                        trigger_ball = bot_win_info["trigger_ball"]
                        remaining_numbers.remove(trigger_ball)
                        
                        call_count += 1
                        self.called_numbers.append(trigger_ball)
                        
                        t_letter = "B" if trigger_ball <= 15 else "I" if trigger_ball <= 30 else "N" if trigger_ball <= 45 else "G" if trigger_ball <= 60 else "O"
                        await self.safe_broadcast({
                           "type": "ball",
                           "letter": t_letter,
                           "number": trigger_ball,
                           "label": f"{t_letter}{trigger_ball}",
                           "call_count": call_count,
                           "game_no": game_display_no,
                           "derash_rooms": derash_by_fee
                        })
                        await asyncio.sleep(1.0)

                        bot_user = self.get_bot_user(db)
                        bot_winners_list = []
                        for fee in active_rooms:
                            self.house_counters[fee] = self.house_counters.get(fee, 0) + 1
                            winner_name = random.choice(BOT_NAMES)
                            bot_phone = random.choice(BOT_PHONE_NUMBERS)
                            bot_prize_display = derash_by_fee.get(str(int(fee)), 0)

                            bot_winners_list.append({
                                "winner_id": bot_user.id,
                                "telegram_name": winner_name,
                                "winner_name": winner_name,
                                "phone_number": bot_phone,
                                "card_number": bot_win_info["card_number"],
                                "winning_card_number": bot_win_info["card_number"],
                                "room_fee": fee,
                                "prize": round(float(bot_prize_display), 2),
                                "winning_numbers": bot_win_info["winning_numbers"],
                                "card_numbers": bot_win_info["card_numbers"],
                                "winning_reason": bot_win_info["winning_pattern"]
                            })

                        game_record = db.query(Game).filter(Game.id == saved_game_id).first()
                        if game_record:
                            game_record.drawn_balls = json.dumps(self.called_numbers)
                            game_record.winners_info = json.dumps(bot_winners_list)
                            db.commit()

                        primary_bot = bot_winners_list[0]
                        self.distribute_multi_room_prize(db, saved_game_id, pools_by_fee, winner_user_id=None, winning_card=bot_win_info["card_number"])

                        await self.safe_broadcast({
                            "type": "game_over",
                            "status": "WINNER_FOUND",
                            "result": "BINGO",
                            "winner_name": primary_bot["telegram_name"],
                            "telegram_name": primary_bot["telegram_name"],
                            "phone_number": primary_bot["phone_number"],
                            "winning_card": primary_bot["card_number"],
                            "prize": primary_bot["prize"],
                            "message": f"🎉 አሸናፊ፦ {primary_bot['telegram_name']} (ካርቴላ #{primary_bot['card_number']})!",
                            "card_number": primary_bot["card_number"],
                            "winner_id": primary_bot["winner_id"],
                            "winning_numbers": bot_win_info["winning_numbers"],
                            "card_numbers": bot_win_info["card_numbers"],
                            "winning_reason": bot_win_info["winning_pattern"],
                            "winners": bot_winners_list
                        })
                        break

                await asyncio.sleep(draw_interval)

        except Exception as e:
            print(f"❌ Error in draw_numbers execution: {e}")
        finally:
            if db:
                db.close()

    # =========================================================
    # 5x5 BINGO PATTERN CHECKER LOGIC
    # =========================================================

    def check_bingo_patterns(self, matrix, drawn_balls):
        if not matrix or len(matrix) != 5 or any(len(row) != 5 for row in matrix):
            return False, [], ""

        drawn_set = set(drawn_balls)
        drawn_set.add("FREE")
        drawn_set.add(None)

        # 1. Horizontal Rows
        for r in range(5):
            if all(matrix[r][c] in drawn_set for c in range(5)):
                return True, [matrix[r][c] for c in range(5)], "Horizontal Row"
        
        # 2. Vertical Columns
        for c in range(5):
            if all(matrix[r][c] in drawn_set for r in range(5)):
                return True, [matrix[r][c] for r in range(5)], "Vertical Column"
        
        # 3. Diagonal Down
        if all(matrix[i][i] in drawn_set for i in range(5)):
            return True, [matrix[i][i] for i in range(5)], "Diagonal Down"
        
        # 4. Diagonal Up
        if all(matrix[i][4 - i] in drawn_set for i in range(5)):
            return True, [matrix[i][4 - i] for i in range(5)], "Diagonal Up"
        
        # 5. 4 Corners
        corners = [(0, 0), (0, 4), (4, 0), (4, 4)]
        if all(matrix[r][c] in drawn_set for r, c in corners):
            return True, [matrix[r][c] for r, c in corners], "4 Corners"

        return False, [], ""

    def find_best_bot_trigger_ball(self, bought_cards, all_1000_cards, current_drawn_balls, remaining_numbers):
        db = SessionLocal()
        bot_user = self.get_bot_user(db)
        db.close()

        bot_cards = [card_num for card_num, info in bought_cards.items() if info["user_id"] == bot_user.id]
        if not bot_cards:
            bot_cards = list(all_1000_cards.keys())

        drawn_set = set(current_drawn_balls)
        drawn_set.add("FREE")
        drawn_set.add(None)

        for c_num in bot_cards:
            card_matrix = all_1000_cards.get(str(c_num))
            if not card_matrix or len(card_matrix) != 5:
                continue

            patterns = []
            for r in range(5):
                patterns.append(([card_matrix[r][c] for c in range(5)], f"Horizontal Row {r+1}"))
            for c in range(5):
                patterns.append(([card_matrix[r][c] for r in range(5)], f"Vertical Column {c+1}"))
            patterns.append(([card_matrix[i][i] for i in range(5)], "Diagonal Down"))
            patterns.append(([card_matrix[i][4-i] for i in range(5)], "Diagonal Up"))
            corners = [(0, 0), (0, 4), (4, 0), (4, 4)]
            patterns.append(([card_matrix[r][c] for r, c in corners], "4 Corners"))

            for pat_nums, pat_name in patterns:
                missing = [n for n in pat_nums if n not in drawn_set]
                if len(missing) == 1 and missing[0] in remaining_numbers:
                    trigger = missing[0]
                    flat_card = [item for sublist in card_matrix for item in sublist]
                    win_nums = [n for n in pat_nums if n and n != "FREE"]
                    return {
                        "card_number": int(c_num),
                        "trigger_ball": trigger,
                        "winning_numbers": win_nums,
                        "card_numbers": flat_card,
                        "winning_pattern": pat_name
                    }
        
        fallback_card = int(random.choice(bot_cards))
        fallback_matrix = all_1000_cards.get(str(fallback_card), [[0]*5 for _ in range(5)])
        fallback_flat = [item for sublist in fallback_matrix for item in sublist] if len(fallback_matrix) == 5 else []
        fallback_trigger = remaining_numbers[0]
        
        return {
            "card_number": fallback_card,
            "trigger_ball": fallback_trigger,
            "winning_numbers": [],
            "card_numbers": fallback_flat,
            "winning_pattern": "ቢንጎ"
        }

    def process_drawn_ball_and_check_winner_v3(self, db, game_id, current_drawn_balls, pools_by_fee, bought_cards, all_1000_cards, room_status):
        bot_user = self.get_bot_user(db)
        detected_winners = []
        
        for card_num, card_info in bought_cards.items():
            fee = card_info["bet_amount"]

            if room_status.get(fee) == "FORCE_HOUSE" and card_info["user_id"] != bot_user.id:
                continue

            card_matrix = all_1000_cards.get(str(card_num))
            if card_matrix:
                is_win, win_nums, pattern = self.check_bingo_patterns(card_matrix, current_drawn_balls)
                if is_win:
                    flat_card = [item for sublist in card_matrix for item in sublist]
                    detected_winners.append({
                        "winner_id": card_info["user_id"],
                        "card_number": card_num,
                        "bet_amount": fee,
                        "winning_numbers": win_nums,
                        "card_numbers": flat_card,
                        "winning_pattern": pattern
                    })
        
        if detected_winners:
            room_winner_counts = {}
            for w in detected_winners:
                f = w["bet_amount"]
                room_winner_counts[f] = room_winner_counts.get(f, 0) + 1
            
            settings = db.query(Setting).first()
            comm_percent = settings.game_commission_percent if (settings and hasattr(settings, 'game_commission_percent')) else 20.0
            
            for w in detected_winners:
                f = w["bet_amount"]
                room_total_pool = pools_by_fee.get(f, 0)
                
                admin_commission = room_total_pool * (comm_percent / 100.0)
                total_room_player_prize = room_total_pool - admin_commission 
                
                winners_in_this_room = room_winner_counts[f]
                w["prize_share"] = total_room_player_prize / winners_in_this_room

            self.distribute_multi_room_prize_v2(db, game_id, pools_by_fee, detected_winners)
            
            return {
                "status": "WINNER_FOUND",
                "winners": detected_winners
            }
            
        return {"status": "CONTINUE"}

    def distribute_multi_room_prize_v2(self, db, game_id, pools_by_fee, detected_winners):
        settings = db.query(Setting).first()
        comm_percent = settings.game_commission_percent if (settings and hasattr(settings, 'game_commission_percent')) else 20.0

        admin_stats = db.query(AdminStats).first()
        if not admin_stats:
            admin_stats = AdminStats(house_balance=0.0, total_commission=0.0)
            db.add(admin_stats)

        bot_user = self.get_bot_user(db)

        game = db.query(Game).filter(Game.id == game_id).first()
        if game:
            game.status = "finished"
            game.winning_card = ",".join([str(w["card_number"]) for w in detected_winners])
            game.finished_at = datetime.now(timezone.utc)
            game.winner_id = detected_winners[0]["winner_id"]
            game.prize = sum([w["prize_share"] for w in detected_winners])

        winning_fees = set([w["bet_amount"] for w in detected_winners])
        
        for w in detected_winners:
            if w["winner_id"] == bot_user.id:
                admin_stats.house_balance += w["prize_share"]
            else:
                process_game_win(
                    db=db,
                    user_id=w["winner_id"],
                    amount=w["prize_share"],
                    game_name="Bingo"
                )
                
        for fee, room_pool in pools_by_fee.items():
            if room_pool <= 0:
                continue
            admin_commission = room_pool * (comm_percent / 100.0)
            admin_stats.total_commission += admin_commission

            if fee not in winning_fees:
                admin_stats.house_balance += (room_pool - admin_commission)

        try:
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"❌ Error committing prize distribution: {e}")

    def distribute_multi_room_prize(self, db, game_id, pools_by_fee, winner_user_id=None, winning_card=None, winning_fee=None):
        settings = db.query(Setting).first()
        comm_percent = settings.game_commission_percent if (settings and hasattr(settings, 'game_commission_percent')) else 20.0

        admin_stats = db.query(AdminStats).first()
        if not admin_stats:
            admin_stats = AdminStats(house_balance=0.0, total_commission=0.0)
            db.add(admin_stats)

        game = db.query(Game).filter(Game.id == game_id).first()
        if game:
            game.status = "finished"
            game.winning_card = str(winning_card)
            game.finished_at = datetime.now(timezone.utc)

        for fee, total_pool_money in pools_by_fee.items():
            if total_pool_money <= 0:
                continue

            admin_commission = total_pool_money * (comm_percent / 100.0)
            player_prize = total_pool_money - admin_commission

            if winner_user_id and fee == winning_fee:
                admin_stats.total_commission += admin_commission
                process_game_win(
                    db=db,
                    user_id=winner_user_id,
                    amount=player_prize,
                    game_name="Bingo"
                )
                if game:
                    game.winner_id = winner_user_id
                    game.prize = player_prize
            else:
                admin_stats.total_commission += admin_commission
                admin_stats.house_balance += player_prize
                
                if not winner_user_id and game:
                    game.winner_id = 0
                    game.prize = sum(pools_by_fee.values())

        try:
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"❌ Error committing prize distribution: {e}")

engine = GameEngine()

# =========================================================
# WEBSOCKET & BINGO API ENDPOINTS
# =========================================================

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@router.post("/buy-card")
async def buy_bingo_card(user_id: int, card_number: int, game_id: int, db: Session = Depends(get_db)):
    """
    ከ Central Wallet 10 ETB ቀንሶ የተመረጠውን 1-1000 ካርቴላ ይገዛል።
    በተመሳሳይ ሰዓት ለሁሉም ተጫዋቾች የተያዘውን ካርድ በ WebSocket ያሰራጫል።
    """
    if not (1 <= card_number <= CARD_COUNT_LIMIT):
        raise HTTPException(status_code=400, detail="Card number must be between 1 and 1000.")

    # Check if game is active
    game = db.query(Game).filter(Game.id == game_id, Game.status.in_(["running", "waiting"])).first()
    if not game:
        raise HTTPException(status_code=400, detail="የነቃ ጨዋታ አልተገኘም!")

    # Check if card is already bought
    existing = db.query(PlayerCard).filter(
        PlayerCard.game_id == game_id,
        PlayerCard.card_number == card_number
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="ይህ ካርቴላ ቀደሞ በሌላ ተጫዋች ተይዟል!")

    # Deduct 10 ETB from User Wallet
    try:
        user = process_game_stake(
            db=db,
            user_id=user_id,
            amount=10.0,
            game_name="Bingo"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Record Player Card
    p_card = PlayerCard(
        game_id=game_id,
        user_id=user_id,
        card_number=card_number,
        bet_amount=10.0
    )
    db.add(p_card)

    # Reserve Main Card
    main_card = db.query(Card).filter(Card.card_number == card_number).first()
    if main_card:
        main_card.is_taken = True
        main_card.reserved_by = user_id
        main_card.current_game_id = game_id

    db.commit()

    # Get updated taken cards list
    all_taken = db.query(PlayerCard).filter(PlayerCard.game_id == game_id).all()
    taken_list = [c.card_number for c in all_taken]

    # Realtime Broadcast to connected clients
    await engine.safe_broadcast({
        "type": "taken_cards_update",
        "bet_amount": 10.0,
        "taken_cards": taken_list
    })

    return {
        "success": True,
        "message": f"ካርቴላ #{card_number} በ 10 ETB ተገዝቷል!",
        "card_number": card_number,
        "new_balance": round(user.balance, 2)
    }
