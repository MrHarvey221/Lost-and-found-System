"""Transactional report, claim, notification and audit operations."""
from fastapi import HTTPException
from sqlalchemy import select, update
import models
from matching import refresh_matches
from security import REVIEW_ROLES

ACTIVE_CLAIMS = {'submitted', 'more_information'}


def history(db, record_type, record_id, previous, new, actor_id, reason):
    db.add(models.StatusHistory(related_record_type=record_type, related_record_id=record_id,
        previous_status=previous, new_status=new, actor_id=actor_id, reason=reason))


def notify(db, uid, event, message):
    db.add(models.Notification(recipient_id=uid, event_type=event, message_summary=message))


def notify_officers(db, event, message, exclude=None):
    officers = db.scalars(select(models.User).where(models.User.role.in_(REVIEW_ROLES), models.User.account_status == 'active')).all()
    for officer in officers:
        if officer.user_id != exclude:
            notify(db, officer.user_id, event, message)


def create_report(db, item, user, kind, threshold, matcher=None):
    cls = models.LostItem if kind == 'lost' else models.FoundItem
    report = cls(**item.model_dump(), reporter_id=user.user_id, status='reported')
    db.add(report)
    db.flush()
    rid = report.lost_item_id if kind == 'lost' else report.found_item_id
    history(db, kind, rid, None, 'reported', user.user_id, 'Report submitted')
    notify(db, user.user_id, 'report', f'Your {kind} report “{report.title}” has been saved.')
    refresh_matches(db, threshold, matcher)
    return report


def create_claim(db, data, user):
    if data.lost_item_id:
        lost=db.get(models.LostItem,data.lost_item_id)
        if not lost or lost.reporter_id!=user.user_id or lost.status!='reported':
            raise HTTPException(422,'Link only an active lost report that belongs to your account.')
    found = db.get(models.FoundItem, data.found_item_id)
    if not found:
        raise HTTPException(404, 'Found report not found.')
    if found.status != 'reported':
        raise HTTPException(409, 'This item is unavailable for new claims.')
    if found.reporter_id == user.user_id:
        raise HTTPException(409, 'You cannot claim an item you reported as found.')
    existing = db.scalar(select(models.Claim).where(models.Claim.found_item_id == found.found_item_id,
        models.Claim.claimant_id == user.user_id, models.Claim.claim_status.in_({'submitted','more_information','approved','completed'})))
    if existing:
        raise HTTPException(409, 'You already have an active claim for this item.')
    claim = models.Claim(claimant_id=user.user_id, found_item_id=found.found_item_id, lost_item_id=data.lost_item_id,
                         claim_statement=data.claim_statement, claim_status='submitted')
    db.add(claim)
    db.flush()
    db.add(models.ClaimEvidence(claim_id=claim.claim_id, evidence_type='ownership_detail',
                               private_description=data.private_description))
    history(db, 'claim', claim.claim_id, None, 'submitted', user.user_id, 'Ownership claim submitted')
    notify(db, user.user_id, 'claim', f'Your claim for “{found.title}” is awaiting officer review.')
    notify_officers(db, 'claim', f'Claim #{claim.claim_id} for “{found.title}” needs review.', exclude=user.user_id)
    return claim


def authorized_claim(db, claim_id, user):
    claim = db.get(models.Claim, claim_id)
    if not claim:
        raise HTTPException(404, 'Claim not found.')
    if claim.claimant_id != user.user_id and user.role not in REVIEW_ROLES:
        # Do not reveal whether another person's private claim exists.
        raise HTTPException(404, 'Claim not found.')
    return claim


