from fastapi import FastAPI

app = FastAPI(
    title="Stock AI Analyst",
    version="0.1.0"
)


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Stock AI Analyst API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }