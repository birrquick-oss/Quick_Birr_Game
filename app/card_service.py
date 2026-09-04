import json
from sqlalchemy.orm import Session
from app.models import Card

def get_card_by_number(db: Session, card_number: int):
    card = db.query(Card).filter(Card.card_number == card_number).first()
    if not card:
        return None
    
    return {
        "card_number": card.card_number,
        "matrix": json.loads(card.data) if isinstance(card.data, str) else card.data
    }
