# #region debug log
"""Debug logging helper for active debug session 5fd6b2 — remove after fix."""
import json as _json, time as _time

_LOG_PATH = "/Users/jvalin/dev/st5/house-helper/.cursor/debug-5fd6b2.log"

def dbg(location: str, message: str, data: dict, hyp: str | None = None) -> None:
    try:
        with open(_LOG_PATH, "a") as f:
            f.write(_json.dumps({
                "sessionId": "5fd6b2",
                "location": location,
                "message": message,
                "data": data,
                "hypothesisId": hyp,
                "timestamp": int(_time.time() * 1000),
            }) + "\n")
    except Exception:
        pass
# #endregion
