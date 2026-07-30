import json
from backend.app.agent.llm import chat as chat_with_ollama

RELATION_PROMPT = """You are a semantic relationship builder. Analyze the connection between a newly approved fact about the user and a list of existing approved facts.
Identify if there are any meaningful semantic relationships between the new fact and the existing facts.

The relation type MUST be chosen strictly from this list:
- related_to: the facts are related or share context
- contradicts: the new fact contradicts or invalidates the existing fact
- clarifies: the new fact clarifies, refines, or adds detail to the existing fact
- causes: the new fact causes or implies the existing fact

Return a JSON array of objects representing relations. Each object MUST have:
- 'fact_b_id': the integer ID of the existing fact
- 'relation_type': one of: 'related_to', 'contradicts', 'clarifies', 'causes'

Response format MUST be exactly:
[
  {{"fact_b_id": 2, "relation_type": "related_to"}}
]"""

async def suggest_relations(new_fact: dict, existing_facts: list[dict]) -> list[dict]:
    """
    Given a new approved fact and a list of existing approved facts, calls the LLM
    to suggest relations between the new fact and any of the existing ones.
    Returns a list of suggested relations: [{"fact_b_id": int, "relation_type": str}].
    """
    if not existing_facts:
        return []
        
    existing_facts_str = "\n".join([
        f"- ID: {f['id']}, Content: '{f['content']}', Category: '{f['category']}'"
        for f in existing_facts
    ])
    
    prompt_user_content = (
        f"Newly Approved Fact:\n"
        f"- ID: {new_fact['id']}, Content: '{new_fact['content']}', Category: '{new_fact['category']}'\n\n"
        f"Existing Approved Facts:\n"
        f"{existing_facts_str}"
    )
    
    messages = [
        {"role": "system", "content": RELATION_PROMPT},
        {"role": "user", "content": prompt_user_content}
    ]
    
    response = await chat_with_ollama(messages, response_format="json")
    if "error" in response:
        print(f"[RelationBuilder] LLM Error: {response['error']}")
        return []
        
    content_str = response.get("message", {}).get("content", "")
    if not content_str:
        return []
        
    try:
        data = json.loads(content_str)
    except json.JSONDecodeError as e:
        print(f"[RelationBuilder] Failed to parse LLM response as JSON: {e}")
        return []
        
    suggestions = []
    if isinstance(data, list):
        suggestions = data
    elif isinstance(data, dict):
        for key, val in data.items():
            if isinstance(val, list):
                suggestions = val
                break
                
    valid_relations = ("related_to", "contradicts", "clarifies", "causes")
    processed_suggestions = []
    
    for sug in suggestions:
        fact_b_id = sug.get("fact_b_id")
        rel_type = sug.get("relation_type")
        
        if fact_b_id is None or not rel_type:
            continue
            
        try:
            fact_b_id = int(fact_b_id)
        except (ValueError, TypeError):
            continue
            
        if rel_type not in valid_relations:
            rel_type = "related_to"
            
        # Ensure we only refer to facts that actually exist in existing_facts
        if any(f["id"] == fact_b_id for f in existing_facts):
            processed_suggestions.append({
                "fact_b_id": fact_b_id,
                "relation_type": rel_type
            })
            
    return processed_suggestions
