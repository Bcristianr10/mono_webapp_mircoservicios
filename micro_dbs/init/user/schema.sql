CREATE TABLE users (
    id SERIAL NOT NULL,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(120) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'student',
    created_at TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (email)
);

CREATE INDEX ix_users_email ON users (email);
