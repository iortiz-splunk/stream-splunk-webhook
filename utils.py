import hmac
import hashlib
from typing import Union

def verify_signature(body: Union[bytes, str], signature: str, api_secret: str) -> bool:
    """
    Verifies the X-Signature header from Stream Chat.

    Args:
        body: The raw request body (as bytes or string).
        signature: The value of the X-Signature header.
        api_secret: Your Stream API secret.

    Returns:
        True if the signature is valid, False otherwise.
    """
    if isinstance(body, str):
        body = body.encode('utf-8') # Ensure body is bytes

    # Convert API secret to bytes
    secret_bytes = api_secret.encode('utf-8')

    # Calculate HMAC-SHA256 signature
    calculated_signature = hmac.new(secret_bytes, body, hashlib.sha256).hexdigest()

    # Compare signatures using hmac.compare_digest for constant-time comparison
    return hmac.compare_digest(calculated_signature, signature)