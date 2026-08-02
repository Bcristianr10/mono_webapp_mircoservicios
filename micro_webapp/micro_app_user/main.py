from fastapi import FastAPI
from routes.routes import users_router

app = FastAPI()

app.include_router(users_router, tags=["Usuarios"])
