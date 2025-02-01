# test_server.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from chatline.generator import generate_stream
from typing import Dict, List

app = FastAPI()

# Add CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/chat")
async def chat(request: Dict[str, List[Dict[str, str]]]):
    """Endpoint that mimics the local generator's behavior."""
    return generate_stream(request["messages"])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

