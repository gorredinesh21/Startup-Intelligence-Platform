import os
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

LOCAL_FALLBACK = os.getenv("LOCAL_FALLBACK", "true").lower() == "true"
DATABASE_URL = os.getenv("DATABASE_URL")

if LOCAL_FALLBACK or not DATABASE_URL:
    # Use SQLite for local fallback
    db_path = os.path.join(os.path.dirname(__file__), "..", "startup_intel.db")
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.abspath(db_path)}"
else:
    SQLALCHEMY_DATABASE_URL = DATABASE_URL

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Startup(Base):
    __tablename__ = "startups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    website = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    market = Column(String, nullable=True)
    tech_stack = Column(String, nullable=True)  # Comma-separated list of tech
    funding_total = Column(Float, default=0.0)
    logo_url = Column(String, nullable=True)
    raptor_summary = Column(Text, nullable=True)  # Global level 3 summary

class FundingRound(Base):
    __tablename__ = "funding_rounds"

    id = Column(Integer, primary_key=True, index=True)
    startup_name = Column(String, index=True, nullable=False)
    round_type = Column(String, nullable=False)  # Seed, Series A, Series B, Grants
    amount = Column(Float, nullable=True)  # in USD
    investors = Column(String, nullable=True)  # Comma-separated list of investors
    date = Column(String, nullable=True)  # YYYY-MM-DD or readable string

class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, index=True)
    startup_name = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    url = Column(String, nullable=True)
    source = Column(String, nullable=True)
    date = Column(String, nullable=True)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
