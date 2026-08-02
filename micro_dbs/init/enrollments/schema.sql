CREATE TABLE enrollments (
    id SERIAL NOT NULL,
    user_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    enrolled_at TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (user_id, course_id)
);

CREATE INDEX ix_enrollments_user_id ON enrollments (user_id);
CREATE INDEX ix_enrollments_course_id ON enrollments (course_id);

CREATE TABLE enrollment_status_history (
    id SERIAL NOT NULL,
    enrollment_id INTEGER NOT NULL REFERENCES enrollments (id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL,
    changed_at TIMESTAMP NOT NULL,
    PRIMARY KEY (id)
);

CREATE INDEX ix_enrollment_status_history_enrollment_id ON enrollment_status_history (enrollment_id);
CREATE INDEX ix_enrollment_status_history_status_changed_at ON enrollment_status_history (status, changed_at);
