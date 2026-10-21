"""Explicit response projections keep password hashes and storage paths private."""
import json
import models
from security import REVIEW_ROLES


def timestamp(value):
    return value.isoformat() + 'Z' if value else None


def user_view(user):
    return {key: getattr(user, key) for key in ('user_id','name','surname','email','role','campus','account_status')}


def report_view(item, user):
    lost = isinstance(item, models.LostItem)
    kind = 'lost' if lost else 'found'
    rid = item.lost_item_id if lost else item.found_item_id
    data = dict(id=f'{"L" if lost else "F"}-{rid}', record_id=rid, type=kind, title=item.title,
        reporter_id=item.reporter_id, reporter_name=' '.join(filter(None, (item.reporter.name, item.reporter.surname))) if user.user_id==item.reporter_id or user.role in REVIEW_ROLES else 'Campus member',
        category=item.category, description=item.description, colour=item.colour, brand=item.brand,
        location=item.location_lost if lost else item.location_found,
        date=(item.date_lost if lost else item.date_found).isoformat(), status=item.status,
        created_at=timestamp(item.created_at), image_url=f'/api/reports/{kind}/{rid}/image' if item.image_ref else None)
    try:
        refs=json.loads(item.image_refs or '[]')
    except ValueError:
        refs=[]
    data['image_urls']=[f'/api/reports/{kind}/{rid}/photos/{index}' for index,_ in enumerate(refs)]
    if not data['image_urls'] and data['image_url']:data['image_urls']=[data['image_url']]
    if not lost and (user.role in REVIEW_ROLES or user.user_id==item.reporter_id):
        data['storage_location'] = item.storage_location
    return data


def evidence_view(evidence):
    return dict(evidence_id=evidence.evidence_id, evidence_type=evidence.evidence_type,
        private_description=evidence.private_description, reviewer_notes=evidence.reviewer_notes,
        created_at=timestamp(evidence.created_at),
        file_url=f'/api/evidence/{evidence.evidence_id}/file' if evidence.uploaded_proof_ref else None)


def claim_view(claim, user, details=False):
    data = dict(claim_id=claim.claim_id, claimant_id=claim.claimant_id,
        claimant_name=' '.join(filter(None, (claim.claimant.name, claim.claimant.surname))),
        found_item_id=claim.found_item_id, item_id=f'F-{claim.found_item_id}',
        lost_item_id=claim.lost_item_id,
        item_title=claim.found_item.title, claim_status=claim.claim_status,
        created_at=timestamp(claim.created_at), reviewer_id=claim.reviewer_id,
        decision=claim.decision, decision_date=timestamp(claim.decision_date))
    if details:
        data.update(claim_statement=claim.claim_statement, review_notes=claim.review_notes,
                    evidence=[evidence_view(e) for e in claim.evidence])
    return data


def match_view(match, user):
    try:
        components = json.loads(match.score_components or '{}')
    except ValueError:
        components = {}
    if not isinstance(components, dict):
        components = {}
    return dict(match_id=match.match_id, similarity_score=float(match.similarity_score),
        score_components=components, match_status=match.match_status, review_status=match.review_status,
        lost=report_view(match.lost_item, user), found=report_view(match.found_item, user),
        reasons=components.get('reasons',[]),matching_mode=components.get('mode','legacy'))


def notification_view(n):
    return dict(notification_id=n.notification_id, event_type=n.event_type, message_summary=n.message_summary,
        timestamp=timestamp(n.timestamp), read_at=timestamp(n.read_at), delivery_channel=n.delivery_channel,match_id=n.match_id)
