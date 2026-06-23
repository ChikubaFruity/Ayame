import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router


def create_app() -> FastAPI:
    app = FastAPI(title="ayame", description="ローカルNotebookLM API")

    # 既定はNext.js dev。Tailscale等の追加オリジンは ALLOW_ORIGINS（カンマ区切り）で指定。
    origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
    extra = os.environ.get("ALLOW_ORIGINS", "")
    origins += [o.strip() for o in extra.split(",") if o.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=r"http://.*\.ts\.net(:\d+)?",
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run(
        "ayame.api.app:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
    )
