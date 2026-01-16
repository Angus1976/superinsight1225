"""
Minimal FastAPI application for debugging
"""

from fastapi import FastAPI
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SuperInsight Minimal Test")

@app.get("/")
async def root():
    logger.info("Root endpoint called")
    return {"status": "ok", "message": "minimal app working"}

@app.get("/health")
async def health():
    logger.info("Health endpoint called")
    return {"status": "healthy", "service": "minimal"}

@app.get("/test")
async def test():
    logger.info("Test endpoint called")
    return {
        "status": "success",
        "message": "If you see this, the minimal app is working correctly"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
