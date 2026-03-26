def get_payload(result):
    return result.payload if hasattr(result, "payload") else result.get("payload", {})