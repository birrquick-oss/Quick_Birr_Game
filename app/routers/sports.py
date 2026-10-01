import os
import uuid
import asyncio
import httpx
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import Session

from app.database import SessionLocal, Base, engine
from app.models import User, WalletTransaction

router = APIRouter(
    prefix="/api/sports",
    tags=["Sports Betting"]
)

# =========================================================
# DATABASE MODEL
# =========================================================

class SportsBet(Base):
    __tablename__ = "sports_bets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    telegram_id = Column(String(64), index=True, nullable=False)
    # match_id እና selection ረጅም Multi-Bet ማስተናገድ እንዲችሉ Text ተደርገዋል
    match_id = Column(Text, nullable=False)
    match_name = Column(String(550), nullable=False)
    selection = Column(Text, nullable=False)
    odds = Column(Float, nullable=False)
    stake = Column(Float, nullable=False)
    potential_payout = Column(Float, nullable=False)
    status = Column(String(32), default="pending")
    reference = Column(String(64), unique=True, index=True)
    created_at = Column(DateTime, server_default=func.now())

# ቴብሉ ዳታቤዝ ውስጥ ካልተፈጠረ አውቶማቲክ ይፈጠራል
Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class PlaceBetRequest(BaseModel):
    telegram_id: str
    match_id: str
    match_name: str
    selection: str
    odds: float = Field(gt=1.0)
    stake_amount: float = Field(gt=0)


MIN_STAKE = 10.0
ODDS_API_KEY = "e34df3461ec51a24ac019b49a3dbc6df"
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports"


# =========================================================
# GET ALL ACTIVE SOCCER LEAGUES
# =========================================================

@router.get("/leagues")
async def get_active_leagues():
    """በ The Odds API ላይ ያሉትን ሁሉንም ንቁ የእግር ኳስ ሊጎች ያመጣል"""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            url = f"{ODDS_API_URL}/?apiKey={ODDS_API_KEY}"
            response = await client.get(url)

            if response.status_code != 200:
                print(f"League Fetch Failed: Status {response.status_code}")
                return []

            all_sports = response.json()
            soccer_leagues = [
                {
                    "key": item["key"],
                    "title": item["title"],
                    "description": item.get("description", "")
                }
                for item in all_sports
                if item.get("group") == "Soccer" and item.get("active", False)
            ]
            return soccer_leagues

    except Exception as e:
        print("League Fetch Error:", e)
        return []


# =========================================================
# GET MATCHES (422 Error እንዳይመጣ ከታመኑ Markets ጋር የተስተካከለ)
# =========================================================

async def fetch_single_league_matches(client: httpx.AsyncClient, key: str) -> List[dict]:
    """ለአንድ ሊግ ብቻ ከ API ጨዋታዎችን ያመጣል"""
    # 422 Error እንዳይመጣ ሁልጊዜ የሚደገፉትን h2h እና totals ብቻ እንጠይቃለን
    url = f"{ODDS_API_URL}/{key}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h,totals"
    try:
        response = await client.get(url, timeout=12.0)
        if response.status_code != 200:
            print(f"Failed to fetch {key}, status: {response.status_code}")
            return []
        
        data = response.json()
        matches = []
        for match in data[:15]:
            h2h_m, totals_m = None, None

            for b in match.get("bookmakers", []):
                for m in b.get("markets", []):
                    k = m.get("key")
                    if k == "h2h" and not h2h_m: 
                        h2h_m = m
                    elif k == "totals" and not totals_m: 
                        totals_m = m

            home_win, draw, away_win = 1.0, 1.0, 1.0
            if h2h_m:
                for outcome in h2h_m.get("outcomes", []):
                    if outcome["name"] == match["home_team"]: 
                        home_win = outcome["price"]
                    elif outcome["name"] == match["away_team"]: 
                        away_win = outcome["price"]
                    elif outcome["name"].lower() == "draw": 
                        draw = outcome["price"]

            # Double Chance Odds በራሱ ቀመር ይሰላል (422 ኤረር እንዳይፈጥር)
            dc_1x = round(1 / ((1/home_win) + (1/draw)), 2) if home_win > 1 and draw > 1 else 1.20
            dc_12 = round(1 / ((1/home_win) + (1/away_win)), 2) if home_win > 1 and away_win > 1 else 1.25
            dc_x2 = round(1 / ((1/draw) + (1/away_win)), 2) if draw > 1 and away_win > 1 else 1.30

            totals_list = [{"name": o.get("name"), "point": o.get("point"), "price": o.get("price")} for o in totals_m.get("outcomes", [])] if totals_m else []

            matches.append({
                "id": match.get("id"),
                "league": key,
                "home_team": match.get("home_team"),
                "away_team": match.get("away_team"),
                "commence_time": match.get("commence_time"),
                "odds": {
                    "h2h": {"1": home_win, "X": draw, "2": away_win},
                    "double_chance": {"1X": dc_1x, "12": dc_12, "X2": dc_x2},
                    "totals": totals_list,
                    "spreads": []
                }
            })
        return matches
    except Exception as e:
        print(f"Error fetching {key}:", e)
        return []


