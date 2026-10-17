from __future__ import annotations

import time
from collections.abc import Callable

import requests


def request_json(
    http_get: Callable[..., requests.Response],
    url: str,
    *,
    params: dict,
    headers: dict,
    timeout: float,
    attempts: int = 2,
):
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = http_get(
                url,
                params=params,
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(0.7 * (attempt + 1))
    assert last_error is not None
    raise last_error
