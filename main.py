from fastapi import FastAPI, Query
from query_engine import fetch_matching_employees, format_response

app = FastAPI(title="Employee Info API")

@app.get("/search")
def search_employee(q: str = Query(..., description="Your query in Arabic or English")):
    records = fetch_matching_employees(q.strip())
    return format_response(records)
