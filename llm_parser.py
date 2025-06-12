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
- CONTEXT: The previous query returned ['Salman Al Hajri', 'Nawaf Al Naimi']
- CURRENT QUERY: "what is his rank?"
- YOUR THOUGHT PROCESS: The query is ambiguous as "his" could refer to multiple people. I must ask for clarification.
- YOUR JSON OUTPUT: {{"intent": "unsupported", "reason": "Which person are you asking about? Please specify a name from the list."}}

- CONTEXT: The previous query returned ['Salman Al Hajri']
- CURRENT QUERY: "what is his rank?"
- YOUR THOUGHT PROCESS: "His" clearly refers to 'Salman Al Hajri'. The user wants a specific field, 'rank'. I will use the 'filter' intent, resolve the context to a condition on 'full_name', and specify the 'rank' column in the "columns" key to fetch only that data. I will also include 'full_name' for context.
- YOUR JSON OUTPUT: {{"intent": "filter", "conditions": [{{"column": "full_name", "operator": "eq", "value": "Salman Al Hajri"}}], "columns": ["rank", "full_name"]}}

# EXAMPLE OF COMPLEX QUERY
- QUERY: "Who has the highest total compensation?"
- THOUGHT PROCESS: The user is asking for a complex calculation (sum of salary and allowances) that requires a special tool. I will use the `highest_total_compensation` intent.
- JSON OUTPUT: {{"intent": "highest_total_compensation", "limit": 1}}


# AVAILABLE INTENTS AND THEIR JSON FORMATS
1.  **intent: "filter"** - For searching for records.
    `{{"intent": "filter", "conditions": [...], "columns": [...]}}`
2.  **intent: "aggregate_count"** - For counting records grouped by a category.
    `{{"intent": "aggregate_count", "dimension": "..."}}`
3.  **intent: "aggregate_metric"** - For calculating sum, avg, min, or max, grouped by a category.
    `{{"intent": "aggregate_metric", "dimension": "...", "metric": "...", "metric_column": "..."}}`
4.  **intent: "ordered_list"** - For finding top/bottom records based on a SINGLE, EXISTING column.
    `{{"intent": "ordered_list", "order_by_column": "...", "ascending": true|false, "limit": integer}}`
5.  **intent: "highest_total_compensation"** - **USE ONLY** for questions about "total compensation", "total pay", or "salary plus allowances". This calculates the sum of all salary and allowance fields.
    `{{"intent": "highest_total_compensation", "limit": integer}}`
6.  **intent: "conditional_aggregate_count"** - For filtered counting.
    `{{"intent": "conditional_aggregate_count", "dimension": "...", "conditions": [...]}}`
7.  **intent: "find_top_group"** - For finding the single best/worst group based on an aggregation of an EXISTING column.
    `{{"intent": "find_top_group", "dimension": "...", "metric_column": "...", "metric": "...", "ranking": "highest|lowest"}}`
8.  **intent: "total_count"** - For getting the total number of all records.
    `{{"intent": "total_count"}}`
9.  **intent: "unsupported"** - When the query cannot be answered.
    `{{"intent": "unsupported", "reason": "A brief explanation."}}`

# AVAILABLE COLUMNS
- For name searches, use 'full_name' for Arabic and 'full_name_en' for English.
- [military_id, full_name, rank, marital_status, base_salary, civil_clothing_allowance, military_clothing_allowance, housing_allowance, phone_allowance, unit_allowance, social_allowance, transport_allowance, position_allowance, specialty_allowance, risk_allowance, total_loan, remaining_loan, retirement_deduction, position, enlistment_date, birth_date, annual_leave_balance, grant_leave_balance, emergency_leave_balance, last_leave_date, last_leave_duration_days, full_name_en]

# RULES
- ALWAYS respond with a valid JSON object.
- For text comparisons, prefer the `ilike` operator over `eq`.
- DO NOT invent new column names like 'total_compensation'. Use the specific intents provided for complex calculations.
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
