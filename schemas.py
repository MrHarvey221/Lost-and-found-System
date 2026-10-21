"""Validated write contracts. Identity comes from the signed session."""
from datetime import date
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

Role = Literal['student', 'staff', 'security', 'lost_property', 'administrator']
Password = Annotated[str, StringConstraints(strip_whitespace=False, min_length=10, max_length=128)]
LoginPassword = Annotated[str, StringConstraints(strip_whitespace=False, min_length=1, max_length=128)]


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class UserCreate(Input):
    name: str = Field(min_length=1, max_length=90)
    surname: str = Field(default='', max_length=90)
    email: EmailStr
    password: Password
    role: Literal['student', 'staff'] = 'student'
    campus: str = Field(default='Main Campus', min_length=1, max_length=80)


class Login(Input):
    email: EmailStr
    password: LoginPassword


class ProfileUpdate(Input):
    name: str = Field(min_length=1, max_length=90)
    surname: str = Field(default='', max_length=90)
    campus: str = Field(min_length=1, max_length=80)


class ReportBase(Input):
    title: str = Field(min_length=2, max_length=90)
    category: str = Field(min_length=1, max_length=60)
    description: str = Field(min_length=5, max_length=2000)
    colour: str | None = Field(default=None, max_length=50)
    brand: str | None = Field(default=None, max_length=80)


class LostItemCreate(ReportBase):
    location_lost: str = Field(min_length=2, max_length=150)
    date_lost: date

    @field_validator('date_lost')
    @classmethod
    def not_future(cls, value):
        if value > date.today():
            raise ValueError('Report date cannot be in the future.')
        return value


class FoundItemCreate(ReportBase):
    location_found: str = Field(min_length=2, max_length=150)
    date_found: date
    storage_location: str | None = Field(default=None, max_length=150)

    @field_validator('date_found')
    @classmethod
    def not_future(cls, value):
        if value > date.today():
            raise ValueError('Report date cannot be in the future.')
        return value


class ClaimCreate(Input):
    found_item_id: int = Field(gt=0)
    lost_item_id: int | None = Field(default=None,gt=0)
    claim_statement: str = Field(min_length=8, max_length=2000)
    private_description: str = Field(min_length=8, max_length=2000)


class ClaimReviewUpdate(Input):
    decision: Literal['approved', 'rejected', 'more_information']
    reviewer_notes: str = Field(min_length=5, max_length=2000)


class StatusUpdate(Input):
    status: Literal['reported', 'closed', 'returned']
    reason: str = Field(min_length=5, max_length=1000)


class UserAdminUpdate(Input):
    role: Role
    account_status: Literal['active', 'suspended']
    reason: str = Field(min_length=5, max_length=1000)


class StorageUpdate(Input):
    storage_location: str = Field(min_length=2, max_length=150)
    reason: str = Field(min_length=5, max_length=1000)


class UserOut(BaseModel):
    user_id: int
    name: str
    surname: str
    email: str
    role: str
    account_status: str
    campus: str


class ReportOut(BaseModel):
    id: str
    record_id: int
    type: Literal['lost','found']
    title: str
    reporter_id: int
    reporter_name: str
    category: str
    description: str
    colour: str | None
    brand: str | None
    location: str
    date: str
    status: str
    created_at: str | None
    image_url: str | None
    image_urls: list[str] = []
    storage_location: str | None = None


class EvidenceOut(BaseModel):
    evidence_id: int
    evidence_type: str
    private_description: str
    reviewer_notes: str | None
    created_at: str | None
    file_url: str | None


class ClaimOut(BaseModel):
    claim_id: int
    claimant_id: int
    claimant_name: str
    found_item_id: int
    lost_item_id: int | None = None
    item_id: str
    item_title: str
    claim_status: str
    created_at: str | None
    reviewer_id: int | None
    decision: str | None
    decision_date: str | None
    claim_statement: str | None = None
    review_notes: str | None = None
    evidence: list[EvidenceOut] | None = None


class MatchOut(BaseModel):
    match_id: int
    similarity_score: float
    score_components: dict
    match_status: str
    review_status: str
    lost: ReportOut
    found: ReportOut
    reasons: list[str] = []
    matching_mode: str = 'fallback'


class NotificationOut(BaseModel):
    notification_id: int
    event_type: str
    message_summary: str
    timestamp: str | None
    read_at: str | None
    delivery_channel: str
    match_id: int | None = None
