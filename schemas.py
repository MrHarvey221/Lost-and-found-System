from pydantic import BaseModel, EmailStr
from datetime import date
from typing import Optional

class UserCreate(BaseModel):
    name: str
    surname: str
    email: EmailStr
    role: str

class LostItemCreate(BaseModel):
    reporter_id: int
    category: str
    description: str
    colour: Optional[str] = None
    brand: Optional[str] = None
    location_lost: str
    date_lost: date
    image_ref: Optional[str] = None

class FoundItemCreate(BaseModel):
    reporter_id: int
    category: str
    description: str
    colour: Optional[str] = None
    brand: Optional[str] = None
    location_found: str
    date_found: date
    image_ref: Optional[str] = None
    storage_location: Optional[str] = None

class ClaimCreate(BaseModel):
    claimant_id: int
    found_item_id: int
    claim_statement: str

class ClaimEvidenceCreate(BaseModel):
    claim_id: int
    evidence_type: str
    private_description: str
    uploaded_proof_ref: Optional[str] = None

class ClaimReviewUpdate(BaseModel):
    reviewer_id: int
    decision: str
    reviewer_notes: Optional[str] = None