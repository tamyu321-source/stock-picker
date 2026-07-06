from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sys
import tempfile
import time
from pathlib import Path
from threading import RLock
from typing import Any


DEFAULT_API_ACCESS_KEY = "19940710"
DEFAULT_SESSION_TTL_SECONDS = 60 * 60 * 24 * 7
DEFAULT_ADMIN_TTL_SECONDS = 60 * 60 * 12
PBKDF2_ITERATIONS = 210_000


def utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def hash_secret(secret: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_urlsafe(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        secret.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${_b64url(digest)}"


def verify_secret(secret: str, stored_hash: str | None) -> bool:
    if not secret or not stored_hash:
        return False
    try:
        scheme, iterations, salt, digest = stored_hash.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        computed = hashlib.pbkdf2_hmac(
            "sha256",
            secret.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        )
        return hmac.compare_digest(_b64url(computed), digest)
    except Exception:
        return False


def key_fingerprint(access_key: str) -> str:
    return hashlib.sha256(access_key.encode("utf-8")).hexdigest()[:12]


def default_store_path() -> str:
    return os.path.join(tempfile.gettempdir(), "stock-picker-auth-store.json")


class AuthStore:
    def __init__(
        self,
        path: str | None = None,
        session_secret: str | None = None,
        access_keys: list[str] | None = None,
        admin_username: str | None = None,
        admin_password_hash: str | None = None,
        admin_password: str | None = None,
        session_ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
        admin_ttl_seconds: int = DEFAULT_ADMIN_TTL_SECONDS,
    ) -> None:
        self.path = Path(path or default_store_path())
        self.session_secret = session_secret or "stock-picker-dev-session-secret"
        self.session_ttl_seconds = session_ttl_seconds
        self.admin_ttl_seconds = admin_ttl_seconds
        self.admin_username = admin_username or ""
        self.admin_password_hash = admin_password_hash or (hash_secret(admin_password) if admin_password else "")
        self._lock = RLock()
        self._data = self._load()
        self._bootstrap_access_keys(access_keys or [])

    @classmethod
    def from_env(cls) -> "AuthStore":
        raw_keys = os.environ.get("USER_ACCESS_KEYS")
        if raw_keys is None:
            raw_keys = os.environ.get("API_ACCESS_KEYS", DEFAULT_API_ACCESS_KEY)
        access_keys = [key.strip() for key in raw_keys.split(",") if key.strip()]
        return cls(
            path=os.environ.get("AUTH_STORE_PATH"),
            session_secret=os.environ.get("AUTH_SESSION_SECRET"),
            access_keys=access_keys,
            admin_username=os.environ.get("ADMIN_USERNAME"),
            admin_password_hash=os.environ.get("ADMIN_PASSWORD_HASH"),
            admin_password=os.environ.get("ADMIN_PASSWORD"),
            session_ttl_seconds=int(os.environ.get("AUTH_SESSION_TTL_SECONDS", str(DEFAULT_SESSION_TTL_SECONDS))),
            admin_ttl_seconds=int(os.environ.get("AUTH_ADMIN_TTL_SECONDS", str(DEFAULT_ADMIN_TTL_SECONDS))),
        )

    @property
    def enabled(self) -> bool:
        return bool(self._data.get("users"))

    @property
    def admin_enabled(self) -> bool:
        return bool(self.admin_username and self.admin_password_hash)

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"users": [], "states": {}, "createdAt": utc_timestamp(), "updatedAt": utc_timestamp()}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        if not isinstance(data, dict):
            data = {}
        data.setdefault("users", [])
        data.setdefault("states", {})
        data.setdefault("createdAt", utc_timestamp())
        data.setdefault("updatedAt", utc_timestamp())
        return data

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data["updatedAt"] = utc_timestamp()
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def _bootstrap_access_keys(self, access_keys: list[str]) -> None:
        if not access_keys:
            return
        changed = False
        with self._lock:
            for index, access_key in enumerate(access_keys):
                if self._find_user_by_key(access_key):
                    continue
                user_id = f"user-{key_fingerprint(access_key)}"
                if self._find_user_by_id(user_id):
                    user_id = f"{user_id}-{secrets.token_urlsafe(4)}"
                self._data["users"].append(
                    {
                        "id": user_id,
                        "label": "Default user" if index == 0 else f"User {index + 1}",
                        "enabled": True,
                        "keyHash": hash_secret(access_key),
                        "keyFingerprint": key_fingerprint(access_key),
                        "notes": "Bootstrapped from USER_ACCESS_KEYS/API_ACCESS_KEYS",
                        "createdAt": utc_timestamp(),
                        "updatedAt": utc_timestamp(),
                        "lastLoginAt": None,
                    }
                )
                self._data["states"].setdefault(user_id, self._empty_state())
                changed = True
            if changed:
                self._save()

    def _empty_state(self) -> dict[str, Any]:
        return {
            "settings": {},
            "savedScans": [],
            "portfolio": None,
            "portfolioMemory": [],
            "recommendationHistory": [],
            "createdAt": utc_timestamp(),
            "updatedAt": utc_timestamp(),
        }

    def _find_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        for user in self._data.get("users", []):
            if user.get("id") == user_id:
                return user
        return None

    def _find_user_by_key(self, access_key: str) -> dict[str, Any] | None:
        for user in self._data.get("users", []):
            if verify_secret(access_key, user.get("keyHash")):
                return user
        return None

    def public_user(self, user: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": user.get("id"),
            "label": user.get("label") or user.get("id"),
            "enabled": bool(user.get("enabled", True)),
            "keyFingerprint": user.get("keyFingerprint"),
            "notes": user.get("notes") or "",
            "createdAt": user.get("createdAt"),
            "updatedAt": user.get("updatedAt"),
            "lastLoginAt": user.get("lastLoginAt"),
            "stateUpdatedAt": (self._data.get("states", {}).get(user.get("id")) or {}).get("updatedAt"),
        }

    def login_with_key(self, access_key: str) -> dict[str, Any] | None:
        with self._lock:
            user = self._find_user_by_key(access_key)
            if not user or not user.get("enabled", True):
                return None
            user["lastLoginAt"] = utc_timestamp()
            user["updatedAt"] = utc_timestamp()
            self._data["states"].setdefault(user["id"], self._empty_state())
            self._save()
            return self.issue_session(self.public_user(user), "user", self.session_ttl_seconds)

    def login_admin(self, username: str, password: str) -> dict[str, Any] | None:
        if not self.admin_enabled:
            return None
        if not hmac.compare_digest(username or "", self.admin_username):
            return None
        if not verify_secret(password, self.admin_password_hash):
            return None
        admin = {"id": "admin", "label": self.admin_username, "enabled": True}
        return self.issue_session(admin, "admin", self.admin_ttl_seconds)

    def issue_session(self, user: dict[str, Any], role: str, ttl_seconds: int) -> dict[str, Any]:
        now = int(time.time())
        payload = {
            "sub": user["id"],
            "role": role,
            "label": user.get("label") or user["id"],
            "iat": now,
            "exp": now + ttl_seconds,
        }
        token = self.sign_payload(payload)
        return {"token": token, "user": user, "role": role, "expiresAt": payload["exp"]}

    def sign_payload(self, payload: dict[str, Any]) -> str:
        body = _b64url(_json_dumps(payload).encode("utf-8"))
        signature = hmac.new(self.session_secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
        return f"{body}.{_b64url(signature)}"

    def verify_session(self, token: str | None) -> dict[str, Any] | None:
        if not token or "." not in token:
            return None
        try:
            body, signature = token.split(".", 1)
            expected = hmac.new(self.session_secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
            if not hmac.compare_digest(_b64url(expected), signature):
                return None
            payload = json.loads(_b64url_decode(body).decode("utf-8"))
        except Exception:
            return None
        if int(payload.get("exp") or 0) < int(time.time()):
            return None
        if payload.get("role") == "user":
            user = self._find_user_by_id(str(payload.get("sub") or ""))
            if not user or not user.get("enabled", True):
                return None
        return payload

    def user_state(self, user_id: str) -> dict[str, Any]:
        with self._lock:
            state = self._data["states"].setdefault(user_id, self._empty_state())
            return json.loads(json.dumps(state, ensure_ascii=False))

    def update_user_state(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        allowed = {"settings", "savedScans", "portfolio", "portfolioMemory", "recommendationHistory"}
        with self._lock:
            state = self._data["states"].setdefault(user_id, self._empty_state())
            for key in allowed:
                if key in payload:
                    state[key] = payload[key]
            state["updatedAt"] = utc_timestamp()
            self._save()
            return self.user_state(user_id)

    def list_users(self) -> list[dict[str, Any]]:
        with self._lock:
            return [self.public_user(user) for user in self._data.get("users", [])]

    def create_user(self, access_key: str, label: str = "", notes: str = "", enabled: bool = True) -> dict[str, Any]:
        if not access_key or not access_key.strip():
            raise ValueError("accessKey is required")
        with self._lock:
            if self._find_user_by_key(access_key):
                raise ValueError("accessKey already exists")
            user_id = f"user-{key_fingerprint(access_key)}"
            if self._find_user_by_id(user_id):
                user_id = f"{user_id}-{secrets.token_urlsafe(4)}"
            user = {
                "id": user_id,
                "label": label.strip() or f"User {key_fingerprint(access_key)}",
                "enabled": bool(enabled),
                "keyHash": hash_secret(access_key),
                "keyFingerprint": key_fingerprint(access_key),
                "notes": notes.strip(),
                "createdAt": utc_timestamp(),
                "updatedAt": utc_timestamp(),
                "lastLoginAt": None,
            }
            self._data["users"].append(user)
            self._data["states"].setdefault(user_id, self._empty_state())
            self._save()
            return self.public_user(user)

    def update_user(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            user = self._find_user_by_id(user_id)
            if not user:
                raise KeyError(user_id)
            if "label" in payload:
                user["label"] = str(payload.get("label") or "").strip() or user_id
            if "notes" in payload:
                user["notes"] = str(payload.get("notes") or "").strip()
            if "enabled" in payload:
                user["enabled"] = bool(payload.get("enabled"))
            if payload.get("accessKey"):
                access_key = str(payload["accessKey"])
                existing = self._find_user_by_key(access_key)
                if existing and existing.get("id") != user_id:
                    raise ValueError("accessKey already exists")
                user["keyHash"] = hash_secret(access_key)
                user["keyFingerprint"] = key_fingerprint(access_key)
            user["updatedAt"] = utc_timestamp()
            self._save()
            return self.public_user(user)

    def reset_user_state(self, user_id: str) -> dict[str, Any]:
        with self._lock:
            if not self._find_user_by_id(user_id):
                raise KeyError(user_id)
            self._data["states"][user_id] = self._empty_state()
            self._save()
            return self.user_state(user_id)


def main(argv: list[str]) -> int:
    if len(argv) >= 3 and argv[1] == "hash-password":
        print(hash_secret(argv[2]))
        return 0
    print("Usage: python -m backend.auth_store hash-password <password>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
