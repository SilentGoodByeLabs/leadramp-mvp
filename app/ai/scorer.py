import os
import json
import logging
from google import genai

logger = logging.getLogger(__name__)


def qualify_lead(name: str, company: str, message: str, source: str) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return {
            "score": 50,
            "summary": "Automated scoring disabled. Manual review required.",
            "follow_up": "",
        }

    prompt = f"""
    You are a Senior Sales Development Representative.
    Qualify this inbound lead.

    Lead Data:
    Name: {name}
    Company: {company}
    Source: {source}
    Message: {message}

    Task:
    1. Score buying intent 0-100.
    2. Write one tactical sentence for the sales rep (urgency + what they want).
    3. Draft a short, professional, ready-to-send follow-up message to the lead.
       Max 3 sentences. Human tone. No AI-sounding phrases. No emojis.

    Return ONLY valid JSON. No markdown. No explanations.

    {{
      "score": <integer 0-100>,
      "summary": "<string>",
      "follow_up": "<string>"
    }}
    """

    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )

        raw_text = response.text.strip()

        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]

        parsed_data = json.loads(raw_text.strip())

        score = max(0, min(100, int(parsed_data.get("score", 50))))
        summary = str(parsed_data.get("summary", "No summary.")).strip()
        follow_up = str(parsed_data.get("follow_up", "")).strip()

        return {"score": score, "summary": summary, "follow_up": follow_up}

    except Exception as e:
        logger.error(f"Lead qualification failed: {str(e)}")
        return {
            "score": 0,
            "summary": "Automated scoring unavailable. Manual review required.",
            "follow_up": "",
        }
