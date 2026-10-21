"""Opt-in, idempotent synthetic data in a dedicated demonstration database."""
from datetime import date, timedelta
from pathlib import Path
from sqlalchemy import select
from config import ROOT, Settings
from security import hash_password
from matching import refresh_matches
import models

DEMO_PASSWORD='FindlyDemo2026!'
DEMO_USERS=[('student.demo@example.com','Amantle','Molefe','student'),
            ('finder.demo@example.com','Neo','Dube','student'),
            ('security.demo@example.com','Campus','Security','security'),
            ('admin.demo@example.com','Campus','Administrator','administrator')]


def demo_settings():
    settings=Settings.from_env()
    settings.database_url='sqlite:///'+str(ROOT/'findly-demo.db')
    settings.data_dir=ROOT/'data-demo'
    settings.demo_mode=True
    return settings


def make_illustrations():
    assets=ROOT/'demo-assets';assets.mkdir(exist_ok=True)
    shapes={
      'bottle':('<rect x="118" y="44" width="84" height="25" rx="8" fill="#766f88"/><path d="M128 69h64v19l12 21v133q0 18-18 18h-52q-18 0-18-18V109l12-21z" fill="#e8a4bd"/><rect x="122" y="119" width="76" height="94" rx="10" fill="#edb2c8"/><path d="M201 112h17q15 0 15 20v31q0 18-27 18" fill="none" stroke="#d487a3" stroke-width="10"/>','#f7e9ef'),
      'bag':('<path d="M123 91V70q0-24 37-24t37 24v21" fill="none" stroke="#47658f" stroke-width="10"/><rect x="94" y="83" width="132" height="174" rx="35" fill="#7398c6"/><rect x="111" y="162" width="98" height="74" rx="15" fill="#8aadd8"/><path d="M119 146h82M125 174h70" stroke="#d9e5f5" stroke-width="5"/>','#edf1f8'),
      'phone':('<rect x="106" y="41" width="108" height="224" rx="20" fill="#494753"/><rect x="113" y="49" width="94" height="204" rx="14" fill="#8d88b7"/><path d="M135 55h50" stroke="#494753" stroke-width="8" stroke-linecap="round"/><circle cx="160" cy="239" r="5" fill="#dcd8ef"/>','#efedf6'),
      'keys':('<circle cx="144" cy="95" r="39" fill="none" stroke="#b3b0b9" stroke-width="12"/><path d="m145 132 0 113h33v-20h-18v-20h18v-17h-18v-56" fill="#c4c1c9"/><circle cx="103" cy="99" r="17" fill="#8bbbd3"/>','#eef4f7'),
      'sleeve':('<rect x="62" y="87" width="196" height="144" rx="15" fill="#787580"/><rect x="68" y="95" width="184" height="130" rx="11" fill="#8a8793"/><path d="M76 102h168" stroke="#c9c4d2" stroke-width="4"/><rect x="218" y="146" width="19" height="8" rx="2" fill="#d4cfdf"/>','#eeecf2'),
    }
    for name,(shape,bg) in shapes.items():
        (assets/(name+'.svg')).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="640" height="420" viewBox="0 0 320 300"><rect width="320" height="300" fill="{bg}"/><ellipse cx="160" cy="266" rx="83" ry="9" fill="#302747" opacity=".05"/>{shape}<text x="160" y="290" text-anchor="middle" font-family="Arial" font-size="7" letter-spacing="2" fill="#9c91a6">DEMO ILLUSTRATION</text></svg>',encoding='utf-8')


def seed_demo(db,matcher):
    make_illustrations()
    users=[]
    for email,name,surname,role in DEMO_USERS:
        user=db.scalar(select(models.User).where(models.User.email==email))
        if not user:
            user=models.User(name=name,surname=surname,email=email,role=role,campus='Main Campus',
                account_status='active',password_hash=hash_password(DEMO_PASSWORD))
            db.add(user);db.flush()
        users.append(user)
    owner,finder=users[:2];monday=date.today()-timedelta(days=2)
    examples=[
      ('lost',owner,'Pink two-litre bottle','Drinkware','Large pink two-litre drinking bottle lost near the university library.','Pink','','University library','bottle'),
      ('found',finder,'Rose reusable water flask','Drinkware','Rose-coloured reusable water flask discovered beside the campus study area.','Rose','','Campus study area','bottle'),
      ('lost',owner,'Black Samsung phone','Electronics','Black Samsung smartphone in a clear case with a small crack on the corner.','Black','Samsung','Student centre','phone'),
      ('found',finder,'Blue Adidas backpack','Bags','Blue Adidas school bag found near the sports fields.','Blue','Adidas','Sports fields','bag'),
      ('lost',owner,'Silver keys with a blue ring','Accessories','Three silver keys on a round blue key ring.','Silver','','Student centre','keys'),
      ('found',finder,'Three keys on a blue keyring','Accessories','A set of three silver keys attached to a blue circular keyring.','Silver','','Student centre','keys'),
      ('lost',owner,'Black Lenovo laptop sleeve','Electronics','Black padded Lenovo laptop sleeve with a grey logo near the zipper.','Black','Lenovo','Main campus library','sleeve'),
      ('found',finder,'Lenovo computer case','Electronics','Found a black Lenovo laptop case with a grey mark beside the zip.','Black','Lenovo','Main campus library','sleeve'),
    ]
    for kind,user,title,category,description,colour,brand,location,illustration in examples:
        cls=models.LostItem if kind=='lost' else models.FoundItem
        if db.scalar(select(cls).where(cls.title==title,cls.reporter_id==user.user_id)):continue
        values=dict(title=title,reporter_id=user.user_id,category=category,description=description,colour=colour,brand=brand,image_ref='demo:'+illustration,status='reported')
        values['location_'+kind]=location;values['date_'+kind]=monday if kind=='lost' else date.today()
        if kind=='found':values['storage_location']='Campus Security front desk'
        item=cls(**values);db.add(item);db.flush()
        rid=item.lost_item_id if kind=='lost' else item.found_item_id
        db.add(models.StatusHistory(related_record_type=kind,related_record_id=rid,previous_status=None,new_status='reported',actor_id=user.user_id,reason='Clearly labelled demonstration-data setup.'))
    db.flush();refresh_matches(db,45,matcher);db.commit()
    return {'accounts':[row[0] for row in DEMO_USERS],'reports':len(examples),'matching':matcher.status()}
