import os
from sqlalchemy import create_engine, MetaData, Table

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://users_db_data:8a2auWuBOT131yz@micro_db_user:5432/micro_db_user")

engine = create_engine(DATABASE_URL)
metadata = MetaData()

users = Table("users", metadata, autoload_with=engine)
