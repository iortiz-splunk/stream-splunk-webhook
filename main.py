import json
import time
import redis.asyncio as aioredis
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import PlainTextResponse
from config import config
from utils import verify_signature

app = FastAPI(
    title="Stream Webhook to Splunk Forwarder",
    description="Receives Stream webhooks and queues them for Splunk forwarding.",
    version="1.0.0"
)

redis_client: aioredis.Redis = None

@app.on_event("startup")
async def startup_event():
    """Connect to Redis on application startup."""
    global redis_client
    try:
        redis_client = aioredis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=config.REDIS_DB,
            decode_responses=True # Decode responses to strings
        )
        await redis_client.ping()
        print(f"Connected to Redis at {config.REDIS_HOST}:{config.REDIS_PORT}/{config.REDIS_DB}")
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")
        # Depending on criticality, you might want to exit or raise an error here
        raise RuntimeError(f"Could not connect to Redis: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Close Redis connection on application shutdown."""
    if redis_client:
        await redis_client.close()
        print("Redis connection closed.")

@app.post("/webhook", status_code=status.HTTP_200_OK)
async def receive_webhook(request: Request):
    """
    Receives Stream Chat webhook events, verifies signature, and queues them for Splunk.
    """
    raw_body = await request.body()
    x_signature = request.headers.get("X-Signature")
    x_webhook_id = request.headers.get("X-Webhook-Id")
    x_api_key = request.headers.get("X-Api-Key")

    if not x_signature:
        print("Missing X-Signature header.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Signature header"
        )

    # Verify the signature
    if not verify_signature(raw_body, x_signature, config.STREAM_API_SECRET):
        print(f"Invalid X-Signature for webhook ID: {x_webhook_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid X-Signature"
        )

    try:
        # Attempt to parse the JSON body
        payload = json.loads(raw_body.decode('utf-8'))
    except json.JSONDecodeError:
        print(f"Invalid JSON payload for webhook ID: {x_webhook_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )

    # Prepare data for the queue, including metadata
    webhook_data = {
        "timestamp": int(time.time()),
        "x_webhook_id": x_webhook_id,
        "x_api_key": x_api_key,
        "original_payload": payload
    }

    try:
        # Push to Redis queue
        await redis_client.rpush(config.WEBHOOK_QUEUE_NAME, json.dumps(webhook_data))
        print(f"Webhook ID {x_webhook_id} queued successfully.")
        return PlainTextResponse("OK", status_code=status.HTTP_200_OK)
    except Exception as e:
        print(f"Failed to push webhook ID {x_webhook_id} to Redis queue: {e}")
        # Respond with 500 but still try to return 200 to Stream if possible,
        # as Stream might retry anyway. For critical failures, a 500 is appropriate.
        # Here, we prioritize quick response to Stream.
        return PlainTextResponse("Internal Server Error", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    try:
        await redis_client.ping()
        return {"status": "healthy", "redis_connected": True}
    except Exception:
        return {"status": "unhealthy", "redis_connected": False}

# To run this application:
# uvicorn main:app --host 0.0.0.0 --port 8000