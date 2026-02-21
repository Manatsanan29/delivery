from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

app = FastAPI(title="Dashboard KPI", version="1.0.0", docs_url=None, redoc_url=None)

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# -------------------------
# OpenAPI JSON (Swagger ใช้ไฟล์นี้)
# -------------------------
_openapi_cache: Dict[str, Any] | None = None

@app.get("/openapi.json", include_in_schema=False)
def openapi_json():
    global _openapi_cache
    if _openapi_cache is None:
        _openapi_cache = get_openapi(
            title=app.title,
            version=app.version,
            routes=app.routes,
        )
    return _openapi_cache

# -------------------------
# Docs (Swagger UI) + inject CSS/JS แบบ "ไม่ใช้ middleware"
# -------------------------
@app.get("/docs", include_in_schema=False)
def custom_docs() -> HTMLResponse:
    resp = get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="API Console",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_favicon_url="/favicon.ico",
        swagger_ui_parameters={
            "docExpansion": "none",
            "defaultModelsExpandDepth": -1,
            "displayRequestDuration": True,
            "filter": True,
            "tryItOutEnabled": True,
        },
    )

    # ✅ inject theme ของเราเข้าไปใน <head> (ปลอดภัย)
    html = resp.body.decode("utf-8")
    inject = """
<link rel="stylesheet" href="/static/swagger.css">
<script src="/static/swagger.js"></script>
"""
    html = html.replace("</head>", inject + "\n</head>")
    return HTMLResponse(html)

# -------------------------
# หน้าแรกให้เด้งไป dashboard
# -------------------------
@app.get("/")
def root():
    return RedirectResponse(url="/dashboard")

# -------------------------
# หน้า Dashboard (สวย)
# -------------------------
@app.get("/dashboard")
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "today_done": 58,
        "today_target": 120,
        "on_time_rate": 92,
        "avg_rating": 4.8,
        "in_transit": 15,
        "pending": 32,
        "completed": 73,
        "top_couriers": [
            {"name": "Somchai P.", "deliveries": 94, "rating": 4.9},
            {"name": "Manee K.", "deliveries": 88, "rating": 4.7},
            {"name": "Aek W.", "deliveries": 72, "rating": 4.6},
        ],
    })

@app.get("/favicon.ico")
def favicon():
    return {}

# -------------------------
# Export PDF (demo)
# -------------------------
@app.get("/export/pdf")
def export_pdf(month: str = "2026-09"):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ยังไม่ได้ติดตั้ง reportlab: {e}")

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 800, f"Monthly Report: {month}")
    c.setFont("Helvetica", 11)
    c.drawString(50, 780, f"Generated at: {datetime.now().isoformat(timespec='seconds')}")
    c.showPage()
    c.save()

    return StreamingResponse(
        BytesIO(buf.getvalue()),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report_{month}.pdf"'},
    )
from fastapi import Form

# ----- storage แบบง่าย (in-memory) -----
EMPLOYEES = {}      # key: employee_id
DAILY_RECORDS = []  # list of dict

@app.get("/form")
def form_page(request: Request):
    return templates.TemplateResponse("form.html", {"request": request, "employee_msg": "", "record_msg": ""})

@app.post("/api/employees")
def create_employee_form(
    request: Request,
    employee_id: str = Form(...),
    name: str = Form(...),
    area_name: str = Form(...),
    zone_code: str = Form(...),
    grade: str = Form(...),
):
    EMPLOYEES[employee_id] = {
        "employee_id": employee_id,
        "name": name,
        "area_name": area_name,
        "zone_code": zone_code,
        "grade": grade,
    }
    return templates.TemplateResponse("form.html", {
        "request": request,
        "employee_msg": f"บันทึกพนักงาน {employee_id} สำเร็จ",
        "record_msg": "",
    })

@app.post("/api/daily-records")
def add_daily_record_form(
    request: Request,
    employee_id: str = Form(...),
    work_date: str = Form(...),
    delivered_boxes: int = Form(...),
    speed_score: float = Form(...),
    volume_score: float = Form(...),
    csat_score: float = Form(...),
):
    if employee_id not in EMPLOYEES:
        return templates.TemplateResponse("form.html", {
            "request": request,
            "employee_msg": "",
            "record_msg": f"ไม่พบรหัสพนักงาน {employee_id} (ให้เพิ่มพนักงานก่อน)",
        })

    DAILY_RECORDS.append({
        "employee_id": employee_id,
        "work_date": work_date,
        "delivered_boxes": delivered_boxes,
        "speed_score": speed_score,
        "volume_score": volume_score,
        "csat_score": csat_score,
    })

    return templates.TemplateResponse("form.html", {
        "request": request,
        "employee_msg": "",
        "record_msg": f"บันทึกรายวันของ {employee_id} วันที่ {work_date} สำเร็จ",
    })

# ----- ดูข้อมูลที่บันทึก (เผื่อเช็ค) -----
@app.get("/api/employees")
def list_employees():
    return {"employees": list(EMPLOYEES.values())}

@app.get("/api/daily-records")
def list_daily_records():
    return {"daily_records": DAILY_RECORDS}
