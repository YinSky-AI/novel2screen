from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

from backend.config import settings

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class Novel(Base):
    __tablename__ = "novels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), default="Untitled")
    raw_text = Column(Text, default="")
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    characters = relationship("CharacterDB", back_populates="novel", cascade="all, delete-orphan")
    episodes = relationship("EpisodeDB", back_populates="novel", cascade="all, delete-orphan")
    scenes = relationship("SceneDB", back_populates="novel", cascade="all, delete-orphan")
    beats = relationship("BeatDB", back_populates="novel", cascade="all, delete-orphan")
    edits = relationship("HumanEdit", back_populates="novel", cascade="all, delete-orphan")
    exports = relationship("Export", back_populates="novel", cascade="all, delete-orphan")


class CharacterDB(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    novel_id = Column(Integer, ForeignKey("novels.id"), nullable=False)
    char_id = Column(String(100), nullable=False)
    name = Column(String(200), default="")
    role = Column(String(100), default="")
    goal = Column(Text, default="")
    fear = Column(Text, default="")
    arc = Column(Text, default="")
    voice_style = Column(String(200), default="")

    novel = relationship("Novel", back_populates="characters")


class EpisodeDB(Base):
    __tablename__ = "episodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    novel_id = Column(Integer, ForeignKey("novels.id"), nullable=False)
    episode_num = Column(Integer, default=1)
    title = Column(String(500), default="")
    summary = Column(Text, default="")
    acts = Column(Text, default="")

    novel = relationship("Novel", back_populates="episodes")


class SceneDB(Base):
    __tablename__ = "scenes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    novel_id = Column(Integer, ForeignKey("novels.id"), nullable=False)
    episode_id = Column(Integer, default=0)
    scene_num = Column(Integer, default=1)
    heading = Column(String(500), default="")
    content = Column(Text, default="")
    beats = Column(Text, default="")
    characters_in = Column(Text, default="")

    novel = relationship("Novel", back_populates="scenes")


class BeatDB(Base):
    __tablename__ = "beats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    novel_id = Column(Integer, ForeignKey("novels.id"), nullable=False)
    scene_id = Column(Integer, default=0)
    beat_num = Column(Integer, default=1)
    type = Column(String(50), default="action")
    character = Column(String(200), default="")
    description = Column(Text, default="")
    dialogue = Column(Text, default="")

    novel = relationship("Novel", back_populates="beats")


class HumanEdit(Base):
    __tablename__ = "human_edits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    novel_id = Column(Integer, ForeignKey("novels.id"), nullable=False)
    scene_id = Column(Integer, default=0)
    field = Column(String(100), default="")
    old_value = Column(Text, default="")
    new_value = Column(Text, default="")
    edited_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    novel = relationship("Novel", back_populates="edits")


class Export(Base):
    __tablename__ = "exports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    novel_id = Column(Integer, ForeignKey("novels.id"), nullable=False)
    format = Column(String(50), default="fountain")
    content = Column(Text, default="")
    exported_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    novel = relationship("Novel", back_populates="exports")


def get_session() -> Session:
    return SessionLocal()


def init_db() -> None:
    import os as _os

    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    db_dir = _os.path.dirname(db_path)
    if db_dir:
        _os.makedirs(db_dir, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized at %s", db_path)


def create_novel(title: str, raw_text: str, chunk_count: int = 0) -> Novel:
    with get_session() as session:
        novel = Novel(title=title, raw_text=raw_text, chunk_count=chunk_count)
        session.add(novel)
        session.commit()
        session.refresh(novel)
        return novel


def get_novel(novel_id: int) -> Novel | None:
    with get_session() as session:
        return session.query(Novel).filter(Novel.id == novel_id).first()


def save_character(novel_id: int, char_data: dict[str, Any]) -> CharacterDB:
    with get_session() as session:
        char = CharacterDB(
            novel_id=novel_id,
            char_id=char_data.get("char_id", ""),
            name=char_data.get("name", ""),
            role=char_data.get("role", ""),
            goal=char_data.get("goal", ""),
            fear=char_data.get("fear", ""),
            arc=char_data.get("arc", ""),
            voice_style=char_data.get("voice_style", ""),
        )
        session.add(char)
        session.commit()
        session.refresh(char)
        return char


def save_episode(novel_id: int, episode_data: dict[str, Any]) -> EpisodeDB:
    with get_session() as session:
        ep = EpisodeDB(
            novel_id=novel_id,
            episode_num=episode_data.get("episode_num", 1),
            title=episode_data.get("title", ""),
            summary=episode_data.get("summary", ""),
            acts=episode_data.get("acts", ""),
        )
        session.add(ep)
        session.commit()
        session.refresh(ep)
        return ep


def save_scene(novel_id: int, scene_data: dict[str, Any]) -> SceneDB:
    with get_session() as session:
        scene = SceneDB(
            novel_id=novel_id,
            episode_id=scene_data.get("episode_id", 0),
            scene_num=scene_data.get("scene_num", 1),
            heading=scene_data.get("heading", ""),
            content=scene_data.get("content", ""),
            beats=scene_data.get("beats", ""),
            characters_in=scene_data.get("characters_in", ""),
        )
        session.add(scene)
        session.commit()
        session.refresh(scene)
        return scene


def save_beat(novel_id: int, beat_data: dict[str, Any]) -> BeatDB:
    with get_session() as session:
        beat = BeatDB(
            novel_id=novel_id,
            scene_id=beat_data.get("scene_id", 0),
            beat_num=beat_data.get("beat_num", 1),
            type=beat_data.get("type", "action"),
            character=beat_data.get("character", ""),
            description=beat_data.get("description", ""),
            dialogue=beat_data.get("dialogue", ""),
        )
        session.add(beat)
        session.commit()
        session.refresh(beat)
        return beat


def save_human_edit(novel_id: int, edit_data: dict[str, Any]) -> HumanEdit:
    with get_session() as session:
        edit = HumanEdit(
            novel_id=novel_id,
            scene_id=edit_data.get("scene_id", 0),
            field=edit_data.get("field", ""),
            old_value=edit_data.get("old_value", ""),
            new_value=edit_data.get("new_value", ""),
        )
        session.add(edit)
        session.commit()
        session.refresh(edit)
        return edit


def save_export(novel_id: int, export_data: dict[str, Any]) -> Export:
    with get_session() as session:
        export = Export(
            novel_id=novel_id,
            format=export_data.get("format", "fountain"),
            content=export_data.get("content", ""),
        )
        session.add(export)
        session.commit()
        session.refresh(export)
        return export


def get_characters_by_novel(novel_id: int) -> list[CharacterDB]:
    with get_session() as session:
        return list(session.query(CharacterDB).filter(CharacterDB.novel_id == novel_id).all())


def get_episodes_by_novel(novel_id: int) -> list[EpisodeDB]:
    with get_session() as session:
        return list(session.query(EpisodeDB).filter(EpisodeDB.novel_id == novel_id).order_by(EpisodeDB.episode_num).all())


def get_scenes_by_novel(novel_id: int) -> list[SceneDB]:
    with get_session() as session:
        return list(session.query(SceneDB).filter(SceneDB.novel_id == novel_id).order_by(SceneDB.scene_num).all())


def get_exports_by_novel(novel_id: int) -> list[Export]:
    with get_session() as session:
        return list(session.query(Export).filter(Export.novel_id == novel_id).all())
