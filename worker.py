import json
import time
import requests
import redis
from config import config

# Initialize Redis client
redis_client = redis.Redis(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT,
    db=config.REDIS_DB,
    decode_responses=True # Decode responses to strings
)

def forward_to_splunk(event_data: dict):
    """
    Forwards a single event to Splunk HEC.
    """
    splunk_hec_headers = {
        "Authorization": f"Splunk {config.SPLUNK_HEC_TOKEN}",
        "Content-Type": "application/json"
    }

    # Construct Splunk HEC payload
    # The 'event' field contains the actual data you want to index.
    # You can also specify 'sourcetype', 'host', 'index', etc., here.
    splunk_payload = {
        "event": event_data["original_payload"],
        "time": event_data["timestamp"],
        "host": "stream-webhook-forwarder",
        "source": "stream-chat-webhook",
        "sourcetype": "_json", # Or a specific sourcetype for your Stream data
        "fields": { # Custom fields that Splunk will extract
            "x_webhook_id": event_data["x_webhook_id"],
            "x_api_key": event_data["x_api_key"]
        }
    }

    try:
        response = requests.post(
            config.SPLUNK_HEC_URL,
            headers=splunk_hec_headers,
            json=splunk_payload,
            verify=False # Set to True in production with proper CA certs
        )
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        print(f"Successfully forwarded webhook ID {event_data['x_webhook_id']} to Splunk. Status: {response.status_code}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Failed to forward webhook ID {event_data['x_webhook_id']} to Splunk: {e}")
        print(f"Response: {getattr(e.response, 'text', 'N/A')}")
        return False

def run_worker():
    """
    Main loop for the Splunk forwarder worker.
    """
    print("Splunk Forwarder Worker started. Waiting for messages...")
    while True:
        try:
            # Block and pop an item from the left of the list (queue)
            # timeout=1 ensures it doesn't block indefinitely and can be interrupted
            _key, raw_data = redis_client.blpop(config.WEBHOOK_QUEUE_NAME, timeout=1)

            if raw_data:
                event_data = json.loads(raw_data)
                webhook_id = event_data.get("x_webhook_id")

                # Basic deduplication check using a Redis Set
                # Add webhook_id to a set with an expiry. If already exists, skip.
                # This handles retries from Stream within the deduplication window.
                if webhook_id:
                    if redis_client.sismember(f"processed_webhooks:{config.WEBHOOK_QUEUE_NAME}", webhook_id):
                        print(f"Skipping duplicate webhook ID {webhook_id} (already processed or in window).")
                        continue
                    else:
                        # Add to set and set expiry
                        redis_client.sadd(f"processed_webhooks:{config.WEBHOOK_QUEUE_NAME}", webhook_id)
                        redis_client.expire(f"processed_webhooks:{config.WEBHOOK_QUEUE_NAME}", config.DEDUPLICATION_WINDOW_SECONDS)

                print(f"Processing webhook ID: {webhook_id}")
                success = forward_to_splunk(event_data)

                if not success:
                    # Implement retry logic here if needed, e.g., re-queueing with delay
                    # For simplicity, we just log and move on.
                    print(f"Failed to send webhook ID {webhook_id} to Splunk. Consider re-queueing.")
                    # If you want to re-queue for retry, use rpush:
                    # redis_client.rpush(config.WEBHOOK_QUEUE_NAME, raw_data)
            else:
                # No data after timeout, just continue looping
                pass

        except redis.exceptions.ConnectionError as e:
            print(f"Redis connection error: {e}. Retrying in 5 seconds...")
            time.sleep(5)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from queue: {e}. Raw data: {raw_data}")
        except Exception as e:
            print(f"An unexpected error occurred in worker: {e}")
            time.sleep(1) # Prevent busy-looping on persistent errors

if __name__ == "__main__":
    run_worker()