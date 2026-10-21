from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.orm import declarative_base
Base = declarative_base()
import datetime

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    surname = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    role = Column(String, nullable=False)
    account_status = Column(String, default="active")

    lost_reports = relationship("LostItem", back_populates="reporter")
    found_reports = relationship("FoundItem", back_populates="reporter")
    claims = relationship("Claim", foreign_keys="[Claim.claimant_id]", back_populates="claimant")
    reviewed_claims = relationship("Claim", foreign_keys="[Claim.reviewer_id]", back_populates="reviewer")
    notifications = relationship("Notification", back_populates="recipient")
    status_histories = relationship("StatusHistory", back_populates="actor")


class LostItem(Base):
    __tablename__ = "lost_items"

    lost_item_id = Column(Integer, primary_key=True, index=True)
    reporter_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    category = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    colour = Column(String)
    brand = Column(String)
    location_lost = Column(String, nullable=False)
    date_lost = Column(Date, nullable=False)
    image_ref = Column(String)
    status = Column(String, default="reported")

    reporter = relationship("User", back_populates="lost_reports")
    matches = relationship("Match", back_populates="lost_item")


class FoundItem(Base):
    __tablename__ = "found_items"

    found_item_id = Column(Integer, primary_key=True, index=True)
    reporter_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    category = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    colour = Column(String)
    brand = Column(String)
    location_found = Column(String, nullable=False)
    date_found = Column(Date, nullable=False)
    image_ref = Column(String)
    storage_location = Column(String)
    status = Column(String, default="reported")

    reporter = relationship("User", back_populates="found_reports")
    matches = relationship("Match", back_populates="found_item")
    claims = relationship("Claim", back_populates="found_item")


class Match(Base):
    __tablename__ = "matches"

    match_id = Column(Integer, primary_key=True, index=True)
    lost_item_id = Column(Integer, ForeignKey("lost_items.lost_item_id"), nullable=False)
    found_item_id = Column(Integer, ForeignKey("found_items.found_item_id"), nullable=False)
    similarity_score = Column(Numeric(5, 2), nullable=False)
    score_components = Column(Text)
    match_status = Column(String, default="candidate")
    review_status = Column(String, default="pending")

    lost_item = relationship("LostItem", back_populates="matches")
    found_item = relationship("FoundItem", back_populates="matches")


class Claim(Base):
    __tablename__ = "claims"

    claim_id = Column(Integer, primary_key=True, index=True)
    claimant_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    found_item_id = Column(Integer, ForeignKey("found_items.found_item_id"), nullable=False)
    claim_statement = Column(Text, nullable=False)
    claim_status = Column(String, default="submitted")
    reviewer_id = Column(Integer, ForeignKey("users.user_id"))
    decision = Column(String)
    decision_date = Column(DateTime)

    claimant = relationship("User", foreign_keys=[claimant_id], back_populates="claims")
    reviewer = relationship("User", foreign_keys=[reviewer_id], back_populates="reviewed_claims")
    found_item = relationship("FoundItem", back_populates="claims")
    evidence = relationship("ClaimEvidence", back_populates="claim")


class ClaimEvidence(Base):
    __tablename__ = "claim_evidence"

    evidence_id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.claim_id"), nullable=False)
    evidence_type = Column(String, nullable=False)
    private_description = Column(Text, nullable=False)
    uploaded_proof_ref = Column(String)
    reviewer_notes = Column(Text)

    claim = relationship("Claim", back_populates="evidence")


class Notification(Base):
    __tablename__ = "notifications"

    notification_id = Column(Integer, primary_key=True, index=True)
    recipient_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    event_type = Column(String, nullable=False)
    message_summary = Column(Text, nullable=False)
    delivery_channel = Column(String, default="email")
    sent_status = Column(String, default="pending")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    recipient = relationship("User", back_populates="notifications")


class StatusHistory(Base):
    __tablename__ = "status_history"

    history_id = Column(Integer, primary_key=True, index=True)
    related_record_type = Column(String, nullable=False)
    related_record_id = Column(Integer, nullable=False)
    previous_status = Column(String)
    new_status = Column(String, nullable=False)
    actor_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    reason = Column(Text)

    actor = relationship("User", back_populates="status_histories")
