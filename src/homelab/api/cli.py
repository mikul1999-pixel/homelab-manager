import uvicorn

def main():
    uvicorn.run(
        "homelab.api.main:app",
        host="0.0.0.0",
        port=3000,
        reload=False,
    )
