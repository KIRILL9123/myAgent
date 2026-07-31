import json
import asyncio
import re
import logging
from backend.app.agent.llm import chat as chat_with_ollama
from backend.app.memory.memory_service import (
    save_extracted_fact,
    get_all_facts,
    update_fact_timestamp
)

logger = logging.getLogger(__name__)

FACT_EXTRACTION_PROMPT = """You are a factual information extractor. Analyze the conversation history between a user and an AI assistant, and extract important, long-term, verifiable facts about the user.
Ignore short-term conversation details, temporary questions, pleasantries, or general topics. Focus strictly on user preferences, habits, relationships, projects, or other notable persistent attributes.

IMPORTANT: If the conversation contains NO facts worth saving — for example, generic questions 
about weather, time, greetings, factual queries without personal information, or simple tool 
requests (like "what events do I have today") — you MUST return an empty JSON array: []
Do NOT invent or stretch facts just to produce output. An empty result is perfectly valid 
and expected for most routine interactions.

You MUST choose one of these categories for each fact:
- preference (e.g. likes/dislikes, food choice, timing preferences)
- habit (e.g. wakes up at 10 AM, goes to gym on Mondays)
- relationship (e.g. wife is Anna, colleague is Dmitry)
- project (e.g. learning Python, working on Home Agent)
- other (any other persistent fact)

Return a JSON array of objects, where each object has:
- 'content': clear description of the fact in Russian, e.g., 'Не любит встречи по утрам'
- 'category': one of the categories above
- 'confidence': confidence score between 0.0 and 1.0 (float)

Response format MUST be a valid JSON array at the top level:
[
  {"content": "...", "category": "...", "confidence": 0.9}
]
If no facts are worth extracting, return: []"""

DEDUPLICATION_PROMPT = """You are a deduplication assistant. Your job is to determine if a new fact candidate is a duplicate, minor semantic variation, or direct update of an existing fact.

New Fact Candidate:
Content: "{new_content}"
Category: "{new_category}"

Existing Facts:
{existing_facts_str}

Please compare the new fact candidate with the list of existing facts. If it refers to the same preference, habit, relationship, project, or detail (even if phrased slightly differently, or represents an update to it), mark it as a duplicate.
Return a JSON object with:
- "is_duplicate": true or false (boolean)
- "fact_id": the ID of the matched existing fact (integer, null if is_duplicate is false)

Response format MUST be exactly:
{{
  "is_duplicate": false,
  "fact_id": null
}}"""

