import os
import json
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
except Exception as e:
    logger.error(f"Gemini configuration error: {e}")

def qualify_lead(name: str, company: str, message: str, source: str) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return {
            "score": 50,
            "summary": "Automated scoring disabled. Manual review required.",
        }

    prompt = f"""
    You are a Senior Sales Development Representative.
    Qualify this lead. Score buying intent 0-100. Write a 1-sentence tactical summary.
    Return ONLY valid JSON. No markdown. No explanations.
    
    Name: {name}
    Company: {company}
    Source: {source}
    Message: {message}
    
    JSON format:
    {{
      "score": <integer 0-100>,
      "summary": "<string>"
    }}
    """

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        
        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
                
        parsed_data = json.loads(raw_text.strip())
        score = max(0, min(100, int(parsed_data.get("score", 50))))
        summary = str(parsed_data.get("summary", "No summary.")).strip()
        
        return {"score": score, "summary": summary}

    except Exception as e:
        logger.error(f"Lead qualification failed: {str(e)}")
        return {
            "score": 0,
            "summary": "Automated scoring unavailable. Manual review required.",
        }
