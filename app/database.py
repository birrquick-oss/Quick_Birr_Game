import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# =========================================================
# QUICK_BIRR GAMES DATABASE
# =========================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./quick_birr_games.db"
)

# Render / Railway / PostgreSQL compatibility
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql://",
        1
    )

# =========================================================
# ENGINE & CONNECT ARGS
# =========================================================

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

# =========================================================
# SESSION & BASE
# =========================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

# =========================================================
# DATABASE SESSION DEPENDENCY
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
    """
    Create all QUICK_BIRR GAMES tables.
    """
    # ⚠️ Models ከ Base በኋላ መጫን ስላለባቸው በቀጥታ እዚህ ላይ Import ይደረጋሉ።
    import app.models as models  # noqa: F401

    # Base.metadata ላይ የተመዘገቡትን Tables በሙሉ Database ውስጥ ይፈጥራል
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")
