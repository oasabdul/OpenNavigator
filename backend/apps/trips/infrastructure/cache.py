from __future__ import annotations

from django.core.cache import cache


class DjangoFrameCache:
    def get(self, key: str) -> object | None:
        return cache.get(key)

    def set(self, key: str, value: object, timeout: int) -> None:
        cache.set(key, value, timeout=timeout)
