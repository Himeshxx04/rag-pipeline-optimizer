from fastapi import Request


def ok(data, request: Request):
    rid = getattr(request.state, "request_id", "unknown")
    return {
        "ok": True,
        "data": data,
        "request_id": rid,
    }