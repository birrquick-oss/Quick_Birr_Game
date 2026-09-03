import json
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Card
from app.card_generator import generate_all_cards


def seed_cards():
    db: Session = SessionLocal()

    existing_count = db.query(Card).count()
    
    # 🎯 1000 ካርዶች አስቀድመው ከተፈጠሩ በድጋሚ አይፈጥርም
    if existing_count >= 1000:
        print(f"✅ {existing_count} cards already exist in the database.")
        db.close()
        return

    # 🔄 ከ 1000 ያነሰ ካርድ ካለ አሮጌዎቹን አጽድቶ አዲሶቹን 1000 ካርዶች ይፈጥራል
    if existing_count > 0:
        print(f"🔄 Found {existing_count} old cards. Re-seeding to 1000 cards...")
        db.query(Card).delete()
        db.commit()

    # 1000 ካርዶችን ማመንጨት
    cards = generate_all_cards(1000)

    for index, card in enumerate(cards, start=1):
        db.add(
            Card(
                card_number=index,
                data=json.dumps(card)
            )
        )

    db.commit()
    print(f"🎉 Successfully seeded {len(cards)} cards into the database!")
    db.close()


if __name__ == "__main__":
    seed_cards()
