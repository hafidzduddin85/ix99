from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/stock/{ticker}", response_class=HTMLResponse)
def stock_detail(request: Request, ticker: str):
    return templates.TemplateResponse("detail.html", {"request": request, "ticker": ticker.upper()})
