"""Explainable hybrid matching: lexical text, optional embeddings and item details."""
import json
import re
from functools import lru_cache
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
import models
from semantic import SemanticEncoder

ELIGIBLE = {'reported'}
FALLBACK_WEIGHTS = {'description':40,'semantic':0,'item_name':20,'category':10,'colour':10,'brand':5,'location':10,'date':5}
SEMANTIC_WEIGHTS = {'description':20,'semantic':30,'item_name':10,'category':10,'colour':10,'brand':5,'location':10,'date':5}
COLOURS = {'pink':{'pink','rose','blush','fuchsia'},'blue':{'blue','navy','azure'},
           'green':{'green','mint','olive'},'black':{'black'},'white':{'white','ivory'},
           'red':{'red','maroon','burgundy'},'purple':{'purple','violet','lilac'},
           'brown':{'brown','tan'},'grey':{'grey','gray','silver'},'yellow':{'yellow','gold'},'orange':{'orange','peach'}}


def normalized(value):
    return ' '.join(re.findall(r'\w+',str(value or '').casefold()))


def item_kind(text, category=''):
    text = normalized(text)
    patterns = [('bottle',r'\b(bottle|bottles|thermos|water container|drinking container)\b'),
                ('backpack',r'\b(backpack|school bag|rucksack)\b'),
                ('phone',r'\b(smartphone|phone|mobile handset)\b'),
                ('laptop sleeve',r'\b(laptop sleeve|laptop case|computer sleeve|computer case)\b'),
                ('headphones',r'\b(headphones|headset)\b'),('earbuds',r'\b(earbuds|airpods)\b'),
                ('keys',r'\b(keys|keyring|key ring)\b'),('wallet',r'\b(wallet|purse)\b'),
                ('book',r'\b(book|textbook|notebook)\b')]
    for kind,pattern in patterns:
        if re.search(pattern,text):return kind
    if re.search(r'\bflask\b',text) and (normalized(category) in {'drinkware','bottles'} or re.search(r'\b(water|drinking|reusable)\b',text)):
        return 'bottle'
    return ''


def canonical_text(text, category=''):
    text = normalized(text)
    for pattern,replacement in [
        (r'\b(rose coloured|rose colored|light pink)\b','pink'),
        (r'\b(water container|drinking container|drinking bottle|water bottle)\b','bottle'),
        (r'\b(school bag|rucksack)\b','backpack'),(r'\b(smartphone|mobile phone)\b','phone'),
        (r'\b(big|large sized)\b','large'),(r'\b(two litre|two litres|two liter|two liters|2 litres|2 litre)\b','2l'),
        (r'\b(study area|reading room)\b','library'),
        (r'\b(lost|misplaced|picked up|found|discovered|somewhere|beside|near|around)\b',' '),
    ]:text=re.sub(pattern,replacement,text)
    if item_kind(text,category)=='bottle':text=re.sub(r'\bflask\b','bottle',text)
    return ' '.join(text.split())


def overlap(a,b):
    a,b=set(normalized(a).split()),set(normalized(b).split())
    return len(a&b)/len(a|b) if a and b else 0.0


def colour_detail(item):
    explicit=normalized(getattr(item,'colour',''))
    # Rose is interpreted as a colour only in the colour field or a colour phrase.
    text=explicit or normalized(getattr(item,'description',''))
    groups={family for family,words in COLOURS.items() if any(re.search(r'\b'+word+r'\b',text) for word in words
            if word!='rose' or explicit or re.search(r'\brose (coloured|colored)\b',text))}
    return groups,explicit


def category_key(value):
    value=normalized(value)
    return {'bottles':'drinkware','water bottles':'drinkware','personal items':'personal','bags':'bags','accessories':'accessories'}.get(value,value)


def location_score(a,b):
    a,b=canonical_text(a),canonical_text(b)
    if not a or not b:return 0.0
    if a==b:return 1.0
    zones=[{'library','study','reading'},{'lecture','classroom','theatre'},{'cafeteria','canteen','dining'},{'parking','carpark'},{'sports','gym'}]
    left,right=set(a.split()),set(b.split())
    if any(left&zone and right&zone for zone in zones):return .9
    if (a in {'campus','main campus','university campus'} or b in {'campus','main campus','university campus'}):return .4
    return overlap(a,b)


def capacity(text):
    text=canonical_text(text)
    match=re.search(r'\b(\d+(?:\.\d+)?)\s*(l|litre|litres|liter|liters|ml)\b',text)
    if not match:return None
    return float(match[1])/(1000 if match[2]=='ml' else 1)


