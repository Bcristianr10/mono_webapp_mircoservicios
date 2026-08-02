CREATE TABLE courses (
    id SERIAL NOT NULL,
    title VARCHAR(150) NOT NULL,
    description TEXT,
    instructor_id INTEGER NOT NULL,
    capacity INTEGER NOT NULL DEFAULT 30,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP,
    PRIMARY KEY (id)
);