@router.get("/matches/{sport_key}")
async def get_matches(sport_key: str):
    target_keys = [sport_key]
    if sport_key == "all":
        # ሁልጊዜ ንቁና አስተማማኝ የሆኑ ዋና ዋና ሊጎች
        target_keys = [
            "soccer_epl", 
            "soccer_spain_la_liga", 
            "soccer_germany_bundesliga", 
            "soccer_italy_serie_a", 
            "soccer_uefa_champs_league",
            "soccer_france_ligue_one"
        ]

    all_matches = []

    try:
        async with httpx.AsyncClient() as client:
            tasks = [fetch_single_league_matches(client, key) for key in target_keys]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for match_group in results:
                if isinstance(match_group, list):
                    all_matches.extend(match_group)

        return all_matches

    except Exception as e:
        print("API Matches Error:", e)
        return []


# =========================================================
# PLACE BET & MY BETS
# =========================================================

@router.post("/place-bet")
def place_bet(request: PlaceBetRequest, db: Session = Depends(get_db)):
    telegram_id = str(request.telegram_id).strip()
    stake = round(float(request.stake_amount), 2)
    odds = round(float(request.odds), 2)

    if stake < MIN_STAKE:
        raise HTTPException(status_code=400, detail=f"Minimum stake is {MIN_STAKE} ETB.")

    user = db.query(User).filter(User.telegram_id == telegram_id).with_for_update().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if round(float(user.balance or 0), 2) < stake:
        raise HTTPException(status_code=400, detail="Insufficient balance!")

    potential_win = round(stake * odds, 2)
    balance_after = round(float(user.balance) - stake, 2)
    user.balance = balance_after
    reference = f"SPORTS-{uuid.uuid4().hex[:16]}"

    stake_tx = WalletTransaction(
        user_id=user.id,
        transaction_type="game_stake_sports",
        amount=-stake,
        balance_after=balance_after,
        game="sports",
        reference=reference,
        description=f"Sports Bet ({request.match_name} - {request.selection} @ {odds})"
    )

    bet_rec = SportsBet(
        user_id=user.id,
        telegram_id=telegram_id,
        match_id=request.match_id,
        match_name=request.match_name,
        selection=request.selection,
        odds=odds,
        stake=stake,
        potential_payout=potential_win,
        status="pending",
        reference=reference
    )

    db.add(stake_tx)
    db.add(bet_rec)

    try:
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        print("Place Bet DB Error:", e)
        raise HTTPException(status_code=500, detail="Bet error.")

    return {
        "success": True,
        "reference": reference,
        "stake_amount": stake,
        "potential_win": potential_win,
        "balance": round(float(user.balance), 2),
        "message": "Bet placed successfully!"
    }


@router.get("/my-bets/{telegram_id}")
def get_user_bets(telegram_id: str, db: Session = Depends(get_db)):
    bets = db.query(SportsBet).filter(SportsBet.telegram_id == str(telegram_id).strip()).order_by(SportsBet.id.desc()).limit(20).all()
    return [
        {
            "id": b.id,
            "match_name": b.match_name,
            "selection": b.selection,
            "odds": b.odds,
            "stake": b.stake,
            "potential_payout": b.potential_payout,
            "status": b.status,
            "created_at": b.created_at.strftime("%Y-%m-%d %H:%M") if b.created_at else ""
        } for b in bets
    ]
