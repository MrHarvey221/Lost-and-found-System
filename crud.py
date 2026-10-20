from sqlalchemy.orm import Session
import models
import schemas
from datetime import datetime

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.user_id == user_id).first()

def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(
        name=user.name,
        surname=user.surname,
        email=user.email,
        role=user.role,
        account_status="active"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def create_lost_item(db: Session, item: schemas.LostItemCreate):
    db_item = models.LostItem(
        reporter_id=item.reporter_id,
        category=item.category,
        description=item.description,
        colour=item.colour,
        brand=item.brand,
        location_lost=item.location_lost,
        date_lost=item.date_lost,
        image_ref=item.image_ref,
        status="reported"
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    run_matching_engine(db, db_item, is_lost=True)
    return db_item

def create_found_item(db: Session, item: schemas.FoundItemCreate):
    db_item = models.FoundItem(
        reporter_id=item.reporter_id,
        category=item.category,
        description=item.description,
        colour=item.colour,
        brand=item.brand,
        location_found=item.location_found,
        date_found=item.date_found,
        image_ref=item.image_ref,
        storage_location=item.storage_location,
        status="reported"
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    run_matching_engine(db, db_item, is_lost=False)
    return db_item

def run_matching_engine(db: Session, new_item, is_lost: bool):
    score_threshold = 50.0
    
    if is_lost:
        candidates = db.query(models.FoundItem).filter(models.FoundItem.status == "reported").all()
        for found in candidates:
            score = 0.0
            if new_item.category.lower() == found.category.lower():
                score += 40.0
            if new_item.colour and found.colour and new_item.colour.lower() == found.colour.lower():
                score += 20.0
            if new_item.brand and found.brand and new_item.brand.lower() == found.brand.lower():
                score += 20.0
            if new_item.location_lost.lower() == found.location_found.lower():
                score += 20.0
                
            if score >= score_threshold:
                match_entry = models.Match(
                    lost_item_id=new_item.lost_item_id,
                    found_item_id=found.found_item_id,
                    similarity_score=score,
                    score_components=f"Category match, Attribute match score: {score}%",
                    match_status="candidate",
                    review_status="pending"
                )
                db.add(match_entry)
        db.commit()
    else:
        candidates = db.query(models.LostItem).filter(models.LostItem.status == "reported").all()
        for lost in candidates:
            score = 0.0
            if new_item.category.lower() == lost.category.lower():
                score += 40.0
            if new_item.colour and lost.colour and new_item.colour.lower() == lost.colour.lower():
                score += 20.0
            if new_item.brand and lost.brand and new_item.brand.lower() == lost.brand.lower():
                score += 20.0
            if new_item.location_found.lower() == lost.location_lost.lower():
                score += 20.0
                
            if score >= score_threshold:
                match_entry = models.Match(
                    lost_item_id=lost.lost_item_id,
                    found_item_id=new_item.found_item_id,
                    similarity_score=score,
                    score_components=f"Category match, Attribute match score: {score}%",
                    match_status="candidate",
                    review_status="pending"
                )
                db.add(match_entry)
        db.commit()

def create_claim(db: Session, claim: schemas.ClaimCreate):
    db_claim = models.Claim(
        claimant_id=claim.claimant_id,
        found_item_id=claim.found_item_id,
        claim_statement=claim.claim_statement,
        claim_status="submitted"
    )
    db.add(db_claim)
    db.commit()
    db.refresh(db_claim)
    return db_claim

def add_claim_evidence(db: Session, evidence: schemas.ClaimEvidenceCreate):
    db_evidence = models.ClaimEvidence(
        claim_id=evidence.claim_id,
        evidence_type=evidence.evidence_type,
        private_description=evidence.private_description,
        uploaded_proof_ref=evidence.uploaded_proof_ref
    )
    db.add(db_evidence)
    db.commit()
    db.refresh(db_evidence)
    return db_evidence

def review_claim(db: Session, claim_id: int, review: schemas.ClaimReviewUpdate):
    db_claim = db.query(models.Claim).filter(models.Claim.claim_id == claim_id).first()
    if not db_claim:
        return None
    
    db_claim.reviewer_id = review.reviewer_id
    db_claim.decision = review.decision
    db_claim.claim_status = f"claim_{review.decision}"
    db_claim.decision_date = datetime.utcnow()
    
    if review.decision == "approved":
        found_item = db.query(models.FoundItem).filter(models.FoundItem.found_item_id == db_claim.found_item_id).first()
        if found_item:
            found_item.status = "returned"
            
    db.commit()
    db.refresh(db_claim)
    return db_claim