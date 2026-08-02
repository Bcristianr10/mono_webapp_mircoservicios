import os
from sqlalchemy import create_engine, MetaData, Table

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://reports_db_data:Qw8LmZ4vRtY29Fp@micro_db_reports:5432/micro_db_reports",
)

engine = create_engine(DATABASE_URL)
metadata = MetaData()

# Copia local de solo lectura de users/courses/enrollments/enrollment_status_history.
# La sincronizacion desde los microservicios reales queda pendiente de definir.
users = Table("users", metadata, autoload_with=engine)
courses = Table("courses", metadata, autoload_with=engine)
enrollments = Table("enrollments", metadata, autoload_with=engine)
enrollment_status_history = Table("enrollment_status_history", metadata, autoload_with=engine)
