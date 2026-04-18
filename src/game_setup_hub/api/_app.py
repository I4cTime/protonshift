"""FastAPI app construction, middleware, and CLI entry point."""

from __future__ import annotations

import argparse
import os
import secrets
import socket

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import game_setup_hub._vendor_compat  # noqa: F401  # must be first

from .. import __version__
from . import _state
from .routes import all_routers

app = FastAPI(title="ProtonShift API", version=__version__)


@app.middleware("http")
async def _auth_middleware(request, call_next):
    if _state.API_TOKEN and request.url.path not in _state.AUTH_EXEMPT_PATHS:
        expected = f"Bearer {_state.API_TOKEN}"
        provided = request.headers.get("authorization", "")
        if not secrets.compare_digest(provided, expected):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing or invalid token"},
                headers={"WWW-Authenticate": "Bearer"},
            )
    return await call_next(request)


# Tight CORS: the browser side is the Electron renderer (file://) plus the
# Next dev server. Nothing else has any business calling us.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"^file://.*$",
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=False,
)


for router in all_routers:
    app.include_router(router)


# ---------------------------------------------------------------------------
# CLI entry point — Electron spawns this process
# ---------------------------------------------------------------------------


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def cli() -> None:
    parser = argparse.ArgumentParser(description="ProtonShift API server")
    parser.add_argument("--port", type=int, default=0, help="Port to listen on (0 = auto)")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Interface to bind. Defaults to loopback; do not change unless you understand the risk.",
    )
    parser.add_argument(
        "--print-token",
        action="store_true",
        help="Print the auth token to stdout on startup (handy for ad-hoc curl).",
    )
    args = parser.parse_args()

    port = args.port if args.port > 0 else _find_free_port()

    # If the parent process didn't provision a token, mint one. This keeps the
    # API authenticated even when launched standalone.
    if not _state.API_TOKEN:
        _state.API_TOKEN = secrets.token_urlsafe(32)
        os.environ["PROTONSHIFT_API_TOKEN"] = _state.API_TOKEN

    print(f"PORT:{port}", flush=True)
    if args.print_token:
        print(f"TOKEN:{_state.API_TOKEN}", flush=True)

    from .. import logging_setup
    logging_setup.configure()

    import uvicorn

    uvicorn.run(app, host=args.host, port=port, log_level="warning")
