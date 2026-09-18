from fastapi import FastAPI
from app.routers import stocks, dashboard, update

app = FastAPI(
    title="Stock AI Analyst",
    version="0.1.0"
)

app.include_router(stocks.router)
app.include_router(dashboard.router)
app.include_router(update.router)


@app.get("/")
def root():
    return {"status": "ok", "message": "Stock AI Analyst API is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}
