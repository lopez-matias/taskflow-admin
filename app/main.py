from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import ROOT_DIR, get_settings
from app.errors import BusinessError
from app.routers import catalogs, dashboard, requests

settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="REST API for creating, assigning, tracking, and auditing internal requests.",
    debug=settings.debug,
)
app.mount("/static", StaticFiles(directory=ROOT_DIR / "app" / "static"), name="static")
templates = Jinja2Templates(directory=ROOT_DIR / "app" / "templates")

app.include_router(catalogs.router, prefix="/api")
app.include_router(requests.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")


@app.exception_handler(BusinessError)
async def business_error_handler(_request: Request, error: BusinessError):
    return JSONResponse(
        status_code=error.status_code,
        content={"detail": error.message, "code": error.code},
    )


@app.get("/api/health", tags=["System"], summary="Service health check")
def health():
    return {"status": "ok", "environment": settings.environment}


@app.get("/", include_in_schema=False)
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"app_name": settings.app_name})
