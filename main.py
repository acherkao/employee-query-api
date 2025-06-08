# main.py - Final Stateless Rich Response Engine

import json
from fastapi import FastAPI
from pydantic import BaseModel
from llm_parser import parse_query_to_filter # Your powerful multi-tool parser
from supabase_client import supabase

app = FastAPI(title="Stateless Employee Info API")

# --- DATA MODELS ---
# Back to the simplest request model, as requested.
class ChatRequest(BaseModel):
    query: str

# In main.py, near the top with other helpers

def detect_language(text: str) -> str:
    """Detects if the primary language of the text is Arabic or English."""
    # A simple heuristic: check for a significant number of Arabic characters.
    arabic_chars = sum(1 for char in text if '\u0600' <= char <= '\u06FF')
    if arabic_chars > 2:  # A small threshold to avoid being triggered by single words
        return 'ar'
    return 'en'

# --- HELPER FORMATTERS ---
def format_detailed_records(records: list) -> list:
    """Formats full employee records for the 'detailed_results' field."""
    if not records: return []
    return [
        {
            "👤 الاسم الكامل": r.get("full_name"),
            "🎖️ الرتبة": r.get("rank"),
            "🛡️ المنصب": r.get("position"),
            "💰 الراتب الأساسي": f"{r.get('base_salary', 0)} QAR",
            "🏠 بدل السكن": f"{r.get('housing_allowance', 0)} QAR",
            "📅 تاريخ آخر إجازة": r.get("last_leave_date"),
            "🧮 مدة الإجازة": f"{r.get('last_leave_duration_days', 0)} يومًا"
        } for r in records
    ]

# In main.py

def create_rich_response(intent: str, raw_results: list, parsed_json: dict | None, lang: str = 'en') -> dict:
    """
    Builds the final, structured JSON response based on the intent, supporting multiple languages.
    """
    
    # --- Handler for list-based results ---
    if intent in ["filter", "ordered_list"]:
        if not raw_results:
            return {"response_type": "empty", "message": "No matching records found."}
        
        message = f"I found {len(raw_results)} matching employees."
        if lang == 'ar':
            message = f"لقد وجدت {len(raw_results)} موظفًا مطابقًا."

        return {
            "response_type": "list_summary",
            "message": message,
            "summary_list": [r.get("full_name") for r in raw_results],
            "detailed_results": format_detailed_records(raw_results)
        }
    
    # --- Handler for counting results ---
    if intent in ["aggregate_count", "conditional_aggregate_count"] and parsed_json:
        dimension = parsed_json.get("dimension", "data").replace('_', ' ').title()
        title = f"Analysis of Count by {dimension}"
        if lang == 'ar':
             title = f"تحليل العدد حسب {dimension}" # Simple translation, can be improved
        
        lines = [title, "=" * len(title)]
        for item in raw_results:
            lines.append(f"- {item.get('category')}: {item.get('count'):,}")
        return {"response_type": "analysis", "message": "\n".join(lines)}

    # --- Handler for metric aggregation (avg, sum, etc.) ---
    if intent == "aggregate_metric" and parsed_json:
        p = parsed_json
        dimension = p.get("dimension", "data").replace('_', ' ').title()
        metric = p.get("metric", "value").capitalize()
        title = f"Analysis of {metric} by {dimension}"
        if lang == 'ar':
            title = f"تحليل {metric} حسب {dimension}"

        lines = [title, "=" * len(title)]
        for item in raw_results:
            value = item.get('value', 0)
            formatted_value = f"{value:,.2f}" if isinstance(value, float) else f"{value:,}"
            lines.append(f"- {item.get('category')}: {formatted_value}")
        return {"response_type": "analysis", "message": "\n".join(lines)}

    # --- Handler for finding the top/bottom group ---
    if intent == "find_top_group" and parsed_json:
        if not raw_results:
            return {"response_type": "analysis", "message": "Could not determine a top group for this query."}
        
        result = raw_results[0]
        p = parsed_json
        dimension_name = p.get("dimension", "category").replace('_', ' ').title()
        metric_name = p.get("metric_column", "value").replace('_', ' ').title()
        ranking_word = p.get("ranking", "top")
        category = result.get("category")
        value = result.get("value", 0)
        formatted_value = f"{value:,.2f}" if isinstance(value, float) else f"{value:,}"

        # --- Multilingual Message Assembly ---
        if lang == 'ar':
            # This is a simplified translation map. A more robust solution might be needed for all columns.
            dimension_map_ar = {"Rank": "الرتبة", "Housing Allowance": "بدل السكن", "Position": "المنصب"}
            ranking_map_ar = {"highest": "الأعلى", "lowest": "الأدنى"}
            
            dimension_name_ar = dimension_map_ar.get(dimension_name, dimension_name)
            metric_name_ar = dimension_map_ar.get(metric_name, metric_name)
            ranking_word_ar = ranking_map_ar.get(ranking_word.lower(), ranking_word)
            
            message = f"{dimension_name_ar} التي لديها {ranking_word_ar} {metric_name_ar} هي '{category}'، بقيمة {formatted_value}."
        else:
            message = f"The {dimension_name} with the {ranking_word} {metric_name} is '{category}', with a value of {formatted_value}."
        
        return {"response_type": "analysis", "message": message}

    # --- Handler for unsupported queries ---
    if intent == "unsupported" and parsed_json:
        reason = parsed_json.get("reason", "I am unable to answer that type of question.")
        return {"response_type": "error", "message": reason}
        
    # --- Final fallback if no other condition is met ---
    return {"response_type": "error", "message": "Could not process the request."}