async def extract_facts_from_conversation(conversation_text: str, source_conversation_id: int | None = None,
                                          source_type: str = "chat", provenance: dict | None = None) -> list[dict]:
    """
    Extracts facts from the conversation text, checks for semantic duplicates against
    existing approved and pending facts, and saves them as pending_approval (if not duplicate).
    Returns list of processed facts.
    """
    messages = [
        {"role": "system", "content": FACT_EXTRACTION_PROMPT},
        {"role": "user", "content": f"Conversation history:\n{conversation_text}"}
    ]
    
    response = await chat_with_ollama(messages, response_format="json", role="extractor")
    if "error" in response:
        logger.warning("LLM error during fact extraction: %s", response["error"])
        return []
        
    content_str = response.get("message", {}).get("content", "")
    logger.debug("Raw fact extraction response: %s", content_str)
    if not content_str:
        return []
        
    # Completion models sometimes wrap valid JSON in a markdown fence even
    # when JSON mode was requested. Accept that harmless wrapper.
    cleaned_content = content_str.strip()
    if cleaned_content.startswith("```"):
        cleaned_content = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned_content, flags=re.IGNORECASE).strip()

    try:
        data = json.loads(cleaned_content)
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse fact extraction response as JSON: %s", e)
        return []
        
    raw_facts = []
    if isinstance(data, list):
        raw_facts = data
    elif isinstance(data, dict):
        if isinstance(data.get("facts"), list):
            raw_facts = data["facts"]
        elif "content" in data or "fact" in data or "text" in data:
            raw_facts = [data]
        else:
            for key, val in data.items():
                if isinstance(val, list):
                    raw_facts = val
                    break
                
    processed_facts = []
    
    # Get existing approved & pending facts for duplicate checking
    all_existing = get_all_facts()
    active_existing = [f for f in all_existing if f["status"] in ("approved", "pending_approval")]
    
    # Gather dedup candidates and run all LLM calls in parallel
    dedup_tasks = []
    dedup_items = []
    existing_facts_str = None
    if active_existing:
        existing_facts_str = "\n".join([
            f"- ID: {f['id']}, Content: '{f['content']}', Category: '{f['category']}'"
            for f in active_existing
        ])

    for item in raw_facts:
        # Some local completion models use `fact`/`text` instead of the
        # requested `content`, and may omit optional metadata. Normalize the
        # aliases so extraction does not silently produce zero facts.
        content = item.get("content") or item.get("fact") or item.get("text") or item.get("description")
        category = item.get("category")
        if not category:
            category = _infer_category(str(content or ""))
        try:
            confidence = float(item.get("confidence", 0.85))
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))
        
        if not content or not category:
            continue
            
        if category not in ("preference", "habit", "relationship", "project", "other"):
            category = "other"

        if active_existing and existing_facts_str:
            messages = [
                {"role": "system", "content": DEDUPLICATION_PROMPT.format(
                    new_content=content, new_category=category,
                    existing_facts_str=existing_facts_str
                )}
            ]
            dedup_tasks.append(chat_with_ollama(messages, response_format="json", role="extractor"))
            dedup_items.append((content, category, confidence))
        else:
            dedup_items.append((content, category, confidence))

    if dedup_tasks:
        dedup_responses = await asyncio.gather(*dedup_tasks, return_exceptions=True)
        for i, resp in enumerate(dedup_responses):
            content, category, confidence = dedup_items[i]
            if isinstance(resp, Exception):
                logger.warning("Deduplication call failed for %r: %s", content, resp)
                dedup_items[i] = (content, category, confidence, False, None)
                continue
            if not isinstance(resp, dict) or resp.get("status") == "error":
                logger.warning("Deduplication model request failed for %r: %s", content, resp)
                dedup_items[i] = (content, category, confidence, False, None)
                continue
            dedup_message = resp.get("message", {})
            if not isinstance(dedup_message, dict):
                logger.warning("Deduplication response has no message object for %r", content)
                dedup_items[i] = (content, category, confidence, False, None)
                continue
            dedup_content_str = dedup_message.get("content", "")
            logger.debug("Deduplication response for %r: %s", content, dedup_content_str)
            try:
                dedup_data = json.loads(dedup_content_str) if dedup_content_str else {}
                is_duplicate_raw = dedup_data.get("is_duplicate", False)
                is_duplicate = str(is_duplicate_raw).lower() == "true" if not isinstance(is_duplicate_raw, bool) else is_duplicate_raw
                raw_id = dedup_data.get("fact_id")
                duplicate_id = int(raw_id) if raw_id is not None and str(raw_id).lower() != "null" else None
            except Exception as e:
                logger.warning("Deduplication parse error for %r: %s", content, e)
                is_duplicate, duplicate_id = False, None
            dedup_items[i] = (content, category, confidence, is_duplicate, duplicate_id)
    else:
        dedup_items = [(c, cat, conf, False, None) for c, cat, conf in dedup_items]

    for content, category, confidence, is_duplicate, duplicate_id in dedup_items:
        if is_duplicate and duplicate_id:
            # Verify the duplicate ID actually exists in our active list
            exists_in_active = any(f["id"] == duplicate_id for f in active_existing)
            if exists_in_active:
                logger.info("Detected duplicate of fact #%s; updating timestamp", duplicate_id)
                update_fact_timestamp(duplicate_id)
                processed_facts.append({
                    "content": content,
                    "category": category,
                    "confidence": confidence,
                    "is_duplicate": True,
                    "fact_id": duplicate_id
                })
                continue
                
        # Reliable preference/habit/project facts are approved automatically;
        # relationships, ambiguous and lower-confidence facts stay in review.
        fact_id, status = save_extracted_fact(
            content=content,
            category=category,
            confidence=confidence,
            source_conversation_id=source_conversation_id,
            source_type=source_type,
            provenance=provenance or {"channel": source_type},
        )
        logger.info("Saved new fact #%s as %s", fact_id, status)
        processed_facts.append({
            "id": fact_id,
            "content": content,
            "category": category,
            "confidence": confidence,
            "is_duplicate": False,
            "status": status
        })
        
    return processed_facts


def _infer_category(content: str) -> str:
    """Best-effort category for completion models that omit the field."""
    lowered = content.lower()
    if any(word in lowered for word in ("предпочит", "люблю", "нравит", "валют", "предпочитаю")):
        return "preference"
    if any(word in lowered for word in ("проект", "планирую", "хочу подключ", "работаю над")):
        return "project"
    if any(word in lowered for word in ("жена", "муж", "друг", "коллег", "семь")):
        return "relationship"
    if any(word in lowered for word in ("каждый день", "обычно", "привыч", "встаю", "работаю по")):
        return "habit"
    return "other"
