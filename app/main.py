from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.crud import seed_reports
from app.database import Base, SessionLocal, engine
from app.routers.web import router as web_router


settings = get_settings()


def ensure_report_schema() -> None:
    inspector = inspect(engine)
    if "research_reports" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("research_reports")}
    with engine.begin() as connection:
        if "status" not in existing_columns:
            connection.execute(
                text(
                    "ALTER TABLE research_reports "
                    "ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'published'"
                )
            )
        connection.execute(
            text(
                "UPDATE research_reports "
                "SET status = 'published' "
                "WHERE status IS NULL OR status = ''"
            )
        )


def ensure_frontend_user_schema() -> None:
    inspector = inspect(engine)
    if "frontend_users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("frontend_users")}
    with engine.begin() as connection:
        if "level" not in existing_columns:
            connection.execute(
                text(
                    "ALTER TABLE frontend_users "
                    "ADD COLUMN level VARCHAR(20) NOT NULL DEFAULT 'User'"
                )
            )
        connection.execute(
            text(
                "UPDATE frontend_users "
                "SET level = 'User' "
                "WHERE level IS NULL OR level = ''"
            )
        )


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_report_schema()
    ensure_frontend_user_schema()
    with SessionLocal() as db:
        seed_reports(db)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(web_router)


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}
