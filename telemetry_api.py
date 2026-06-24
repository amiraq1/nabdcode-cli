import asyncio
import os
import json
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import time

app = FastAPI(title="CLIProxy Telemetry Bridge")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

LOG_FILE_PATH = os.getenv("NABD_LOG_PATH", ".nabd.log")

async def log_reader():
    """Generator that yields new lines appended to the log file via SSE."""
    import re
    if not os.path.exists(LOG_FILE_PATH):
        open(LOG_FILE_PATH, 'w').close()
        
    last_latency = 0
    with open(LOG_FILE_PATH, 'r') as f:
        f.seek(0, 2) # Start at the end of the file
        while True:
            line = f.readline()
            if not line:
                await asyncio.sleep(0.5)
                continue
            
            # صائد الـ Latency الذكي (Smart catch)
            latency_match = re.search(r'(\d+(?:\.\d+)?)\s*ms', line, re.IGNORECASE)
            if latency_match:
                last_latency = float(latency_match.group(1))
            
            payload = {
                "timestamp": time.time(),
                "log": line.strip(),
                "metrics": {
                    "latency_ms": last_latency,
                    "status": "active"
                }
            }
            yield f"data: {json.dumps(payload)}\n\n"

@app.get("/stream")
async def stream_telemetry(request: Request):
    """SSE endpoint for live dashboard telemetry."""
    return StreamingResponse(log_reader(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8081, log_level="warning")
