import os
from sqlalchemy import create_engine, MetaData, Table

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://courses_db_data:2wvTyzhft81R8f6@micro_db_courses:5432/micro_db_courses")

engine = create_engine(DATABASE_URL)
metadata = MetaData()

courses = Table("courses", metadata, autoload_with=engine)
