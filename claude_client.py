"""Claude API client for author queries and book title searches."""

import json
import re
import time
import requests
from .config import CLAUDE_URL, CLAUDE_MODEL, ui
from .auth import get_bearer


def claude_author_query(text_excerpt: str, language: str) -> dict:
    token = get_bearer()
    if not token:
        return {"success": False, "error": "No API token"}

    headers = {
        "Content-Type": "application/json",
        "x-api-key": token,
        "anthropic-version": "2023-06-01"
    }

    prompt = f'''You are a literary analysis expert. Based on the following text excerpt from a children's book in {language.title()}, provide specific information about the author.

Text excerpt:
{text_excerpt[:2000]}  # Limit excerpt size

Please respond with ONLY a valid JSON object (no additional text) containing:
- "author": The specific author's name if clearly identifiable, or "Unknown" if not determinable
- "confidence": A number between 0-100 indicating your confidence level
- "reasoning": Brief explanation of why you identified this author or why it's unknown

Focus on actual author identification based on writing style, known works, or explicit mentions in the text.'''

    data = {
        "model": CLAUDE_MODEL,
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        response = requests.post(CLAUDE_URL, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            content = result["content"][0]["text"].strip()
            
            # Try to parse as JSON
            try:
                parsed = json.loads(content)
                return {"success": True, "data": parsed}
            except json.JSONDecodeError:
                # If not valid JSON, extract key information
                return {"success": True, "data": {"author": "Unknown", "confidence": 0, "reasoning": "Could not parse response"}}
        else:
            return {"success": False, "error": f"API error: {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def search_book_titles(lang, api_key, max_attempts=3):
    ui.log(f"🔍 Searching for book titles in {lang}...")
    ui.set_status(f"Querying Claude for {lang} book titles")

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }
    prompt = (
        f"List as many popular children's book titles as possible that were originally written in {lang} language. "
        f"Focus on books that were originally published in {lang}, not translations. "
        f"Include classic and contemporary children's books in {lang}. "
        "Provide at least 50 unique book titles, one per line, without author names or additional information."
    )
    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 1000,
        "temperature": 0.7,
        "messages": [{"role": "user", "content": prompt}]
    }

    for attempt in range(1, max_attempts + 1):
        try:
            ui.set_status(f"Claude attempt {attempt}/{max_attempts}")
            resp = requests.post(CLAUDE_URL, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            content = resp.json().get("content", [])
            results = []

            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    for line in part["text"].splitlines():
                        line = line.strip()
                        # Remove numbering, bullets, and other prefixes
                        line = re.sub(r"^[-•\d\.)\s]*", "", line).strip()
                        # Remove quotes if present
                        line = re.sub(r'^["\'](.+?)["\']$', r'\1', line)
                        # Filter out generic phrases and very short lines
                        if (line and len(line) > 2 and 
                            not line.lower().startswith(('popular children', 'popular kids', 'famous children', 'classic children')) and
                            'originally written in' not in line.lower()):
                            results.append(line)

            # Remove duplicates while preserving order
            seen = set()
            unique_results = []
            for title in results:
                if title.lower() not in seen:
                    seen.add(title.lower())
                    unique_results.append(title)

            ui.log(f"✅ Found {len(unique_results)} book titles from Claude")
            return unique_results

        except Exception as e:
            ui.log(f"⚠️ Attempt {attempt} failed: {e}")
            if attempt < max_attempts:
                wait = 2 ** (attempt - 1)
                ui.log(f"⏳ Retrying in {wait}s...")
                time.sleep(wait)
            else:
                ui.log("❌ All attempts to contact Claude failed.")
                return []