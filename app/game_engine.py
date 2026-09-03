import random
import asyncio
import json
import inspect
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.websocket_manager import manager
from app.database import SessionLocal
from app.models import Game, Setting, User, AdminStats, PlayerCard, Card

BOT_NAMES = [
    "user_45456", "user_MUTD", "user_Dereje16", "user_65788", "user_Gadissa", "user_43688",  
    "user_89856", "user_56488", "user_Finfine", "user_88786", "user_Abeti", "user_54321",
    "user_Shegaw16", "user_78646", "user_Abenu888", "user_56787", "user_Berihun19", "user_32743",
    "user_Kaka", "user_Forever", "user_Tarekegni", "user_77633", "user_Chuchu", "user_55894",
    "user_36648", "user_93121", "user_Temu19", "user_48539", "user_የማሪያምልጅ21", "user_89175",
    "user_53929", "user_79348", "user_Abdissa", "user_91976", "user_Obssa21", "user_Degu22",
    "user_48271", "user_Bekele", "user_73924", "user_Miki22", "user_74583", "user_Habte",
    "user_92746", "user_Sami19", "user_35482", "user_Eyob", "user_81635", "user_Lemma17",
    "user_56391", "user_Nati", "user_74826", "user_Yonas21", "user_39157", "user_Mesfin",
    "user_68432", "user_Dani", "user_82519", "user_Amare16", "user_47683", "user_Fikru",
    "user_95317", "user_Solomon", "user_63845", "user_Tesfa19", "user_21764", "user_Kebede",
    "user_87431", "user_Robi22", "user_52689", "user_Mulatu", "user_76352", "user_Teddy18",
    "user_41976", "user_Girma", "user_68524", "user_Yared20", "user_93168", "user_Bini",
    "user_57243", "user_Amanuel19", "user_84617", "user_Sisay", "user_31582", "user_Bereket21",
    "user_76439", "user_Mered", "user_52816", "user_Abel17", "user_69354", "user_Freedom",
    "user_81726", "user_ብርሃን21", "user_45938", "user_ሀገሬ", "user_72615", "user_Eyou19"
]

BOT_PHONE_NUMBERS = [
    "2519****2244", "2519****3478", "2519****5589", "2519****8990", "2519****0901", "አልተመዘገበም",
    "2519****6702", "2519****2313", "2519****4424", "2519****4535", "2519****8246", "አልተመዘገበም",
    "2517****5444", "2517****3478", "2517****4589", "2517****9555", "2517****8685", "አልተመዘገበም",
    "2519****2149", "2519****6803", "2519****9881", "2519****6686", "2519****4282", "አልተመዘገበም",
    "2517****1141", "2517****1211", "2519****7661", "2519****7464", "2519****2676", "አልተመዘገበም",
    "2519****6389", "2519****5141", "2519****6395", "2519****0403", "2519****9365", "አልተመዘገበም",  
    "2519****4821", "2519****7364", "2519****1598", "2519****6043", "2519****9275", "አልተመዘገበም",
    "2517****3816", "2517****7452", "2517****2094", "2517****8631", "2517****5147", "አልተመዘገበም",
    "2519****6713", "2519****4286", "2519****9052", "2519****3178", "2519****6549", "አልተመዘገበም",
    "2517****1468", "2517****5931", "2517****8274", "2517****3605", "2517****9182", "አልተመዘገበም",
    "2519****2457", "2519****6819", "2519****5036", "2519****7742", "2519****1395", "አልተመዘገበም",
    "2517****4263", "2517****8507", "2519****2914", "2519****6378", "2519****9046", "አልተመዘገበም",
    "2519****5182", "2519****7436", "2517****1659", "2517****4827", "2519****8305", "አልተመዘገበም",
    "2519****3761", "2517****6294", "2519****8147", "2517****2508", "2519****5473", "አልተመዘገበም",
]

# አዲሱ ቢንጎ የ 10 ብር ክፍል ብቻ ነው የሚጠቀመው
SUPPORTED_FEES = [10.0]
BOT_ALLOWED_FEES = [10.0]

