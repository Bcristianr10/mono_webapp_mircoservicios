from fastapi import FastAPI
from routes.routes import reports_router

app = FastAPI()

app.include_router(reports_router, tags=["Reportes"])
