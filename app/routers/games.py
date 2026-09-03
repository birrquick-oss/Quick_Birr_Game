import random
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Game, User, PlayerCard

router = APIRouter(
    prefix="/api/games",
    tags=["Games"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/current")
def current_game(
    telegram_id: str = Query(...),
    db: Session = Depends(get_db)
):
    BET_AMOUNT = 10.0  # 🎯 ለአዲሱ ፕሮጀክት 10 ብር ብቻ ነው

    # 1. የተጫዋቹን መረጃ ከዳታቤዝ መፈለግ (ከሌለ መመዝገብ)
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        user = User(
            telegram_id=telegram_id,
            telegram_name=f"User_{telegram_id}",
            first_name="Player",
            balance=0.0,
            wallet=0.0,
            gift_coin=0.0,
            is_admin=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 2. የመጨረሻውን የነቃ ጨዋታ (Active Game) መፈለግ
    game = db.query(Game).filter(Game.status.in_(["running", "waiting"])).order_by(Game.id.desc()).first()

    # 💡 ጨዋታ ከሌለ አዲስ መፍጠር
    if not game:
        game = Game(
            game_no=str(random.randint(100000, 199999)),
            status="running",
            ticket_price=BET_AMOUNT,
            total_players=0,
            total_pool=0.0
        )
        db.add(game)
        db.commit()
        db.refresh(game)

    # 3. በ 10 ብር ክፍል የተገዙ ጠቅላላ የካርዶች ብዛት
    room_cards_bought = db.query(PlayerCard).filter(
        PlayerCard.game_id == game.id,
        PlayerCard.bet_amount == BET_AMOUNT
    ).count()

    # 4. ጠቅላላ የተሰበሰበው ብር (Pool) እና አሸናፊው የሚደርሰው (80%)
    total_pool_money = room_cards_bought * BET_AMOUNT
    derash_money = total_pool_money * 0.80

    # 5. መረጃውን መመለስ
    return {
        "success": True,
        "game_id": game.id,
        "game_no": game.game_no,
        "status": game.status,
        "bet": BET_AMOUNT,
        "active_game": 1 if game.status in ["running", "waiting"] else 0,
        "wallet": user.balance,
        "balance": user.balance,
        "gift": user.gift_coin,
        "players": room_cards_bought,
        "derash": round(derash_money, 2),
        "total_pool": total_pool_money
    }
