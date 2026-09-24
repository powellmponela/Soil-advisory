from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from .config import BASE_DIR, SESSION_SECRET, STAFF_ENABLED
from .data_access import load_public_predictions, safe_private_listing
from .security import credentials_valid, is_authenticated

app=FastAPI(title="Soil Advisory Platform",version="0.1.0")
app.add_middleware(SessionMiddleware,secret_key=SESSION_SECRET,same_site="lax",https_only=True)
app.mount("/static",StaticFiles(directory=BASE_DIR/"app"/"static"),name="static")
templates=Jinja2Templates(directory=BASE_DIR/"app"/"templates")

@app.get("/",response_class=HTMLResponse)
def home(request:Request):
    return templates.TemplateResponse("public.html",{"request":request})

@app.get("/api/public/filters")
def public_filters():
    df=load_public_predictions()
    return {"districts":sorted(df["district"].dropna().astype(str).unique().tolist()),
      "crops":sorted(df["crop"].dropna().astype(str).unique().tolist()),
      "seasons":sorted(df["season"].dropna().astype(str).unique().tolist()),
      "scenarios":sorted(df["scenario"].dropna().astype(str).unique().tolist())}

@app.get("/api/public/advisory")
def public_advisory(district:str|None=None,crop:str|None=None,season:str|None=None,scenario:str|None=None):
    df=load_public_predictions()
    for col,value in {"district":district,"crop":crop,"season":season,"scenario":scenario}.items():
        if value: df=df[df[col].astype(str).str.casefold()==value.casefold()]
    return {"count":len(df),"results":df.fillna("").to_dict(orient="records")}

@app.get("/staff/login",response_class=HTMLResponse)
def login_page(request:Request):
    if not STAFF_ENABLED:
        return templates.TemplateResponse("login.html",{"request":request,"error":"Staff access is not configured on this deployment."},status_code=503)
    if is_authenticated(request): return RedirectResponse("/staff",status_code=303)
    return templates.TemplateResponse("login.html",{"request":request,"error":None})

@app.post("/staff/login",response_class=HTMLResponse)
def login(request:Request,username:str=Form(...),password:str=Form(...)):
    if not credentials_valid(username,password):
        return templates.TemplateResponse("login.html",{"request":request,"error":"Invalid username or password."},status_code=401)
    request.session["authenticated"]=True
    request.session["username"]=username
    return RedirectResponse("/staff",status_code=303)

@app.post("/staff/logout")
def logout(request:Request):
    request.session.clear()
    return RedirectResponse("/",status_code=303)

def require_staff(request:Request):
    if not is_authenticated(request): raise HTTPException(status_code=401,detail="Authentication required")

@app.get("/staff",response_class=HTMLResponse)
def staff_home(request:Request):
    if not STAFF_ENABLED: return RedirectResponse("/staff/login",status_code=303)
    if not is_authenticated(request): return RedirectResponse("/staff/login",status_code=303)
    return templates.TemplateResponse("staff.html",{"request":request})

@app.get("/api/staff/list/{area}")
def staff_listing(request:Request,area:str,path:str=""):
    require_staff(request)
    try: entries=safe_private_listing(area,path)
    except ValueError as exc: raise HTTPException(status_code=400,detail=str(exc)) from exc
    return {"area":area,"path":path,"entries":entries}

@app.get("/health")
def health(): return JSONResponse({"status":"ok"})
