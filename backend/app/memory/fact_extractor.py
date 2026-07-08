import json
from backend.app.agent.llm_client import chat_with_ollama
from backend.app.memory.memory_service import (
    save_pending_fact,
    get_all_facts,
    update_fact_timestamp
)

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

async def extract_facts_from_conversation(conversation_text: str, source_conversation_id: int | None = None) -> list[dict]:
    """
    Extracts facts from the conversation text, checks for semantic duplicates against
    existing approved and pending facts, and saves them as pending_approval (if not duplicate).
    Returns list of processed facts.
    """
    messages = [
        {"role": "system", "content": FACT_EXTRACTION_PROMPT},
        {"role": "user", "content": f"Conversation history:\n{conversation_text}"}
    ]
    
    response = await chat_with_ollama(messages, response_format="json")
    if "error" in response:
        print(f"[FactExtractor] LLM Error: {response['error']}")
        return []
        
    content_str = response.get("message", {}).get("content", "")
    print(f"[FactExtractor] Raw content_str: {content_str}")
    if not content_str:
        return []
        
    try:
        data = json.loads(content_str)
    except json.JSONDecodeError as e:
        print(f"[FactExtractor] Failed to parse LLM response as JSON: {e}")
        return []
        
    raw_facts = []
    if isinstance(data, list):
        raw_facts = data
    elif isinstance(data, dict):
        if "content" in data and "category" in data:
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
    
    for item in raw_facts:
        content = item.get("content")
        category = item.get("category")
        confidence = item.get("confidence", 1.0)
        
        if not content or not category:
            continue
            
        # Ensure category is one of the allowed categories
        if category not in ("preference", "habit", "relationship", "project", "other"):
            category = "other"
            
        is_duplicate = False
        duplicate_id = None
        
        if active_existing:
            # Format existing facts for deduplication LLM call
            existing_facts_str = "\n".join([
                f"- ID: {f['id']}, Content: '{f['content']}', Category: '{f['category']}'"
                for f in active_existing
            ])
            
            dedup_messages = [
                {"role": "system", "content": DEDUPLICATION_PROMPT.format(
                    new_content=content,
                    new_category=category,
                    existing_facts_str=existing_facts_str
                )}
            ]
            
            dedup_resp = await chat_with_ollama(dedup_messages, response_format="json")
            if "error" not in dedup_resp:
                dedup_content_str = dedup_resp.get("message", {}).get("content", "")
                print(f"[FactExtractor] Deduplication raw response for '{content}': {dedup_content_str}")
                try:
                    dedup_data = json.loads(dedup_content_str)
                    is_duplicate_raw = dedup_data.get("is_duplicate", False)
                    is_duplicate = str(is_duplicate_raw).lower() == "true" if not isinstance(is_duplicate_raw, bool) else is_duplicate_raw
                    
                    raw_id = dedup_data.get("fact_id")
                    if raw_id is not None and str(raw_id).lower() != "null":
                        duplicate_id = int(raw_id)
                except Exception as e:
                    print(f"[FactExtractor] Deduplication parse error: {e}")
                    
        if is_duplicate and duplicate_id:
            # Verify the duplicate ID actually exists in our active list
            exists_in_active = any(f["id"] == duplicate_id for f in active_existing)
            if exists_in_active:
                print(f"[FactExtractor] Detected duplicate of fact #{duplicate_id}. Updating timestamp.")
                update_fact_timestamp(duplicate_id)
                processed_facts.append({
                    "content": content,
                    "category": category,
                    "confidence": confidence,
                    "is_duplicate": True,
                    "fact_id": duplicate_id
                })
                continue
                
        # If not duplicate, save as pending_approval
        fact_id = save_pending_fact(
            content=content,
            category=category,
            confidence=confidence,
            source_conversation_id=source_conversation_id
        )
        print(f"[FactExtractor] Saved new fact #{fact_id} as pending_approval.")
        processed_facts.append({
            "id": fact_id,
            "content": content,
            "category": category,
            "confidence": confidence,
            "is_duplicate": False,
            "status": "pending_approval"
        })
        
    return processed_facts
