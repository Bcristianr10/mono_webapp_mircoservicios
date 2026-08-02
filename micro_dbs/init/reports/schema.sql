-- Copia local de solo lectura para el microservicio de reportes.
-- Mismas tablas que consulta app/modules/reports/services.py en el monolito
-- (users, courses, enrollments, enrollment_status_history). El mecanismo de
-- sincronizacion desde los microservicios reales queda pendiente de definir.

-- Sin password_hash: la API de usuarios nunca lo expone (GET /api/users),
-- y esta copia es solo para lectura/reportes, no para autenticar.
CREATE TABLE users (
    id SERIAL NOT NULL,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(120) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'student',
    created_at TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (email)
);

CREATE INDEX ix_users_email ON users (email);

CREATE TABLE courses (
    id SERIAL NOT NULL,
    title VARCHAR(150) NOT NULL,
    description TEXT,
    instructor_id INTEGER NOT NULL REFERENCES users (id),
    capacity INTEGER NOT NULL DEFAULT 30,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP,
    PRIMARY KEY (id)
);

CREATE TABLE enrollments (
    id SERIAL NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users (id),
    course_id INTEGER NOT NULL REFERENCES courses (id),
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    enrolled_at TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (user_id, course_id)
);

CREATE INDEX ix_enrollments_user_id ON enrollments (user_id);
CREATE INDEX ix_enrollments_course_id ON enrollments (course_id);

-- UNIQUE en (enrollment_id, status, changed_at): permite que el worker use
-- ON CONFLICT DO NOTHING y sea seguro reprocesar un evento duplicado.
CREATE TABLE enrollment_status_history (
    id SERIAL NOT NULL,
    enrollment_id INTEGER NOT NULL REFERENCES enrollments (id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL,
    changed_at TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (enrollment_id, status, changed_at)
);

CREATE INDEX ix_enrollment_status_history_enrollment_id ON enrollment_status_history (enrollment_id);
CREATE INDEX ix_enrollment_status_history_status_changed_at ON enrollment_status_history (status, changed_at);
