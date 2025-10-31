from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import base64
import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request


class ApiClient:
    """Minimal HTTP client for config endpoints with HMAC auth."""

    def __init__(self, hmac_key: Optional[str], base_url: Optional[str] = None, timeout: float = 10.0) -> None:
        self.hmac_key = hmac_key or ""
        self.base_url = (base_url or os.environ.get("REX_API_BASE_URL") or "http://localhost:8000").rstrip("/")
        self.timeout = timeout

    # --- Auth helpers
    def _sign(self, method: str, path: str, body: str, ts: str) -> str:
        message = f"{ts}{method}{path}{body}".encode("utf-8")
        key_bytes = self.hmac_key.encode("utf-8")
        digest = hmac.new(key_bytes, message, hashlib.sha512).digest()
        return base64.b64encode(digest).decode("ascii").strip()

    def _headers(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        ts = str(int(time.time()))
        sig = self._sign(method.upper(), path, body, ts)
        return {
            "x-signature": sig,
            "x-timestamp": ts,
            "Content-Type": "application/json",
        }

    # --- Endpoints
    def get_config_field(self, field: str) -> Optional[Dict[str, Any]]:
        """GET /config/{field}. Returns dict; on HTTP 400 returns {"field": field, "value": ""}; None on other errors."""
        path = f"/config/{urllib.parse.quote(field)}"
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url, method="GET", headers=self._headers("GET", path, ""))
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = resp.read().decode("utf-8")
                return json.loads(data) if data else {}
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            if e.code == 400:
                return {"field": field, "value": ""}
            # Let caller decide how to display the error; return None to signal failure
            return None
        except Exception:
            return None

    def patch_config_bulk(self, updates: List[Tuple[str, Any]]) -> Tuple[bool, int, str]:
        """PATCH /config with body: [{"field": str, "value": Any}, ...]. Returns (ok, status, text)."""
        path = "/config"
        url = f"{self.base_url}{path}"
        payload_list = [{"field": f, "value": v} for (f, v) in updates]
        try:
            body_str = json.dumps(payload_list, separators=(",", ":"), ensure_ascii=False)
        except Exception:
            payload_list = [{"field": f, "value": ("" if v is None else str(v))} for (f, v) in updates]
            body_str = json.dumps(payload_list, separators=(",", ":"), ensure_ascii=False)
        headers = self._headers("PATCH", path, body_str)
        data = body_str.encode("utf-8")
        req = urllib.request.Request(url, data=data, method="PATCH", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp_text = resp.read().decode("utf-8", errors="replace")
                status = getattr(resp, "status", resp.getcode())
                return True, int(status), resp_text
        except urllib.error.HTTPError as e:
            resp_text = e.read().decode("utf-8", errors="replace")
            return False, e.code, resp_text
        except Exception as ex:
            return False, 0, str(ex)
