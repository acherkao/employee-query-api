import os
import json # Import the json library
from dotenv import load_dotenv
import openai # Corrected import

# --- Best Practice: Load environment variables at the start ---
load_dotenv()

# --- Correctly instantiate the client and configure the API key ---
# The API key is fetched from environment variables and passed directly.
# If OPENAI_API_KEY is in your .env, the client will find it automatically.
# Explicitly passing it like this is also perfectly fine and clear.
client = openai.OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

# In llm_parser.py
# In llm_parser.py

def parse_query_to_filter(query: str):
    system_prompt = """
You are a query analysis engine. Your job is to classify a user's natural language query into a specific intent and extract all parameters into a valid JSON object.

# AVAILABLE INTENTS AND THEIR JSON FORMATS

1.  **intent: "filter"**
    - **Use Case:** Searching for specific records based on conditions.
    - **JSON:** `{"intent": "filter", "conditions": [{"column": "...", "operator": "...", "value": ...}, ...]}`
    - **Example:** "all colonels with salary over 22000" -> `{"intent": "filter", "conditions": [{"column": "rank", "operator": "eq", "value": "عقيد"}, {"column": "base_salary", "operator": "gt", "value": 22000}]}`

2.  **intent: "aggregate_count"**
    - **Use Case:** Counting records grouped by a specific category.
    - **JSON:** `{"intent": "aggregate_count", "dimension": "column_to_group_by"}`
    - **Example:** "married vs single" -> `{"intent": "aggregate_count", "dimension": "marital_status"}`

3.  **intent: "aggregate_metric"**
    - **Use Case:** Calculating a sum, average, min, or max of a numeric column, grouped by a category.
    - **JSON:** `{"intent": "aggregate_metric", "dimension": "column_to_group_by", "metric": "avg|sum|min|max", "metric_column": "column_to_calculate"}`
    - **Example:** "average salary per rank" -> `{"intent": "aggregate_metric", "dimension": "rank", "metric": "avg", "metric_column": "base_salary"}`

4.  **intent: "ordered_list"**
    - **Use Case:** Finding the top or bottom records based on a certain column.
    - **JSON:** `{"intent": "ordered_list", "order_by_column": "...", "ascending": true|false, "limit": integer}`
    - **Example:** "top 5 highest paid" -> `{"intent": "ordered_list", "order_by_column": "base_salary", "ascending": false, "limit": 5}`

5.  **intent: "unsupported"**
    - **Use Case:** When the user's question cannot be answered with the available tools or data.
    - **JSON:** `{"intent": "unsupported", "reason": "A brief explanation"}`
    - **Example:** "what's the weather like?" -> `{"intent": "unsupported", "reason": "I can only answer questions about employee data."}`

6.  **intent: "conditional_aggregate_count"**
    - **Use Case:** Counting records grouped by a category, but only for a subset of data that matches certain conditions.
    - **JSON:** `{"intent": "conditional_aggregate_count", "dimension": "...", "conditions": [{"column": "...", "operator": "...", "value": ...}]}`
    - **Example:** "count of married vs single, but only for Group Commanders" -> `{"intent": "conditional_aggregate_count", "dimension": "marital_status", "conditions": [{"column": "position", "operator": "eq", "value": "قائد مجموعة"}]}`

7.  **intent: "find_top_group"**
    - **Use Case:** Finding which single category/group has the absolute highest or lowest value for a specific calculation (max, avg, sum).
    - **JSON:** `{"intent": "find_top_group", "dimension": "...", "metric_column": "...", "metric": "max|avg|sum|min", "ranking": "highest|lowest"}`
    - **Example:** "Which rank has the highest housing allowance?" -> `{"intent": "find_top_group", "dimension": "rank", "metric_column": "housing_allowance", "metric": "max", "ranking": "highest"}`
    - **Example:** "Which position has the lowest average salary?" -> `{"intent": "find_top_group", "dimension": "position", "metric_column": "base_salary", "metric": "avg", "ranking": "lowest"}`

# AVAILABLE COLUMNS
# For searching by name, use 'full_name' for Arabic queries and 'full_name_en' for English queries.
[full_name, full_name_en, rank, marital_status, base_salary, housing_allowance, last_leave_date, last_leave_duration_days, position]

# RULES
- If the user query includes a name in English, you MUST use the 'full_name_en' column for the filter.
- ALWAYS respond with a valid JSON object.
- Default to the "filter" intent for simple lookups.
- For text comparisons like names or ranks, prefer the `ilike` operator over `eq`.
"""
    # ... rest of your function
# ... rest of the function # ^-- Fixed typo from "oyeperator" to "operator"

    user_prompt = f"Query: {query}"

    try:
        completion = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0,
            # Forcing JSON output is a great feature for reliability
            response_format={"type": "json_object"}
        )
        result_string = completion.choices[0].message.content

        # --- Use the safe json.loads() instead of the dangerous eval() ---
        return json.loads(result_string)

    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        print(f"LLM returned a non-JSON string: {result_string}")
        return None
    except openai.APIError as e:
        # Handle API errors from OpenAI
        print(f"OpenAI API error: {e}")
        return None
    except Exception as e:
        # Handle other potential errors
        print(f"An unexpected error occurred: {e}")
        return None

# Example Usage:
# query = "all employees with a base salary greater than 5000"
# filter_json = parse_query_to_filter(query)
# if filter_json:
#     print(json.dumps(filter_json, indent=2))
