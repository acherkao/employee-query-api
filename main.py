import json
from fastapi import FastAPI
from pydantic import BaseModel
from llm_parser import parse_query_to_filter
from supabase_client import supabase

# --- GLOBAL CACHE FOR SINGLE-USER DEMO ---
# This dictionary will hold the context of the last "list-based" query.
# It is NOT safe for a multi-user environment.
LAST_CONTEXT_CACHE = {}

app = FastAPI(title="Stateless Demo API with Context Cache")


@app.get("/")
def read_root():
    """A simple health check endpoint for deployment platforms like Render."""
    return {"status": "ok", "message": "Welcome to the Employee Q&A API!"}


class ChatRequest(BaseModel):
    query: str

def detect_language(text: str) -> str:
    """Detects if the primary language of the text is Arabic or English."""
    arabic_chars = sum(1 for char in text if '\u0600' <= char <= '\u06FF')
    return 'ar' if arabic_chars > 2 else 'en'

def format_to_string_message(intent: str, raw_results: list, parsed_json: dict | None, lang: str = 'en') -> str:
    """
    Builds a single, formatted string message as the final output and manages the global cache.
    """
    global LAST_CONTEXT_CACHE

    # --- Cache Management: Decide whether to save or clear context ---
    if intent in ["filter", "ordered_list", "highest_total_compensation"]:
        if not raw_results:
            LAST_CONTEXT_CACHE = {} # Clear cache if no results are found
            return "No matching records found."
        
        # This is a list-based query, so we SAVE its results to the cache for follow-ups.
        LAST_CONTEXT_CACHE = {"raw_results": raw_results}
        print(f"[DEBUG] Caching {len(raw_results)} records for next turn.")
        
        # --- Specific Formatting for Filter Intent ---
        if intent == "filter" and len(raw_results) == 1 and parsed_json:
            record = raw_results[0]
            requested_columns = parsed_json.get("columns")

            # CASE 1: A specific field was requested
            if requested_columns:
                name = (record.get("full_name_en") or record.get("full_name")) if lang != 'ar' else record.get("full_name")
                
                req_cols_lower = [c.lower() for c in requested_columns]
                if 'total_loan' in req_cols_lower or 'remaining_loan' in req_cols_lower:
                    total_loan = record.get('Total_Loan', 0) or 0
                    if total_loan > 0:
                        remaining_loan = record.get('Remaining_Loan', 0) or 0
                        if lang == 'ar':
                            return f"نعم، لدى '{name}' قرض إجمالي بقيمة {total_loan:,.0f} والمبلغ المتبقي هو {remaining_loan:,.0f}."
                        else:
                            return f"Yes, '{name}' has a total loan of {total_loan:,.0f} with {remaining_loan:,.0f} remaining."
                    else:
                        if lang == 'ar':
                            return f"لا، ليس لدى '{name}' أي قروض قائمة."
                        else:
                            return f"No, '{name}' does not have any loans."

                details_list = [
                    f"{col.replace('_', ' ').title()}: {record.get(col)}"
                    for col in requested_columns if col.lower() not in ["full_name", "full_name_en"] and record.get(col) is not None
                ]
                details_str = ", ".join(details_list)
                if lang == 'ar':
                     return f"'{name}' لديه {details_str}."
                else:
                    return f"For '{name}', the {details_str}."

            # CASE 2: A general detail request
            else:
                details = []
                for key, value in record.items():
                    if value is not None and key not in ['id', 'created_at']:
                        formatted_key = key.replace('_', ' ').title()
                        details.append(f"- {formatted_key}: {value}")
                
                name = record.get('full_name') if lang == 'ar' else (record.get('full_name_en') or record.get('full_name'))
                header = f"إليك تفاصيل '{name}':\n" if lang == 'ar' else f"Here are the details for '{name}':\n"
                return header + "\n".join(details)

        # --- Specific Formatting for Ordered List Intent ---
        elif intent == "ordered_list" and parsed_json:
            p = parsed_json
            order_col = p.get("order_by_column", "value")
            is_ascending = p.get("ascending", False)
            limit = p.get("limit", len(raw_results))
            
            lines = []
            for record in raw_results:
                name = (record.get('full_name_en') or record.get('full_name')) if lang != 'ar' else record.get('full_name')
                value = record.get(order_col)
                formatted_value = f"{value:,.2f}" if isinstance(value, (int, float)) else f"{value:,}"
                lines.append(f"- {name}: {formatted_value}")
            
            order_col_formatted = order_col.replace('_', ' ').title()
            ranking_word = "Bottom" if is_ascending else "Top"
            
            if lang == 'ar':
                ranking_word_ar = "أقل" if is_ascending else "أعلى"
                header = f"إليك {ranking_word_ar} {limit} موظفين حسب '{order_col_formatted}':"
            else:
                header = f"Here are the {ranking_word} {limit} employees by '{order_col_formatted}':"
            
            return f"{header}\n" + "\n".join(lines)

        # CASE 3 (Fallback): Filter with multiple results.
        names_key = 'full_name' if lang == 'ar' else 'full_name_en'
        names = [r.get(names_key) or r.get('full_name') for r in raw_results]

        if lang == 'ar':
            message = f"لقد وجدت {len(raw_results)} موظفًا مطابقًا:\n" + "\n".join([f"- {name}" for name in names])
            message += "\n\nيمكنك السؤال عن تفاصيل شخص معين أو طلب 'عرض كل التفاصيل'."
        else:
            message = f"I found {len(raw_results)} matching employees:\n" + "\n".join([f"- {name}" for name in names])
            message += "\n\nYou can ask for details about a specific person or say 'show all details'."
        return message
    else:
        # For any other intent, clear the cache.
        LAST_CONTEXT_CACHE = {}
        print("[DEBUG] Clearing context cache for non-list-based intent.")

    # --- Formatting logic for other intents ---
    if intent == "total_count":
        if not raw_results or "count" not in raw_results[0]:
            return "I could not retrieve the total count."
        total = raw_results[0].get("count", 0)
        if lang == 'ar':
            return f"يوجد إجمالي {total:,} موظف."
        else:
            return f"There are a total of {total:,} employees."

    if intent == "highest_total_compensation" and parsed_json:
        limit = parsed_json.get("limit", 1)
        header_en = f"Here are the Top {limit} Employees by Total Compensation:"
        header_ar = f"إليك أعلى {limit} موظفين حسب إجمالي الراتب:"
        header = header_ar if lang == 'ar' else header_en
        lines = [header, "=" * len(header)]
        for item in raw_results:
            name = (item.get('full_name_en') or item.get('full_name')) if lang != 'ar' else item.get('full_name')
            compensation = item.get('total_compensation', 0)
            lines.append(f"- {name}: {compensation:,.0f}")
        return "\n".join(lines)

    if intent == "find_top_group" and parsed_json:
        if not raw_results: return "Could not determine a top group for this query."
        result = raw_results[0]
        p = parsed_json
        dimension_name = p.get("dimension", "category").replace('_', ' ').title()
        metric_name = p.get("metric_column", "value").replace('_', ' ').title()
        ranking_word = p.get("ranking", "top")
        category = result.get("category")
        value = result.get("value", 0)
        formatted_value = f"{value:,.2f}" if isinstance(value, float) else f"{value:,}"
        return f"The {dimension_name} with the {ranking_word} {metric_name} is '{category}', with a value of {formatted_value}."

    if intent in ["aggregate_count", "conditional_aggregate_count"] and parsed_json:
        dimension = parsed_json.get("dimension", "data").replace('_', ' ').title()
        title = f"Analysis of Count by {dimension}"
        lines = [title, "=" * len(title)]
        for item in raw_results:
            lines.append(f"- {item.get('category')}: {item.get('count'):,}")
        return "\n".join(lines)
    
    if intent == "aggregate_metric" and parsed_json:
        p = parsed_json
        dimension = p.get("dimension", "data").replace('_', ' ').title()
        metric = p.get("metric", "value").capitalize()
        title = f"Analysis of {metric} by {dimension}"
        lines = [title, "=" * len(title)]
        for item in raw_results:
            value = item.get('value', 0)
            formatted_value = f"{value:,.2f}" if isinstance(value, float) else f"{value:,}"
            lines.append(f"- {item.get('category')}: {formatted_value}")
        return "\n".join(lines)
    
    if intent == "unsupported" and parsed_json:
        return parsed_json.get("reason", "I am unable to answer that question.")

    return "I could not process the request."


