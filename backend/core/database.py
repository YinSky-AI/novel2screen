"""SQLAlchemy ORM models for Novel2Screen.
Section 8 of the platform specification.
"""
from __future__ import annotations
import os
from datetime import datetime
from sqlalchemy import (create_engine, Column, Integer, String, Text,
                        Float, ForeignKey, JSON, DateTime, Index)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./novel2screen.db")
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Novel(Base):
    __tablename__ = "novels"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    raw_text = Column(Text, nullable=False)
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    chapters = relationship("Chapter", back_populates="novel", cascade="all, delete-orphan")
    characters = relationship("CharacterDB", back_populates="novel", cascade="all, delete-orphan")
    episodes = relationship("EpisodeDB", back_populates="novel", cascade="all, delete-orphan")
    exports = relationship("Export", back_populates="novel", cascade="all, delete-orphan")


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)
    novel_id = Column(Integer, ForeignKey("novels.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    order = Column(Integer, nullable=False)

    novel = relationship("Novel", back_populates="chapters")

    __table_args__ = (Index("idx_chapter_novel_order", "novel_id", "order"),)


class CharacterDB(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, index=True)
    novel_id = Column(Integer, ForeignKey("novels.id"), nullable=False, index=True)
    character_id = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    goal = Column(Text, default="")
    fear = Column(Text, default="")
    arc = Column(Text, default="")
    voice_style = Column(String(255), default="")
    traits = Column(JSON, default=list)

    novel = relationship("Novel", back_populates="characters")

    __table_args__ = (Index("idx_char_novel", "novel_id", "character_id"),)


class EpisodeDB(Base):
    __tablename__ = "episodes"

    id = Column(Integer, primary_key=True, index=True)
    novel_id = Column(Integer, ForeignKey("novels.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    summary = Column(Text, default="")
    theme = Column(String(255), default="")
    pacing = Column(String(255), default="")
    episode_order = Column(Integer, default=0)

    novel = relationship("Novel", back_populates="episodes")
    scenes = relationship("SceneDB", back_populates="episode", cascade="all, delete-orphan")

    __table_args__ = (Index("idx_episode_novel_order", "novel_id", "episode_order"),)


class SceneDB(Base):
    __tablename__ = "scenes"

    id = Column(Integer, primary_key=True, index=True)
    episode_id = Column(Integer, ForeignKey("episodes.id"), nullable=False, index=True)
    scene_id = Column(String(50), nullable=False)
    location = Column(String(255), default="")
    time = Column(String(50), default="")
    visual_focus = Column(Text, nullable=True)
    sound_effect = Column(String(255), nullable=True)
    voice_over = Column(Text, nullable=True)
    transition = Column(String(50), default="cut")
    duration_estimate = Column(String(20), default="120s")

    episode = relationship("EpisodeDB", back_populates="scenes")
    beats = relationship("BeatDB", back_populates="scene", cascade="all, delete-orphan")


class BeatDB(Base):
    __tablename__ = "beats"

    id = Column(Integer, primary_key=True, index=True)
    scene_id_fk = Column(Integer, ForeignKey("scenes.id"), nullable=False, index=True)
    type = Column(String(20), nullable=False)
    character_id = Column(String(50), nullable=True)
    content = Column(Text, nullable=False)
    emotion = Column(String(50), nullable=True)

    scene = relationship("SceneDB", back_populates="beats")


class HumanEdit(Base):
    __tablename__ = "human_edits"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(100), nullable=False, index=True)
    original_yaml_hash = Column(String(64), nullable=False)
    edited_yaml = Column(Text, nullable=False)
    reconcile_status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


class Export(Base):
    __tablename__ = "exports"

    id = Column(Integer, primary_key=True, index=True)
    novel_id = Column(Integer, ForeignKey("novels.id"), nullable=False, index=True)
    task_id = Column(String(100), nullable=False, index=True)
    yaml_content = Column(Text, nullable=False)
    exported_at = Column(DateTime, default=datetime.utcnow)

    novel = relationship("Novel", back_populates="exports")


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
