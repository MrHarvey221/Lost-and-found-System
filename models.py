from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Numeric, ForeignKey, Index, text, func
from sqlalchemy.orm import relationship
from database import Base
import datetime

def utcnow():
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    surname = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    role = Column(String, nullable=False)
    account_status = Column(String, default="active")
    password_hash = Column(String)
    auth_version = Column(Integer, nullable=False, default=0, server_default="0")
    campus = Column(String, nullable=False, default="Main Campus", server_default="Main Campus")
    __table_args__ = (Index('uq_users_email_ci', func.lower(email), unique=True),)

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
    title = Column(String, nullable=False, default="Lost item", server_default="Lost item")
    image_refs = Column(Text)
    created_at = Column(DateTime, default=utcnow, server_default=func.current_timestamp())
    __table_args__ = (Index('ix_lost_reporter_status', 'reporter_id', 'status'), Index('ix_lost_category_status', 'category', 'status'))

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
    title = Column(String, nullable=False, default="Found item", server_default="Found item")
    image_refs = Column(Text)
    created_at = Column(DateTime, default=utcnow, server_default=func.current_timestamp())
    __table_args__ = (Index('ix_found_reporter_status', 'reporter_id', 'status'), Index('ix_found_category_status', 'category', 'status'))

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
    __table_args__ = (Index('uq_match_pair', 'lost_item_id', 'found_item_id', unique=True), Index('ix_match_found', 'found_item_id'))

    lost_item = relationship("LostItem", back_populates="matches")
    found_item = relationship("FoundItem", back_populates="matches")


class Claim(Base):
    __tablename__ = "claims"

    claim_id = Column(Integer, primary_key=True, index=True)
    claimant_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    found_item_id = Column(Integer, ForeignKey("found_items.found_item_id"), nullable=False)
    lost_item_id = Column(Integer, ForeignKey('lost_items.lost_item_id'))
    claim_statement = Column(Text, nullable=False)
    claim_status = Column(String, default="submitted")
    reviewer_id = Column(Integer, ForeignKey("users.user_id"))
    decision = Column(String)
    decision_date = Column(DateTime)
    review_notes = Column(Text)
    created_at = Column(DateTime, default=utcnow, server_default=func.current_timestamp())
    __table_args__ = (
        Index('ix_claim_status', 'claim_status'),
        Index('ix_claim_reviewer', 'reviewer_id'),
        Index('uq_claim_active_owner', 'claimant_id', 'found_item_id', unique=True,
              sqlite_where=text("claim_status IN ('submitted','more_information','approved','completed')")),
        Index('uq_claim_approved_item', 'found_item_id', unique=True,
              sqlite_where=text("claim_status IN ('approved','completed')")),
    )

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
    created_at = Column(DateTime, default=utcnow, server_default=func.current_timestamp())
    __table_args__ = (Index('ix_evidence_claim', 'claim_id'),)

    claim = relationship("Claim", back_populates="evidence")


class Notification(Base):
    __tablename__ = "notifications"

    notification_id = Column(Integer, primary_key=True, index=True)
    recipient_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    event_type = Column(String, nullable=False)
    message_summary = Column(Text, nullable=False)
    delivery_channel = Column(String, default="in_app")
    sent_status = Column(String, default="delivered")
    timestamp = Column(DateTime, default=utcnow)
    read_at = Column(DateTime)
    match_id = Column(Integer, ForeignKey('matches.match_id'))
    __table_args__ = (Index('ix_notification_recipient_time', 'recipient_id', 'timestamp'),
                     Index('uq_notification_match', 'recipient_id', 'match_id', 'event_type', unique=True))

    recipient = relationship("User", back_populates="notifications")


class StatusHistory(Base):
    __tablename__ = "status_history"

    history_id = Column(Integer, primary_key=True, index=True)
    related_record_type = Column(String, nullable=False)
    related_record_id = Column(Integer, nullable=False)
    previous_status = Column(String)
    new_status = Column(String, nullable=False)
    actor_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    timestamp = Column(DateTime, default=utcnow)
    reason = Column(Text)
    __table_args__ = (Index('ix_history_record', 'related_record_type', 'related_record_id'), Index('ix_history_actor', 'actor_id'))

    actor = relationship("User", back_populates="status_histories")
