from fastapi import FastAPI
from routes.routes import enrollments_router

app = FastAPI()

app.include_router(enrollments_router, tags=["Matrículas"])
