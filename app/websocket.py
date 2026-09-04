import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Game, PlayerCard, User
from app.websocket_manager import manager

router = APIRouter(tags=["WebSocket"])

BET_AMOUNT = 10.0  # 🎯 ለአዲሱ ፕሮጀክት 10 ብር ክፍል ብቻ


@router.websocket("/ws/bingo")
async def websocket_bingo_endpoint(websocket: WebSocket):
    """
    🌐 የቀጥታ ስርጭት የዌብሶኬት ግንኙነት፦
    ለ 10 ብር ክፍል የተያዙ ካርዶችን፣ የ 60 ሰከንድ ቆጣሪን እና የቀጥታ የዕጣ ቁጥሮችን ያስተላልፋል።
    """
    await manager.connect(websocket)
    db: Session = SessionLocal()

    try:
        # 1. አክቲቭ የሆነውን ጨዋታ መፈለግ
        active_game = db.query(Game).filter(
            Game.status.in_(["running", "waiting"])
        ).order_by(Game.id.desc()).first()

        # 2. በ 10 ብር ክፍል የተያዙ ካርዶችን ማውጣት
        taken_cards = []
        if active_game:
            player_cards = db.query(PlayerCard).filter(
                PlayerCard.game_id == active_game.id,
                PlayerCard.bet_amount == BET_AMOUNT
            ).all()
            taken_cards = [pc.card_number for pc in player_cards]

        # 3. አዲስ ለገባው ተጫዋች የመነሻ ሁኔታውን (Initial State) መላክ
        init_payload = {
            "type": "init_state",
            "game_id": active_game.id if active_game else None,
            "game_no": active_game.game_no if active_game else None,
            "status": active_game.status if active_game else "waiting",
            "bet_amount": BET_AMOUNT,
            "taken_cards": taken_cards,
            "total_players": len(taken_cards),
            "derash": round(len(taken_cards) * BET_AMOUNT * 0.80, 2)
        }
        await websocket.send_text(json.dumps(init_payload))

        # 4. ከተጫዋቹ የሚመጡ መልእክቶችን ማዳመጥ (Ping/Pong ወይም መረጃዎች)
        while True:
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)
                
                # የተያዙ ካርዶችን ጥያቄ ሲልክ
                if data.get("action") == "get_taken_cards":
                    current_game = db.query(Game).filter(
                        Game.status.in_(["running", "waiting"])
                    ).order_by(Game.id.desc()).first()

                    current_taken = []
                    if current_game:
                        pcs = db.query(PlayerCard).filter(
                            PlayerCard.game_id == current_game.id,
                            PlayerCard.bet_amount == BET_AMOUNT
                        ).all()
                        current_taken = [p.card_number for p in pcs]

                    await websocket.send_text(json.dumps({
                        "type": "taken_cards_update",
                        "bet_amount": BET_AMOUNT,
                        "taken_cards": current_taken
                    }))

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"⚠️ WebSocket connection error: {e}")
        manager.disconnect(websocket)
    finally:
        db.close()
