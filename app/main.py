import os
import logging
from typing import List

from fastapi import (
    FastAPI,
    Depends,
    status,
    BackgroundTasks,
    Form,
    Request,
)
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import APP_NAME, ENVIRONMENT, BASE_DIR
from app.db import Base, engine, get_db, SessionLocal
from app.models import Lead
from app.schemas import LeadCreate, LeadRead
from app.ai.scorer import qualify_lead

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=APP_NAME,
    version="0.3.0",
    description="AI lead intake and follow-up engine for service businesses.",
)

templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))


@app.get("/health")
def health():
    return {
        "status": "ok",
        "app": APP_NAME,
        "environment": ENVIRONMENT,
        "ai_enabled": bool(os.getenv("GEMINI_API_KEY")),
    }


def process_lead_with_ai(
    lead_id: int,
    name: str,
    company: str,
    message: str,
    source: str,
):
    """
    Background task that qualifies a lead using AI.
    Used by the JSON API.
    """
    db = SessionLocal()
    try:
        logger.info(f"Starting AI qualification for Lead {lead_id}")
        ai_result = qualify_lead(name, company, message, source)

        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if lead:
            lead.score = ai_result.get("score", 0)
            lead.ai_summary = ai_result.get("summary", "No summary generated.")
            lead.status = "qualified" if lead.score >= 70 else "nurturing"
            db.commit()
            logger.info(f"Lead {lead_id} scored: {lead.score}")
    except Exception as e:
        logger.error(f"Background AI task failed: {e}")
    finally:
        db.close()


@app.post("/leads", response_model=LeadRead, status_code=status.HTTP_201_CREATED)
def create_lead(
    payload: LeadCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    lead_data = payload.model_dump(exclude_none=True)
    lead = Lead(**lead_data)

    db.add(lead)
    db.commit()
    db.refresh(lead)

    background_tasks.add_task(
        process_lead_with_ai,
        lead.id,
        lead.name,
        lead.company or "",
        lead.message or "",
        lead.source,
    )

    return lead


@app.get("/leads", response_model=List[LeadRead])
def list_leads(limit: int = 20, db: Session = Depends(get_db)):
    safe_limit = min(max(limit, 1), 100)
    return (
        db.query(Lead)
        .order_by(Lead.created_at.desc())
        .limit(safe_limit)
        .all()
    )


def empty_form():
    return {
        "name": "",
        "email": "",
        "phone": "",
        "company": "",
        "source": "demo_page",
        "message": "",
    }


@app.get("/demo", response_class=HTMLResponse)
def demo_page(request: Request, db: Session = Depends(get_db)):
    recent_leads = (
        db.query(Lead)
        .order_by(Lead.created_at.desc())
        .limit(5)
        .all()
    )

    return templates.TemplateResponse(
        "demo.html",
        {
            "request": request,
            "lead": None,
            "error": None,
            "recent_leads": recent_leads,
            "form": empty_form(),
        },
    )


@app.post("/demo", response_class=HTMLResponse)
def demo_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(""),
    phone: str = Form(""),
    company: str = Form(""),
    source: str = Form("demo_page"),
    message: str = Form(""),
    db: Session = Depends(get_db),
):
    name = name.strip()
    email = email.strip()
    phone = phone.strip()
    company = company.strip()[:180]
    source = source.strip() or "demo_page"
    message = message.strip()[:5000]

    form = {
        "name": name,
        "email": email,
        "phone": phone,
        "company": company,
        "source": source,
        "message": message,
    }

    error = None
    lead = None

    if len(name) < 2:
        error = "Name must be at least 2 characters."
    elif not email and not phone:
        error = "Either email or phone is required."
    elif email and "@" not in email:
        error = "Email format looks invalid."
    else:
        lead = Lead(
            name=name,
            email=email or None,
            phone=phone or None,
            company=company or None,
            source=source,
            message=message or None,
        )

        db.add(lead)
        db.commit()
        db.refresh(lead)

        # For the demo page, qualify immediately so the client sees the result.
        ai_result = qualify_lead(
            lead.name,
            lead.company or "",
            lead.message or "",
            lead.source,
        )

        lead.score = ai_result.get("score", 0)
        lead.ai_summary = ai_result.get("summary", "No summary generated.")
        lead.status = "qualified" if lead.score >= 70 else "nurturing"

        db.commit()
        db.refresh(lead)

    recent_leads = (
        db.query(Lead)
        .order_by(Lead.created_at.desc())
        .limit(5)
        .all()
    )

    response_status = status.HTTP_200_OK if not error else status.HTTP_422_UNPROCESSABLE_ENTITY

    return templates.TemplateResponse(
        "demo.html",
        {
            "request": request,
            "lead": lead,
            "error": error,
            "recent_leads": recent_leads,
            "form": form,
        },
        status_code=response_status,
    )
