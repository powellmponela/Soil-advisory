from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .config import BASE_DIR, PUBLIC_PREDICTIONS, SESSION_SECRET, STAFF_ENABLED
from .data_access import load_public_predictions, safe_private_listing
from .security import credentials_valid, is_authenticated

app = FastAPI(title="Soil Advisory Platform", version="0.2.0")
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="lax",
    https_only=True,
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "app" / "templates")


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("public.html", {"request": request})


@app.get("/api/public/summary")
def public_summary():
    df = load_public_predictions()
    if df.empty:
        return {
            "records": 0,
            "districts": 0,
            "municipalities": 0,
            "crops": 0,
            "scenarios": 0,
            "versions": [],
            "status": "No approved predictions published",
        }
    versions = sorted(
        [v for v in df["published_version"].dropna().astype(str).unique().tolist() if v]
    )
    return {
        "records": int(len(df)),
        "districts": int(df["district"].dropna().astype(str).nunique()),
        "municipalities": int(df["municipality"].dropna().astype(str).nunique()),
        "crops": int(df["crop"].dropna().astype(str).nunique()),
        "scenarios": int(df["scenario"].dropna().astype(str).nunique()),
        "versions": versions,
        "status": "Published advisory outputs available",
    }


@app.get("/api/public/filters")
def public_filters():
    df = load_public_predictions()
    return {
        "districts": sorted(df["district"].dropna().astype(str).unique().tolist()),
        "crops": sorted(df["crop"].dropna().astype(str).unique().tolist()),
        "seasons": sorted(df["season"].dropna().astype(str).unique().tolist()),
        "scenarios": sorted(df["scenario"].dropna().astype(str).unique().tolist()),
    }


@app.get("/api/public/advisory")
def public_advisory(
    district: str | None = None,
    crop: str | None = None,
    season: str | None = None,
    scenario: str | None = None,
):
    df = load_public_predictions()
    for col, value in {
        "district": district,
        "crop": crop,
        "season": season,
        "scenario": scenario,
    }.items():
        if value:
            df = df[df[col].astype(str).str.casefold() == value.casefold()]
    return {"count": len(df), "results": df.fillna("").to_dict(orient="records")}


@app.get("/downloads/published-predictions.csv")
def download_published_predictions():
    if not PUBLIC_PREDICTIONS.exists():
        raise HTTPException(status_code=404, detail="No published prediction file available")
    return FileResponse(
        PUBLIC_PREDICTIONS,
        media_type="text/csv",
        filename="soil_advisory_published_predictions.csv",
    )


@app.get("/staff/login", response_class=HTMLResponse)
def login_page(request: Request):
    if not STAFF_ENABLED:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Staff access is not configured on this deployment.",
            },
            status_code=503,
        )
    if is_authenticated(request):
        return RedirectResponse("/staff", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/staff/login", response_class=HTMLResponse)
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if not credentials_valid(username, password):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid username or password."},
            status_code=401,
        )
    request.session["authenticated"] = True
    request.session["username"] = username
    return RedirectResponse("/staff", status_code=303)


@app.post("/staff/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


def require_staff(request: Request):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Authentication required")


@app.get("/staff", response_class=HTMLResponse)
def staff_home(request: Request):
    if not STAFF_ENABLED:
        return RedirectResponse("/staff/login", status_code=303)
    if not is_authenticated(request):
        return RedirectResponse("/staff/login", status_code=303)
    return templates.TemplateResponse("staff.html", {"request": request})


@app.get("/api/staff/list/{area}")
def staff_listing(request: Request, area: str, path: str = ""):
    require_staff(request)
    try:
        entries = safe_private_listing(area, path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"area": area, "path": path, "entries": entries}


@app.get("/health")
def health():
    return JSONResponse({"status": "ok"})