@app.post("/chat")
def chat_handler(payload: ChatRequest):
    lang = detect_language(payload.query)
    print(f"\n[DEBUG] Received query: '{payload.query}'")
    
    # Pass the current query AND the globally cached context to the parser
    parsed_json = parse_query_to_filter(payload.query, LAST_CONTEXT_CACHE)
    
    print(f"[DEBUG] LLM classified intent: {parsed_json}")
    intent = parsed_json.get("intent")
    raw_results = []
    
    try:
        # --- TOOL ROUTER ---
        if intent == "filter":
            conditions = parsed_json.get("conditions", [])
            columns_to_select = parsed_json.get("columns", ["*"])
            select_string = ",".join(columns_to_select)

            if conditions:
                supa_query = supabase.table("qag_employees").select(select_string)
                for f in conditions:
                    operator, column, value = f.get("operator", "eq"), f.get("column"), f.get("value")
                    query_value = f"%{value}%" if operator == "ilike" else value
                    supa_query = getattr(supa_query, operator)(column, query_value)
                raw_results = supa_query.execute().data
        
        elif intent == "total_count":
            response = supabase.table("qag_employees").select('*', count='exact').execute()
            if response.count is not None:
                raw_results = [{"count": response.count}]

        elif intent == "ordered_list":
            p = parsed_json
            response = supabase.rpc('get_ordered_employees', {'order_by_column': p["order_by_column"], 'is_ascending': p["ascending"], 'limit_count': p["limit"]}).execute()
            raw_results = response.data

        elif intent == "highest_total_compensation":
            p = parsed_json
            limit = p.get("limit", 1)
            response = supabase.rpc('get_top_employees_by_total_compensation', {'limit_count': limit}).execute()
            raw_results = response.data

        elif intent == "aggregate_count":
            dimension = parsed_json["dimension"]
            response = supabase.rpc('get_counts_by_dimension', {'dimension_column': dimension}).execute()
            raw_results = response.data

        elif intent == "aggregate_metric":
            p = parsed_json
            response = supabase.rpc('get_aggregate_by_dimension', {'metric_column': p["metric_column"], 'dimension_column': p["dimension"], 'metric_type': p["metric"]}).execute()
            raw_results = response.data
        
        elif intent == "conditional_aggregate_count":
            p = parsed_json
            conditions = p.get("conditions", [])
            response = supabase.rpc('get_conditional_counts_by_dimension', {'dimension_column': p["dimension"], 'filters': conditions}).execute()
            raw_results = response.data
        
        elif intent == "find_top_group":
            p = parsed_json
            is_desc = (p.get("ranking") == "highest")
            response = supabase.rpc('get_top_category_by_metric', {'dimension_column': p["dimension"], 'metric_column': p["metric_column"], 'metric_type': p["metric"], 'is_descending': is_desc}).execute()
            raw_results = response.data
        
        # Intent 'unsupported' requires no data fetching, it's handled by the formatter.

    except Exception as e:
        print(f"[ERROR] Error executing intent '{intent}': {e}")
        return {"message": f"An error occurred while processing your request: {e}"}

    final_message = format_to_string_message(intent, raw_results, parsed_json, lang)
    
    return {"message": final_message}
