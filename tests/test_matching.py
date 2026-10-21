from datetime import date
from types import SimpleNamespace
from matching import score_pairs


def pair(**changes):
    data = dict(description='black padded laptop sleeve grey zipper',category='Electronics',
                colour='Black',brand='Lenovo',location_lost='Main Campus Library',
                location_found='Main Campus Library',date_lost=date(2026,1,1),date_found=date(2026,1,2))
    data.update(changes)
    return SimpleNamespace(**data)


def test_good_match_beats_incorrect_match():
    lost = pair()
    good = pair(description='padded black laptop sleeve with grey zipper')
    bad = pair(description='red cotton winter jacket', category='Clothing', colour='Red',brand='Other',location_found='Sports field')
    scores = score_pairs(lost, [bad,good])
    assert scores[0][0] is good and scores[0][1] >= 70
    assert scores[1][1] == 0


def test_empty_text_missing_attributes_and_tiny_dataset():
    lost = pair(description='',colour=None,brand=None,location_lost='')
    found = pair(description='',colour=None,brand=None,location_found='')
    score = score_pairs(lost,[found])[0][1]
    assert 0 <= score < 45  # missing fields do not earn points or inflate scores
    assert score_pairs(lost,[]) == []
    assert 0 <= score_pairs(pair(description='a'),[pair(description='a')])[0][1] <= 100


def test_date_chronology_and_distant_dates():
    lost = pair()
    earlier = pair(date_found=date(2025,12,1))
    assert score_pairs(lost,[earlier])[0][1] == 0
    later = pair(date_found=date(2026,6,1))
    assert score_pairs(lost,[later])[0][2]['date']['points'] == 0
