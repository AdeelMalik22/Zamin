"""Compatibility ASGI entrypoint.

Application code lives in :mod:`app.main`; run with ``uvicorn app.main:app``.
"""

from app.main import app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