# --- MASTER ENDPOINT ---
@app.post("/chat")
def chat_handler(payload: ChatRequest):
    
    # ...
    lang = detect_language(payload.query) # <-- DETECT LANGUAGE HERE
    print(f"[DEBUG] Detected language: {lang}")
    # ...
    """
    Stateless endpoint that returns a rich, structured response for the client UI to handle.
    It takes only a 'query' and returns a comprehensive JSON object.
    """
    print(f"\n[DEBUG] Received query: '{payload.query}'")
    parsed_json = parse_query_to_filter(payload.query)
    print(f"[DEBUG] LLM classified intent: {parsed_json}")

    if not parsed_json or "intent" not in parsed_json:
        return {"response_type": "error", "message": "I'm sorry, I couldn't understand your request."}

    intent = parsed_json.get("intent")
    raw_results = []
    
    try:
        # --- TOOL ROUTER ---
        if intent == "filter":
            conditions = parsed_json.get("conditions", [])
            if conditions:
                supa_query = supabase.table("qag_employees").select("*")
                for f in conditions:
                    operator, column, value = f.get("operator", "eq"), f.get("column"), f.get("value")
                    query_value = f"%{value}%" if operator == "ilike" else value
                    supa_query = getattr(supa_query, operator)(column, query_value)
                raw_results = supa_query.execute().data
        
        # ADD THIS NEW ELIF BLOCK
        elif intent == "conditional_aggregate_count":
            p = parsed_json
            conditions = p.get("conditions", [])
            # The conditions JSON from the LLM can be passed directly to the function!
            response = supabase.rpc(
                'get_conditional_counts_by_dimension',
                {
                    'dimension_column': p["dimension"],
                    'filters': conditions
                }
            ).execute()
            raw_results = response.data
            return create_rich_response(intent, raw_results, parsed_json, lang)

        
        elif intent == "ordered_list":
            p = parsed_json
            response = supabase.rpc('get_ordered_employees', {'order_by_column': p["order_by_column"], 'is_ascending': p["ascending"], 'limit_count': p["limit"]}).execute()
            raw_results = response.data

        elif intent == "aggregate_count":
            dimension = parsed_json["dimension"]
            response = supabase.rpc('get_counts_by_dimension', {'dimension_column': dimension}).execute()
            raw_results = response.data

        elif intent == "aggregate_metric":
            p = parsed_json
            response = supabase.rpc('get_aggregate_by_dimension', {'metric_column': p["metric_column"], 'dimension_column': p["dimension"], 'metric_type': p["metric"]}).execute()
            raw_results = response.data
        
        
        elif intent == "find_top_group":
            p = parsed_json
            # Translate the LLM's friendly word ("highest") to the function's boolean
            is_desc = (p.get("ranking") == "highest")
            
            response = supabase.rpc(
                'get_top_category_by_metric',
                {
                    'dimension_column': p["dimension"],
                    'metric_column': p["metric_column"],
                    'metric_type': p["metric"],
                    'is_descending': is_desc
                }
            ).execute()
            raw_results = response.data
            # The formatter will now handle the display
            return create_rich_response(intent, raw_results, parsed_json, lang)
        
        # --- ADD THIS ENTIRE 'ELIF' BLOCK HERE ---
        elif intent == "unsupported":
            print("[DEBUG] LLM classified the query as unsupported.")
            # We call the formatter, which will extract the reason from the JSON
            return create_rich_response(intent, [], parsed_json, lang)    
    except Exception as e:
        print(f"[ERROR] Error executing intent '{intent}': {e}")
        return {"response_type": "error", "message": "An error occurred while processing your request."}
