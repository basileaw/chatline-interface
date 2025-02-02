# test_backend.py
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import asyncio
import json
import uvicorn

app = FastAPI()

async def fake_stream():
    messages = ["Hello", " from", " the", " backend", "!"]
    for msg in messages:
        yield f'data: {json.dumps({"choices": [{"delta": {"content": msg}}]})}\n\n'
        await asyncio.sleep(0.5)
    yield 'data: [DONE]\n\n'

@app.post("/chat/stream")
async def stream_chat():
    return StreamingResponse(fake_stream(), media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run("test_backend:app", host="127.0.0.1", port=5000, reload=True)