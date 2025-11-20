"""HTTP module."""

import logging

from requests import Session
from yarl import URL

logger = logging.getLogger(__name__)

class HTTPSession(Session):
    """An HTTP session with origin."""

    def __init__(self, origin: URL | str, timeout=60, **kwargs):
        super().__init__(**kwargs)
        self.origin = URL(origin)
        self.timeout = timeout

    def __repr__(self):
        return f"{self.__class__.__name__}(origin={self.origin!r}, timeout={self.timeout})"

    def request(self, method: str, path: str, **kwargs):
        """Send an HTTP request.

        :param method: Method for the request.
        :param path: Path joined to the URL.
        :param \\**kwargs: Optional keyword arguments passed to the session.
        """
        url = self.origin.with_path(path)
        kwargs.setdefault("timeout", self.timeout)
        response = super().request(method, url, **kwargs)
        try:
            response.raise_for_status()
        except Exception:
            logger.exception("HTTP request failed: %(method)s %(url)s", {
                "method": method,
                "url": url,
            })
            raise
        else:
            return response
