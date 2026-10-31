import hashlib
import hmac


def verify_github_signature(
    raw_payload_bytes: bytes,
    secret_token: str,
    signature_header: str | None,
) -> bool:
    """
    Cryptographically verify GitHub webhook payload using HMAC-SHA256.
    Uses timing-safe comparison to prevent side-channel timing attacks.
    """
    if not secret_token or not signature_header or not signature_header.startswith("sha256="):
        return False

    expected_hash = signature_header.split("sha256=")[1].strip()
    computed_hmac = hmac.new(
        key=secret_token.encode("utf-8"),
        msg=raw_payload_bytes,
        digestmod=hashlib.sha256,
    )

    return hmac.compare_digest(computed_hmac.hexdigest(), expected_hash)
