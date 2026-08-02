from fastapi import FastAPI
from routes.routes import courses_router

app = FastAPI()

app.include_router(courses_router, tags=["Cursos"])