class MatchEngine:
    def __init__(self,mode='off',model_dir=None):
        self.encoder=SemanticEncoder(mode,model_dir)

    def status(self):return self.encoder.status()

    def score_pairs(self,lost,found_items):
        if not found_items:return []
        source=[lost]+list(found_items)
        raw=[str(getattr(item,'title','') or '')+' '+str(item.description or '') for item in source]
        texts=[canonical_text(text,item.category) for text,item in zip(raw,source)]
        try:
            matrix=TfidfVectorizer(ngram_range=(1,2),sublinear_tf=True,stop_words='english',token_pattern=r'(?u)\b\w+\b').fit_transform(texts)
            lexical=cosine_similarity(matrix[0:1],matrix[1:]).ravel().tolist()
        except ValueError:lexical=[0.0]*len(found_items)
        semantic=self.encoder.similarities(raw)
        weights=SEMANTIC_WEIGHTS if semantic is not None else FALLBACK_WEIGHTS
        results=[]
        for index,found in enumerate(found_items):
            lk,fk=item_kind(raw[0],lost.category),item_kind(raw[index+1],found.category)
            name_score=overlap(canonical_text(getattr(lost,'title',''),lost.category),canonical_text(getattr(found,'title',''),found.category))
            if lk and fk and lk==fk:name_score=max(name_score,.8)
            lc,ln=colour_detail(lost);fc,fn=colour_detail(found)
            colour=(1.0 if ln and ln==fn else .85) if lc and fc and lc&fc else 0.0
            brand=overlap(lost.brand,found.brand)
            gap=(found.date_found-lost.date_lost).days if lost.date_lost and found.date_found else None
            components={'description':max(0.0,min(1.0,float(lexical[index]))),
                'semantic':float(semantic[index]) if semantic is not None else 0.0,'item_name':name_score,
                'category':float(bool(category_key(lost.category)) and category_key(lost.category)==category_key(found.category)),
                'colour':colour,'brand':brand,'location':location_score(lost.location_lost,found.location_found),
                'date':max(0.0,1-gap/30) if gap is not None and gap>=0 else 0.0}
            penalties=[]
            if lk and fk and lk!=fk:penalties.append(('Different kinds of item',40))
            if lc and fc and not lc&fc:penalties.append(('Conflicting colours',22))
            if lost.brand and found.brand and brand<.2:penalties.append(('Different reported brands',15))
            if components['category']==0 and lost.category and found.category:penalties.append(('Different categories',10))
            lcap,fcap=capacity(raw[0]),capacity(raw[index+1])
            if lcap and fcap and abs(lcap-fcap)/max(lcap,fcap)>.35:penalties.append(('Conflicting stated capacities',15))
            total=sum(weights[key]*value for key,value in components.items())-sum(points for _,points in penalties)
            if gap is not None and gap < -2:total=0
            if lk and fk and lk!=fk:total=min(total,20)
            reasons=[]
            if components['description']>=.2 or components['semantic']>=.5:reasons.append('Similar item descriptions')
            if lk and lk==fk:reasons.append('Both describe '+('a ' if lk not in {'keys','headphones','earbuds'} else '')+lk)
            if colour:reasons.append('Same colour' if colour==1 else 'Similar colour')
            if components['location']>=.6:reasons.append('Similar location descriptions')
            if components['date']>.5:reasons.append('Dates are consistent')
            if brand>=.8:reasons.append('Same reported brand')
            detail={key:{'similarity':round(value,4),'weight':weights[key],'points':round(weights[key]*value,2)} for key,value in components.items()}
            detail.update(mode='semantic' if semantic is not None else 'fallback',reasons=reasons,
                          penalties=[{'reason':reason,'points':points} for reason,points in penalties])
            results.append((found,round(max(0,min(100,total)),2),detail))
        return sorted(results,key=lambda result:result[1],reverse=True)


def score_pairs(lost,found_items):
    """Deterministic, dependency-light fallback entry point for tests and explanations."""
    return MatchEngine('off').score_pairs(lost,found_items)


def refresh_matches(db,threshold=45,matcher=None):
    matcher=matcher or MatchEngine('off')
    lost_items=db.scalars(select(models.LostItem).where(models.LostItem.status.in_(ELIGIBLE))).all()
    found_items=db.scalars(select(models.FoundItem).where(models.FoundItem.status.in_(ELIGIBLE))).all()
    existing={(m.lost_item_id,m.found_item_id):m for m in db.scalars(select(models.Match)).all()}
    active=set()
    for lost in lost_items:
        for found,score,components in matcher.score_pairs(lost,found_items):
            if score<threshold or score<=0:continue
            pair=(lost.lost_item_id,found.found_item_id);active.add(pair)
            values=dict(lost_item_id=pair[0],found_item_id=pair[1],similarity_score=score,
                score_components=json.dumps(components),match_status='candidate',review_status='pending')
            db.execute(insert(models.Match).values(**values).on_conflict_do_update(
                index_elements=['lost_item_id','found_item_id'],
                set_={key:values[key] for key in ('similarity_score','score_components','match_status')}))
            match_id=db.scalar(select(models.Match.match_id).where(models.Match.lost_item_id==pair[0],models.Match.found_item_id==pair[1]))
            for uid in {lost.reporter_id,found.reporter_id}:
                message=(f'Good news! Someone reported finding an item that may match your lost {lost.title}. View potential match.'
                         if uid==lost.reporter_id else f'Your found {found.title} may match a campus member’s lost item. View potential match.')
                db.execute(insert(models.Notification).values(recipient_id=uid,event_type='match',match_id=match_id,
                    message_summary=message,delivery_channel='in_app',sent_status='delivered',timestamp=models.utcnow())
                    .on_conflict_do_nothing(index_elements=['recipient_id','match_id','event_type']))
    for pair,match in existing.items():
        if pair not in active:match.match_status='inactive'
    db.flush()