def review_claim(db, claim, review, officer, threshold, matcher=None):
    if claim.claimant_id == officer.user_id:
        raise HTTPException(403, 'You cannot review your own ownership claim.')
    if claim.claim_status not in ACTIVE_CLAIMS:
        raise HTTPException(409, 'This claim has already been decided.')
    found = db.get(models.FoundItem, claim.found_item_id)
    if found.status != 'reported':
        raise HTTPException(409, 'This item is already reserved, returned or closed.')
    if review.decision == 'approved' and not claim.evidence:
        raise HTTPException(409, 'Private evidence is required before approval.')
    previous = claim.claim_status
    if review.decision == 'approved':
        # Compare-and-set serializes competing approvals in SQLite.
        changed = db.execute(update(models.FoundItem).where(models.FoundItem.found_item_id == found.found_item_id,
                         models.FoundItem.status == 'reported').values(status='claim_approved')).rowcount
        if not changed:
            raise HTTPException(409, 'Another claim has already reserved this item.')
        history(db, 'found', found.found_item_id, 'reported', 'claim_approved', officer.user_id, review.reviewer_notes)
        others = db.scalars(select(models.Claim).where(models.Claim.found_item_id == found.found_item_id,
            models.Claim.claim_id != claim.claim_id, models.Claim.claim_status.in_(ACTIVE_CLAIMS))).all()
        for other in others:
            old = other.claim_status
            other.claim_status, other.decision = 'rejected', 'rejected'
            other.reviewer_id, other.decision_date = officer.user_id, models.utcnow()
            other.review_notes = 'A different ownership claim was verified by an officer.'
            history(db, 'claim', other.claim_id, old, 'rejected', officer.user_id, other.review_notes)
            notify(db, other.claimant_id, 'claim', f'Claim #{other.claim_id} was rejected because another claim was verified.')
    claim.claim_status = review.decision
    claim.decision, claim.review_notes = review.decision, review.reviewer_notes
    claim.reviewer_id, claim.decision_date = officer.user_id, models.utcnow()
    for evidence in claim.evidence:
        evidence.reviewer_notes = review.reviewer_notes
    history(db, 'claim', claim.claim_id, previous, review.decision, officer.user_id, review.reviewer_notes)
    notify(db, claim.claimant_id, 'claim', f'Claim #{claim.claim_id}: {review.decision.replace("_", " ")}. {review.reviewer_notes}')
    if review.decision == 'approved':
        notify(db, found.reporter_id, 'claim', f'An officer approved a claim for “{found.title}”. Await a verified handover.')
    db.flush()
    refresh_matches(db, threshold, matcher)
    return claim


def update_report_status(db, item, kind, data, user, threshold, matcher=None):
    officer = user.role in REVIEW_ROLES
    rid = item.lost_item_id if kind == 'lost' else item.found_item_id
    if not officer and (item.reporter_id != user.user_id or kind != 'lost' or data.status not in {'closed', 'reported'}):
        raise HTTPException(403, 'Only officers may update found-item or return status. You may close your own lost report.')
    if item.status == data.status:
        return item
    if item.status in {'returned', 'claim_approved'} and data.status == 'reported':
        raise HTTPException(409, 'A reserved or returned item cannot be reopened.')
    if kind == 'found':
        if item.status == 'claim_approved' and data.status != 'returned':
            raise HTTPException(409, 'Complete the approved handover before changing this status.')
        if data.status == 'returned':
            claim = db.scalar(select(models.Claim).where(models.Claim.found_item_id == rid, models.Claim.claim_status == 'approved'))
            if not claim:
                raise HTTPException(409, 'Approve an ownership claim before recording a return.')
            claim.claim_status = 'completed'
            if claim.lost_item_id:
                lost=db.get(models.LostItem,claim.lost_item_id)
                if lost and lost.reporter_id==claim.claimant_id and lost.status=='reported':
                    lost.status='returned'
                    history(db,'lost',lost.lost_item_id,'reported','returned',user.user_id,'Verified recovery through the linked ownership claim. '+data.reason)
            history(db, 'claim', claim.claim_id, 'approved', 'completed', user.user_id, data.reason)
            notify(db, claim.claimant_id, 'claim', f'The handover for “{item.title}” has been recorded. Your claim is complete.')
        if data.status == 'closed':
            active = db.scalars(select(models.Claim).where(models.Claim.found_item_id == rid,
                                                          models.Claim.claim_status.in_(ACTIVE_CLAIMS))).all()
            for claim in active:
                old = claim.claim_status
                claim.claim_status = 'rejected'
                claim.decision, claim.review_notes = 'rejected', data.reason
                claim.reviewer_id, claim.decision_date = user.user_id, models.utcnow()
                history(db, 'claim', claim.claim_id, old, 'rejected', user.user_id, data.reason)
                notify(db, claim.claimant_id, 'claim', f'Claim #{claim.claim_id} was closed by an officer: {data.reason}')
    old = item.status
    item.status = data.status
    history(db, kind, rid, old, data.status, user.user_id, data.reason)
    notify(db, item.reporter_id, 'report', f'“{item.title}” is now {data.status}. {data.reason}')
    db.flush()
    refresh_matches(db, threshold, matcher)
    return item
