import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# =========================================================
# QUICK_BIRR GAMES DATABASE
# =========================================================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Local development fallback only
    DATABASE_URL = "sqlite:///./quick_birr_games.db"
    print("⚠️ DATABASE_URL not found. Using local SQLite database.")
else:
    print("✅ DATABASE_URL found.")
    print("🔗 Database type:",
          "PostgreSQL" if "postgres" in DATABASE_URL else "Other")


# =========================================================
# POSTGRES URL COMPATIBILITY
# =========================================================

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql://",
        1
    )


# =========================================================
# ENGINE
# =========================================================

connect_args = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args = {
        "check_same_thread": False
    }


engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)


# =========================================================
# SESSION
# =========================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# =========================================================
# BASE
# =========================================================

Base = declarative_base()


# =========================================================
# DATABASE SESSION
# =========================================================

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# =========================================================
# INITIALIZE DATABASE
# =========================================================

def initialize_database():

    print("==============================================")
    print("🗄️ QUICK_BIRR GAMES DATABASE INITIALIZATION")
    print("==============================================")

    try:

        # Import models so SQLAlchemy registers all tables
        import app.models  # noqa: F401

        print("📋 Registered tables:")

        for table in Base.metadata.sorted_tables:
            print(f"   ✅ {table.name}")

        # Create tables
        Base.metadata.create_all(bind=engine)

        print("==============================================")
        print("✅ DATABASE TABLES CREATED / VERIFIED")
        print("==============================================")

    except Exception as e:

        print("==============================================")
        print("❌ DATABASE INITIALIZATION FAILED")
        print("==============================================")

        print(f"Error: {e}")

        raise
