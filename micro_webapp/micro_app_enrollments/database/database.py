import os
from sqlalchemy import create_engine, MetaData, Table

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://enrollments_db_data:h9UY9yv2K7IZ2ED@micro_db_enrollments:5432/micro_db_enrollments")

engine = create_engine(DATABASE_URL)
metadata = MetaData()

enrollments = Table("enrollments", metadata, autoload_with=engine)
enrollment_status_history = Table("enrollment_status_history", metadata, autoload_with=engine)
