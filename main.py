from fastapi import FastAPI, Query
from query_engine import fetch_matching_employees, format_response
from llm_parser import parse_query_to_filter
from supabase_client import supabase

app = FastAPI(title="Employee Info API")

@app.get("/search")
def search_employee(q: str = Query(..., description="Your query in Arabic or English")):
        # Try LLM-based filtering first
    parsed = parse_query_to_filter(q)
    if parsed and "filter" in parsed:
        f = parsed["filter"]
        supa_query = supabase.table("employees").select("*")
        if f["operator"] == "eq":
            supa_query = supa_query.eq(f["column"], f["value"])
        elif f["operator"] == "gt":
            supa_query = supa_query.gt(f["column"], f["value"])
        elif f["operator"] == "gte":
            supa_query = supa_query.gte(f["column"], f["value"])
        elif f["operator"] == "lt":
            supa_query = supa_query.lt(f["column"], f["value"])
        elif f["operator"] == "lte":
            supa_query = supa_query.lte(f["column"], f["value"])
        elif f["operator"] == "ilike":
            supa_query = supa_query.ilike(f["column"], f["value"])
        results = supa_query.execute().data
        return format_response(results)

    # fallback to basic name/position search
    records = fetch_matching_employees(q.strip())
    return format_response(records)
