import os
import json
from dotenv import load_dotenv
import openai

# --- Setup ---
load_dotenv()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def parse_query_to_filter(query: str, last_context: dict | None = None) -> dict:
    """
    Classifies a query into an intent. If 'last_context' is provided, it uses it
    to understand follow-up questions for a single-user demo.
    """
    
    # Dynamically build the context part of the prompt
    context_prompt = "No previous context is available. This is a new query."
    if last_context:
        # Create a simplified summary of the last answer for the LLM
        summary_list = [r.get("full_name") for r in last_context.get("raw_results", [])]
        if summary_list:
            context_prompt = f"The previous query returned a list of these people: {summary_list}. The user might be asking a follow-up question about one of them."
    
    system_prompt = f"""
You are a query analysis engine for a single-user demo. You will receive the latest user query and, optionally, the context from the last answer.
Your job is to classify the user's query into an intent and extract all parameters into a valid JSON object.
If the query is a follow-up (e.g., uses 'he', 'she', 'it', 'their'), you MUST use the provided context to resolve it.

# CONTEXT FROM PREVIOUS TURN
{context_prompt}

# EXAMPLE OF CONTEXT RESOLUTION
- CONTEXT: The previous query returned ['Salman Al Hajri']
- CURRENT QUERY: "does he have a loan?"
- YOUR THOUGHT PROCESS: The user is asking about a loan. I will check the `total_loan` and `remaining_loan` columns. I will resolve "he" to 'Salman Al Hajri' and request those columns so the system can formulate a complete answer.
- YOUR JSON OUTPUT: {{"intent": "filter", "conditions": [{{"column": "full_name", "operator": "eq", "value": "Salman Al Hajri"}}], "columns": ["total_loan", "remaining_loan", "full_name"]}}

# AVAILABLE INTENTS AND THEIR JSON FORMATS
1.  **intent: "filter"** - For searching for records. If a user asks for a specific field (e.g., "what is his rank?"), add a "columns" key with the specific database column(s). If no specific columns are asked for, omit the "columns" key.
    `{{"intent": "filter", "conditions": [...], "columns": ["column_name", ...]}}`
2.  **intent: "aggregate_count"** - For counting records grouped by a category. Use this only when a user asks to count "by" or "per" a category (e.g., "count by rank").
    `{{"intent": "aggregate_count", "dimension": "column_to_group_by"}}`
3.  **intent: "aggregate_metric"** - For calculating sum, avg, min, or max, grouped by a category.
    `{{"intent": "aggregate_metric", "dimension": "...", "metric": "...", "metric_column": "..."}}`
4.  **intent: "ordered_list"** - For finding top/bottom records.
    `{{"intent": "ordered_list", "order_by_column": "...", "ascending": true|false, "limit": integer}}`
5.  **intent: "conditional_aggregate_count"** - For filtered counting.
    `{{"intent": "conditional_aggregate_count", "dimension": "...", "conditions": [...]}}`
6.  **intent: "find_top_group"** - For finding the single best/worst group.
    `{{"intent": "find_top_group", "dimension": "...", "metric_column": "...", "metric": "...", "ranking": "highest|lowest"}}`
7.  **intent: "total_count"** - For getting the total number of records, without grouping (e.g., "how many employees are there?").
    `{{"intent": "total_count"}}`
8.  **intent: "unsupported"** - When the query cannot be answered.
    `{{"intent": "unsupported", "reason": "A brief explanation."}}`

# AVAILABLE COLUMNS
- For name searches, use 'full_name' for Arabic and 'full_name_en' for English.
- [military_id, full_name, rank, marital_status, base_salary, civil_clothing_allowance, military_clothing_allowance, housing_allowance, phone_allowance, unit_allowance, social_allowance, transport_allowance, position_allowance, specialty_allowance, risk_allowance, total_loan, remaining_loan, retirement_deduction, position, enlistment_date, birth_date, annual_leave_balance, grant_leave_balance, emergency_leave_balance, last_leave_date, last_leave_duration_days, full_name_en]

# RULES
- ALWAYS respond with a valid JSON object.
- For text comparisons, prefer the `ilike` operator over `eq`.
"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Latest Query: {query}"}
    ]

    try:
        completion = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        print(f"LLM parsing error: {e}")
        return {"intent": "unsupported", "reason": f"An error occurred while analyzing the query: {e}"}
