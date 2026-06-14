import json
import google.generativeai as genai
from config import GEMINI_API_KEY, PROFILE

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-2.0-flash")

def analyze_job(title, description):
    prompt = f"""
    Candidate Profile:
    {json.dumps(PROFILE, indent=2)}

    Job Title:
    {title}

    Job Description:
    {description}

    Analyze:
    1. Match skills
    2. Check experience
    3. Decide APPLY or SKIP

    Rules:
    - Senior/Lead roles = SKIP
    - More than 3 years required = SKIP
    - 70%+ skill match = APPLY

    Return ONLY a valid JSON object with the following schema:
    {{"decision": "APPLY or SKIP", "match_percentage": <integer between 0-100>, "reason": "<short reasoning>", "pitch": "<3 lines custom pitch for recruiter>"}}
    """

    response = model.generate_content(prompt)
    try:
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    except Exception:
        return None

def answer_questions(questions):
    prompt = f"""
    Candidate Profile:
    {json.dumps(PROFILE, indent=2)}

    Answer the following job application questions based strictly on the candidate profile.
    Questions:
    {json.dumps(questions, indent=2)}
    
    Return ONLY a valid JSON object where keys are the exact questions and values are your generated answers.
    """
    response = model.generate_content(prompt)
    try:
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    except Exception:
        return {}