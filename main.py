from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import models, schemas, crud
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI-Assisted Lost and Found API",
    description="Backend API for managing lost/found reports, user authentication, and matching.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Lost and Found API Backend is running successfully."}

@app.post("/users/", response_model=schemas.UserCreate, status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

@app.post("/reports/lost/", status_code=status.HTTP_201_CREATED)
def report_lost_item(item: schemas.LostItemCreate, db: Session = Depends(get_db)):
    user = crud.get_user(db, user_id=item.reporter_id)
    if not user:
        raise HTTPException(status_code=404, detail="Reporter user not found")
    db_item = crud.create_lost_item(db=db, item=item)
    return {"message": "Lost item reported successfully and checked for matches.", "lost_item_id": db_item.lost_item_id}

@app.post("/reports/found/", status_code=status.HTTP_201_CREATED)
def report_found_item(item: schemas.FoundItemCreate, db: Session = Depends(get_db)):
    user = crud.get_user(db, user_id=item.reporter_id)
    if not user:
        raise HTTPException(status_code=404, detail="Reporter user not found")
    db_item = crud.create_found_item(db=db, item=item)
    return {"message": "Found item reported successfully and checked for matches.", "found_item_id": db_item.found_item_id}

@app.get("/matches/lost/{lost_item_id}")
def get_potential_matches(lost_item_id: int, db: Session = Depends(get_db)):
    matches = db.query(models.Match).filter(models.Match.lost_item_id == lost_item_id).all()
    return matches

@app.post("/claims/", status_code=status.HTTP_201_CREATED)
def submit_claim(claim: schemas.ClaimCreate, db: Session = Depends(get_db)):
    user = crud.get_user(db, user_id=claim.claimant_id)
    if not user:
        raise HTTPException(status_code=404, detail="Claimant user not found")
    
    found_item = db.query(models.FoundItem).filter(models.FoundItem.found_item_id == claim.found_item_id).first()
    if not found_item:
        raise HTTPException(status_code=404, detail="Found item not found")
        
    db_claim = crud.create_claim(db=db, claim=claim)
    return {"message": "Claim submitted successfully. Please submit private evidence.", "claim_id": db_claim.claim_id}

@app.post("/claims/evidence/", status_code=status.HTTP_201_CREATED)
def submit_claim_evidence(evidence: schemas.ClaimEvidenceCreate, db: Session = Depends(get_db)):
    db_claim = db.query(models.Claim).filter(models.Claim.claim_id == evidence.claim_id).first()
    if not db_claim:
        raise HTTPException(status_code=404, detail="Claim not found")
        
    db_evidence = crud.add_claim_evidence(db=db, evidence=evidence)
    return {"message": "Private claim evidence submitted securely.", "evidence_id": db_evidence.evidence_id}

@app.patch("/claims/{claim_id}/review/", status_code=status.HTTP_200_OK)
def review_and_decide_claim(claim_id: int, review: schemas.ClaimReviewUpdate, db: Session = Depends(get_db)):
    reviewer = crud.get_user(db, user_id=review.reviewer_id)
    if not reviewer:
        raise HTTPException(status_code=404, detail="Reviewer user not found")
    if reviewer.role not in ["security", "administrator"]:
        raise HTTPException(status_code=403, detail="Unauthorized: Only security personnel or administrators can review claims.")
        
    updated_claim = crud.review_claim(db=db, claim_id=claim_id, review=review)
    if not updated_claim:
        raise HTTPException(status_code=404, detail="Claim not found")
        
    return {
        "message": f"Claim has been {review.decision}.",
        "claim_id": updated_claim.claim_id,
        "status": updated_claim.claim_status
    }