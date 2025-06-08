from supabase_client import supabase

def fetch_matching_employees(query: str):
    # Simplistic keyword-based matching across multiple columns
    response = supabase.table("qag_employees").select("*").ilike("full_name", f"%{query}%").execute()
    results = response.data

    if not results:
        response = supabase.table("qag_employees").select("*").ilike("position", f"%{query}%").execute()
        results = response.data

    return results

def format_response(records):
    if not records:
        return {"message": "لم يتم العثور على نتائج. No results found."}

    formatted = []
    for r in records:
        formatted.append({
            "👤 الاسم الكامل": r["full_name"],
            "🎖️ الرتبة": r["rank"],
            "🛡️ المنصب": r["position"],
            "💰 الراتب الأساسي": f"{r['base_salary']} QAR",
            "🏠 بدل السكن": f"{r['housing_allowance']} QAR",
            "📅 تاريخ آخر إجازة": r["last_leave_date"],
            "🧮 مدة الإجازة": f"{r['last_leave_duration_days']} يومًا"
        })
    return formatted
