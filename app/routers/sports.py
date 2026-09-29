import uuid
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User, WalletTransaction


router = APIRouter(
    prefix="/api/sports",
    tags=["Sports Betting"]
)


# =========================================================
# DATABASE
# =========================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================================================
# REQUEST MODEL
# =========================================================

class PlaceBetRequest(BaseModel):
    telegram_id: str
    match_id: str
    match_name: str
    selection: str
    odds: float = Field(gt=1.0)
    stake_amount: float = Field(gt=0)


# =========================================================
# CONFIG & CONSTANTS
# =========================================================

MIN_STAKE = 10.0  # አነስተኛ የመደቢያ መጠን

# The Odds API (ወይም የሚጠቀሙበት API)
ODDS_API_KEY = "YOUR_ODDS_API_KEY"  # የ API ቁልፍህን እዚህ አስገባ
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports"


# =========================================================
# GET MATCHES (ጨዋታዎችን ከ API ማምጫ)
# =========================================================

@router.get("/matches/{sport_key}")
async def get_matches(sport_key: str):
    """
    sport_key ለምሳሌ:
    - soccer_epl (Premier League)
    - soccer_spain_la_liga
    - soccer_germany_bundesliga
    - soccer_italy_serie_a
    - soccer_uefa_champs_league
    """
    if not ODDS_API_KEY or ODDS_API_KEY == "YOUR_ODDS_API_KEY":
        # API Key ከሌለ ወይም ዝግጁ ካልሆነ ለሙከራ የሚሆኑ Dummy Data-ዎችን ይመልሳል
        return [
            {
                "id": "match_001",
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "commence_time": "2026-10-01T19:00:00Z",
                "odds": {"home_win": 1.95, "draw": 3.40, "away_win": 3.80}
            },
            {
                "id": "match_002",
                "home_team": "Real Madrid",
                "away_team": "Barcelona",
                "commence_time": "2026-10-02T20:00:00Z",
                "odds": {"home_win": 2.10, "draw": 3.30, "away_win": 3.20}
            }
        ]

    try:
        async with httpx.AsyncClient() as client:
            url = f"{ODDS_API_URL}/{sport_key}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h"
            response = await client.get(url, timeout=10.0)

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to fetch matches from sports provider."
                )

            data = response.json()
            matches = []

            for match in data[:15]:  # የመጀመሪያዎቹን 15 ጨዋታዎች ብቻ መውሰድ
                h2h_market = next(
                    (m for b in match.get("bookmakers", []) for m in b.get("markets", []) if m.get("key") == "h2h"),
                    None
                )

                home_win, draw, away_win = 1.0, 1.0, 1.0
                if h2h_market:
                    for outcome in h2h_market.get("outcomes", []):
                        if outcome["name"] == match["home_team"]:
                            home_win = outcome["price"]
                        elif outcome["name"] == match["away_team"]:
                            away_win = outcome["price"]
                        elif outcome["name"].lower() == "draw":
                            draw = outcome["price"]

                matches.append({
                    "id": match.get("id"),
                    "home_team": match.get("home_team"),
                    "away_team": match.get("away_team"),
                    "commence_time": match.get("commence_time"),
                    "odds": {
                        "home_win": home_win,
                        "draw": draw,
                        "away_win": away_win
                    }
                })

            return matches

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving live matches."
        )


# =========================================================
# PLACE BET (ውርርድ መመዝገቢያ)
# =========================================================

@router.post("/place-bet")
def place_bet(
    request: PlaceBetRequest,
    db: Session = Depends(get_db)
):
    telegram_id = str(request.telegram_id).strip()
    stake = round(float(request.stake_amount), 2)
    odds = round(float(request.odds), 2)

    # -----------------------------------------------------
    # Validate stake & data
    # -----------------------------------------------------

    if stake < MIN_STAKE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Minimum stake is {MIN_STAKE} ETB."
        )

    if not telegram_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram ID is required."
        )

    # -----------------------------------------------------
    # Lock user row
    # -----------------------------------------------------

    user = (
        db.query(User)
        .filter(User.telegram_id == telegram_id)
        .with_for_update()
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    # -----------------------------------------------------
    # Check banned user
    # -----------------------------------------------------

    if getattr(user, "is_banned", 0):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is currently restricted."
        )

    # -----------------------------------------------------
    # Check balance
    # -----------------------------------------------------

    current_balance = round(float(user.balance or 0), 2)

    if current_balance < stake:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient balance! Your balance is {current_balance:.2f} ETB."
        )

    # -----------------------------------------------------
    # Calculate potential win & deduct stake
    # -----------------------------------------------------

    potential_win = round(stake * odds, 2)
    balance_after_stake = round(current_balance - stake, 2)

    user.balance = balance_after_stake
    reference = f"SPORTS-{uuid.uuid4().hex[:16]}"

    # -----------------------------------------------------
    # Stake transaction
    # -----------------------------------------------------

    stake_transaction = WalletTransaction(
        user_id=user.id,
        transaction_type="game_stake_sports",
        amount=-stake,
        balance_after=balance_after_stake,
        game="sports",
        reference=reference,
        description=f"Sports Bet ({request.match_name} - {request.selection} @ {odds})"
    )

    db.add(stake_transaction)

    # -----------------------------------------------------
    # ONE COMMIT
    # -----------------------------------------------------

    try:
        db.commit()
        db.refresh(user)

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bet could not be placed. Please try again."
        )

    return {
        "success": True,
        "reference": reference,
        "stake_amount": stake,
        "potential_win": potential_win,
        "balance": round(float(user.balance), 2),
        "message": f"Bet placed successfully for {request.match_name}!"
    }