class GameEngine:

    def __init__(self):
        self.running = False
        self.called_numbers = []
        self.current_game = None
        self.house_counters = {10.0: 0}

    def get_bot_user(self, db: Session):
        bot = db.query(User).filter(User.telegram_id == "BOT_VIRTUAL_PLAYER").first()
        if not bot:
            default_bot_name = random.choice(BOT_NAMES)
            bot = User(
                telegram_id="BOT_VIRTUAL_PLAYER",
                telegram_name=default_bot_name,
                first_name=default_bot_name,
                balance=9999999.0,
                wallet=0.0,
                gift_coin=0.0
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

        # ከጠዋቱ 12:00 እስከ ቀኑ 7:00 (ከ6:00 እስከ 12:59)
        if 6 <= hour < 13:
            return random.randint(50, 100)

        # ከቀኑ 7:00 እስከ ሌሊቱ 6:00 (ከ13:00 እስከ 23:59)
        elif 13 <= hour <= 23:
            return random.randint(100, 150)

        # ከሌሊቱ 6:00 እስከ ሌሊቱ 9:00 (ከ0:00 እስከ 2:59)
        elif 0 <= hour < 3:
            return random.randint(40, 80)

        # ከሌሊቱ 9:00 እስከ ጠዋቱ 12:00 (ከ3:00 እስከ 5:59)
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
                    # 1-1000 ካርቴላዎች እንዲሸፍን ተደርጓል
                    available_numbers = [num for num in range(1, 1001) if num not in taken_numbers]
                    if available_numbers:
                        cards_to_buy_count = min(needed, len(available_numbers))
                        cards_to_buy = random.sample(available_numbers, cards_to_buy_count)
                        
                        for c_num in cards_to_buy:
                            active_check = db.query(Game).filter(Game.id == game_id, Game.status.in_(["running", "waiting"])).first()
                            if not active_check:
                                break

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

            print(f"🤖 Fast auto-bought bot cards completed for Game ID {game_id}.")
        except Exception as e:
            if db:
                db.rollback()
            print(f"❌ Error in auto_buy_bot_cards: {e}")
        finally:
            if db:
                db.close()

    async def safe_broadcast(self, payload):
        try:
            preview = payload if isinstance(payload, dict) else str(payload)
            if isinstance(preview, dict):
                preview = {k: preview.get(k) for k in list(preview)[:5]}
            
            maybe = None
            try:
                maybe = manager.broadcast(payload)
            except Exception as e:
                print(f"❌ manager.broadcast raised synchronously: {e}")

            try:
                if inspect.isawaitable(maybe):
                    await maybe
                    return True
                if callable(maybe):
                    maybe()
                    return True
            except Exception as e:
                print(f"❌ Error during broadcast invocation: {e}")

            sent = False
            for attr in ("connections", "active_connections", "websockets"):
                conns = getattr(manager, attr, None)
                if conns:
                    for ws in list(conns):
                        try:
                            await ws.send_json(payload)
                            sent = True
                        except Exception as e:
                            print(f"❌ Failed to send to socket: {e}")
                    if sent:
                        return True
            return False
        except Exception as e:
            print(f"❌ safe_broadcast unexpected error: {e}")
            return False

    async def start_game(self):
        if self.running:
            return

        self.running = True
        print("🎯 የቢንጎ ጨዋታ ሞተር ስራ ጀምሯል...")

        while self.running:
            db: Session = None
            saved_game_id = None
            game_display_no = "0"
            try:
                db = SessionLocal()
                settings = db.query(Setting).first()

                # ቆጣሪው ወደ 60 ሰከንድ ተቀይሯል
                countdown_seconds = settings.countdown_seconds if (settings and hasattr(settings, 'countdown_seconds')) else 60
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
        has_bought_cards = True
        
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
                
                settings = db.query(Setting).first()
                if settings and hasattr(settings, 'game_commission_percent'):
                    comm_percent = settings.game_commission_percent

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
                print(f"❌ Error during countdown DB update: {e}")
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
            
        return has_bought_cards

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

            # 1-1000 ካርቴላዎችን ይጭናል
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

            winner_detected = False

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
                            telegram_name = user_record.telegram_name if user_record and user_record.telegram_name else f"user_{w['winner_id']}"
                            
                            if user_record and hasattr(user_record, 'phone_number') and user_record.phone_number:
                                phone_number = user_record.phone_number
                            else:
                                phone_number = "ስልክ አልተመዘገበም"
                        
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
                    winner_detected = True
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
                        winner_detected = True
                        break

                await asyncio.sleep(draw_interval)

        except Exception as e:
            print(f"❌ Error in draw_numbers execution: {e}")
        finally:
            if db:
                db.close()

    def check_bingo_patterns(self, matrix, drawn_balls):
        if not matrix or len(matrix) != 5 or any(len(row) != 5 for row in matrix):
            return False, [], ""

        drawn_set = set(drawn_balls)
        drawn_set.add("FREE")
        drawn_set.add(None)

        for r in range(5):
            if all(matrix[r][c] in drawn_set for c in range(5)):
                return True, [matrix[r][c] for c in range(5)], "Horizontal Row"
        for c in range(5):
            if all(matrix[r][c] in drawn_set for r in range(5)):
                return True, [matrix[r][c] for r in range(5)], "Vertical Column"
        if all(matrix[i][i] in drawn_set for i in range(5)):
            return True, [matrix[i][i] for i in range(5)], "Diagonal Down"
        if all(matrix[i][4 - i] in drawn_set for i in range(5)):
            return True, [matrix[i][4 - i] for i in range(5)], "Diagonal Up"
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
                patterns.append(([card_matrix[i][c] for i in range(5)], f"Vertical Column {c+1}"))
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
                user = db.query(User).filter(User.id == w["winner_id"]).first()
                if user:
                    user.balance += w["prize_share"]
                
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
                user = db.query(User).filter(User.id == winner_user_id).first()
                if user:
                    user.balance += player_prize
                
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
