import json
import os
import re

import requests
from requests import Response

SUPERSET_URL = os.getenv("SUPERSET_URL", "http://localhost:8088")
SUPERSET_USER = os.getenv("SUPERSET_USER", "admin")
SUPERSET_PASSWORD = os.getenv("SUPERSET_PASSWORD", "admin")


class SupersetClient:
    def __init__(
        self,
        url: str = SUPERSET_URL,
        username: str = SUPERSET_USER,
        password: str = SUPERSET_PASSWORD,
    ) -> None:
        self.url = url.rstrip("/")
        self.session = requests.Session()
        # Session (cookie) login rather than JWT: when the Public role holds a
        # permission, FAB serves that endpoint anonymously and ignores the bearer token.
        login_page = self.session.get(f"{self.url}/login/")
        login_page.raise_for_status()
        match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', login_page.text)
        res = self.session.post(
            f"{self.url}/login/",
            data={
                "username": username,
                "password": password,
                "csrf_token": match.group(1) if match else "",
            },
        )
        res.raise_for_status()
        me = self.session.get(f"{self.url}/api/v1/me/")
        if me.status_code != 200:
            raise RuntimeError(f"Login failed for {username}: {me.status_code}")
        res = self.session.get(f"{self.url}/api/v1/security/csrf_token/")
        res.raise_for_status()
        self.session.headers["X-CSRFToken"] = res.json()["result"]
        self.session.headers["Referer"] = self.url

    def request(self, method: str, path: str, **kwargs) -> Response:
        res = self.session.request(method, f"{self.url}{path}", **kwargs)
        if res.status_code >= 400:
            raise RuntimeError(f"{method} {path} -> {res.status_code}: {res.text[:2000]}")
        return res

    def get(self, path: str, **kwargs) -> dict:
        return self.request("GET", path, **kwargs).json()

    def post(self, path: str, payload: dict) -> dict:
        return self.request("POST", path, json=payload).json()

    def put(self, path: str, payload: dict) -> dict:
        return self.request("PUT", path, json=payload).json()

    def find(self, resource: str, column: str, value: str) -> dict | None:
        q = {"filters": [{"col": column, "opr": "eq", "value": value}], "page_size": 100}
        res = self.get(f"/api/v1/{resource}/", params={"q": json.dumps(q)})
        return res["result"][0] if res["result"] else None
