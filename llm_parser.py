import openai
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def parse_query_to_filter(query: str):
    system_prompt = """
You are a helpful assistant that transforms user natural language queries in Arabic or English
into structured JSON filters for a Supabase SQL-like API. Use the column names below to map logic.

Available columns: [Full_Name, Rank, Marital_Status, Base_Salary, Housing_Allowance, Last_Leave_Duration_Days, Position]

Only respond with a JSON like:
{"filter": {"column": "...", "operator": "...", "value": ...}}

Supported operators: eq, gt, gte, lt, lte, ilike
"""

    user_prompt = f"Query: {query}"

    try:
        completion = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0
        )
        result = completion.choices[0].message.content.strip()
        return eval(result) if result.startswith("{") else None
    except Exception as e:
        print("LLM parsing error:", e)
        return None
