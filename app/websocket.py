import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Game, PlayerCard
from app.websocket_manager import manager

router = APIRouter(tags=["WebSocket"])

BET_AMOUNT = 10.0

# 1. Frontend የሚጠቀመውን ሁለቱንም Path (/ws እና /ws/bingo) እንዲቀበል ተደርጓል
@router.websocket("/ws")
@router.websocket("/ws/bingo")
async def websocket_bingo_endpoint(websocket: WebSocket):
    # Origin እና Header ምንም ይሁን ምን Websocket ግንኙነቱን ይቀበላል
    await manager.connect(websocket)

    try:
        # DB Session ለጥያቄው ብቻ ከፍቶ ወዲያው ይዘጋል (Connection Leak እንዳይኖር)
        db: Session = SessionLocal()
        try:
            active_game = db.query(Game).filter(
                Game.status.in_(["running", "waiting"])
            ).order_by(Game.id.desc()).first()

            taken_cards = []
            if active_game:
                player_cards = db.query(PlayerCard).filter(
                    PlayerCard.game_id == active_game.id,
                    PlayerCard.bet_amount == BET_AMOUNT
                ).all()
                taken_cards = [pc.card_number for pc in player_cards]

            init_payload = {
                "type": "init_state",
                "game_id": active_game.id if active_game else None,
                "game_no": getattr(active_game, 'game_no', str(100000 + (active_game.id if active_game else 0))),
                "status": active_game.status if active_game else "waiting",
                "bet_amount": BET_AMOUNT,
                "taken_cards": taken_cards,
                "total_players": len(taken_cards),
                "derash": round(len(taken_cards) * BET_AMOUNT * 0.80, 2)
            }
            await websocket.send_text(json.dumps(init_payload))
        finally:
            db.close()

        # መልእክት ሲመጣ ብቻ ዳታቤዝ ከፍቶ መመለስ
        while True:
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)
                
                if data.get("action") == "get_taken_cards":
                    db_req: Session = SessionLocal()
                    try:
                        current_game = db_req.query(Game).filter(
                            Game.status.in_(["running", "waiting"])
                        ).order_by(Game.id.desc()).first()

                        current_taken = []
                        if current_game:
                            pcs = db_req.query(PlayerCard).filter(
                                PlayerCard.game_id == current_game.id,
                                PlayerCard.bet_amount == BET_AMOUNT
                            ).all()
                            current_taken = [p.card_number for p in pcs]

                        await websocket.send_text(json.dumps({
                            "type": "taken_cards_update",
                            "bet_amount": BET_AMOUNT,
                            "taken_cards": current_taken
                        }))
                    finally:
                        db_req.close()

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"⚠️ WebSocket connection error: {e}")
        manager.disconnect(websocket)
