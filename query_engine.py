from supabase_client import supabase

def fetch_matching_employees(query: str):
    # Simplistic keyword-based matching across multiple columns
    response = supabase.table("employees").select("*").ilike("Full_Name", f"%{query}%").execute()
    results = response.data

    if not results:
        response = supabase.table("employees").select("*").ilike("Position", f"%{query}%").execute()
        results = response.data

    return results

def format_response(records):
    if not records:
        return {"message": "لم يتم العثور على نتائج. No results found."}

    formatted = []
    for r in records:
        formatted.append({
            "👤 الاسم الكامل": r["Full_Name"],
            "🎖️ الرتبة": r["Rank"],
            "🛡️ المنصب": r["Position"],
            "💰 الراتب الأساسي": f"{r['Base_Salary']} QAR",
            "🏠 بدل السكن": f"{r['Housing_Allowance']} QAR",
            "📅 تاريخ آخر إجازة": r["Last_Leave_Date"],
            "🧮 مدة الإجازة": f"{r['Last_Leave_Duration_Days']} يومًا"
        })
    return formatted
