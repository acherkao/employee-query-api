# Employee Query API

This API allows querying military employee records in Arabic or English using natural language.

## Run locally

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

## Example Query

```
GET /search?q=بندر
```

Response:

```json
[
  {
    "👤 الاسم الكامل": "بندر نواف معجب المري",
    "🎖️ الرتبة": "Lieutenant General",
    "🛡️ المنصب": "قائد عام",
    "💰 الراتب الأساسي": "19500 QAR",
    "🏠 بدل السكن": "6000 QAR",
    "📅 تاريخ آخر إجازة": "2025-01-26",
    "🧮 مدة الإجازة": "40 يومًا"
  }
]
```
