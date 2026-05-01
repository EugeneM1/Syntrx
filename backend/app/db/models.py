"""SQLAlchemy models for users, profiles, and reports."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    profiles: Mapped[list["GeneticProfile"]] = relationship(back_populates="user")


class GeneticProfile(Base):
    __tablename__ = "genetic_profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    file_format: Mapped[str] = mapped_column(String(40))
    total_variants: Mapped[int] = mapped_column(Integer)
    matched_variants: Mapped[int] = mapped_column(Integer)
    raw_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    genotypes_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="profiles")
    reports: Mapped[list["Report"]] = relationship(back_populates="profile")


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("genetic_profiles.id"))
    payload_json: Mapped[dict] = mapped_column(JSON)
    summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    profile: Mapped[GeneticProfile] = relationship(back_populates="reports")
