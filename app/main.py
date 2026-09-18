from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routers import stocks, dashboard, update, detail, broker, pipeline, web

app = FastAPI(title="Stock AI Analyst", version="0.1.0")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# API routes
app.include_router(stocks.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(update.router, prefix="/api")
app.include_router(detail.router, prefix="/api")
app.include_router(broker.router, prefix="/api")
app.include_router(pipeline.router, prefix="/api")

# Web routes
app.include_router(web.router)


@app.get("/health")
def health():
    return {"status": "healthy"}
