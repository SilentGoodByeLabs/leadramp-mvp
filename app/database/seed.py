import logging

from app.db import SessionLocal
from app.models import Lead

logger = logging.getLogger(__name__)

SAMPLE_LEADS = [
    {
        "name": "Sarah Jenkins",
        "email": "sarah@jenkinsrealty.com",
        "phone": "+15559876543",
        "company": "Jenkins Realty Group",
        "source": "facebook_ad",
        "message": "We are getting 50 leads a day and my team is forgetting to call them. I need automation ASAP. What is your pricing?",
        "score": 92,
        "ai_summary": "High urgency. 50 leads/day with slow follow-up. Asked for pricing. Call today.",
        "follow_up": "Hi Sarah - saw you are handling 50 leads a day and follow-ups are slipping. We can have instant qualification and rep alerts live this week. Are you free for a 15-minute call tomorrow?",
        "status": "qualified",
        "qualified_seconds": 1.4,
    },
    {
        "name": "Amara Okafor",
        "email": "amara@brightsmiledental.com",
        "phone": "+442071234567",
        "company": "Bright Smile Dental",
        "source": "google_search",
        "message": "We miss calls after hours and lose patients to competitors. Can you fix this? Available for a call this week.",
        "score": 84,
        "ai_summary": "Clear pain: after-hours missed calls. Available this week. Book demo now.",
        "follow_up": "Hi Amara - missed after-hours calls are pure lost revenue for the clinic. We can capture and respond within seconds, 24/7. You mentioned this week works - does Thursday suit you?",
        "status": "qualified",
        "qualified_seconds": 1.1,
    },
    {
        "name": "Michael Chen",
        "email": "m.chen@chenlogistics.com",
        "phone": "",
        "company": "Chen Logistics",
        "source": "website_form",
        "message": "Interested in learning more about your services.",
        "score": 55,
        "ai_summary": "Early research stage. No urgency or budget signal. Nurture with a case study.",
        "follow_up": "Hi Michael - thanks for reaching out. Here is a 2-minute case study on how similar logistics teams cut manual follow-up by 80%. Happy to answer any questions.",
        "status": "nurturing",
        "qualified_seconds": 0.9,
    },
    {
        "name": "Promo Bot",
        "email": "winner@cheapshoes.biz",
        "phone": "",
        "company": "",
        "source": "website_form",
        "message": "click here to buy cheap shoes now",
        "score": 5,
        "ai_summary": "Spam. No business intent. Auto-archived.",
        "follow_up": None,
        "status": "nurturing",
        "qualified_seconds": 0.6,
    },
]


def seed_sample_leads() -> None:
    db = SessionLocal()
    try:
        added = 0
        for item in SAMPLE_LEADS:
            if item.get("email"):
                exists = db.query(Lead).filter(Lead.email == item["email"]).first()
            else:
                exists = db.query(Lead).filter(Lead.name == item["name"]).first()

            if exists:
                continue

            db.add(Lead(**item))
            added += 1

        db.commit()

        if added:
            logger.info(f"Seeded {added} sample lead(s).")
    except Exception as e:
        db.rollback()
        logger.error(f"Seeding failed: {e}")
    finally:
        db.close()
