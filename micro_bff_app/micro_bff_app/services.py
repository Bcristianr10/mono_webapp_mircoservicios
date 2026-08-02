import os
import httpx

USERS_URL = os.getenv("USERS_URL", "http://micro_app_user:8001")
COURSES_URL = os.getenv("COURSES_URL", "http://micro_app_courses:8002")
ENROLLMENTS_URL = os.getenv("ENROLLMENTS_URL", "http://micro_app_enrollments:8003")
REPORTS_URL = os.getenv("REPORTS_URL", "http://micro_app_reports:8004")

TIMEOUT = 5

def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def register(full_name, email, password, role="student"):
    r = httpx.post(
        f"{USERS_URL}/api/users/register",
        json={"full_name": full_name, "email": email, "password": password, "role": role},
        timeout=TIMEOUT,
    )
    return r.status_code, r.json()

def login(email, password):
    r = httpx.post(
        f"{USERS_URL}/api/users/login",
        json={"email": email, "password": password},
        timeout=TIMEOUT,
    )
    return r.status_code, r.json()

def list_users(token):
    r = httpx.get(f"{USERS_URL}/api/users", headers=_auth(token), timeout=TIMEOUT)
    return r.status_code, r.json()

def get_user(token, user_id):
    r = httpx.get(f"{USERS_URL}/api/users/{user_id}", headers=_auth(token), timeout=TIMEOUT)
    return r.status_code, r.json()


def list_courses(token):
    r = httpx.get(f"{COURSES_URL}/api/courses", headers=_auth(token), timeout=TIMEOUT)
    return r.status_code, r.json()


def my_courses(token):
    r = httpx.get(f"{COURSES_URL}/api/courses/mine", headers=_auth(token), timeout=TIMEOUT)
    return r.status_code, r.json()

def get_course(token, course_id):
    r = httpx.get(f"{COURSES_URL}/api/courses/{course_id}", headers=_auth(token), timeout=TIMEOUT)
    return r.status_code, r.json()

def create_course(token, title, description, capacity):
    r = httpx.post(
        f"{COURSES_URL}/api/courses",
        headers=_auth(token),
        json={"title": title, "description": description, "capacity": int(capacity)},
        timeout=TIMEOUT,
    )
    return r.status_code, r.json()

def update_course(token, course_id, title, description, capacity):
    r = httpx.put(
        f"{COURSES_URL}/api/courses/{course_id}",
        headers=_auth(token),
        json={"title": title, "description": description, "capacity": int(capacity)},
        timeout=TIMEOUT,
    )
    return r.status_code, r.json()

def deactivate_course(token, course_id):
    r = httpx.delete(f"{COURSES_URL}/api/courses/{course_id}", headers=_auth(token), timeout=TIMEOUT)
    return r.status_code

 
def my_enrollments(token):
    r = httpx.get(f"{ENROLLMENTS_URL}/api/enrollments", headers=_auth(token), timeout=TIMEOUT)
    return r.status_code, r.json()

def enroll(token, course_id):
    r = httpx.post(
        f"{ENROLLMENTS_URL}/api/enrollments",
        headers=_auth(token),
        json={"course_id": course_id},
        timeout=TIMEOUT,
    )
    return r.status_code, r.json()

def cancel_enrollment(token, course_id):
    r = httpx.delete(
        f"{ENROLLMENTS_URL}/api/enrollments/{course_id}",
        headers=_auth(token),
        timeout=TIMEOUT,
    )
    return r.status_code

def cancel_all_for_course(token, course_id):
    r = httpx.delete(
        f"{ENROLLMENTS_URL}/api/enrollments/course/{course_id}/all",
        headers=_auth(token),
        timeout=TIMEOUT,
    )
    return r.status_code

def count_enrolled_for(token, course_id):
    r = httpx.get(
        f"{ENROLLMENTS_URL}/api/enrollments/course/{course_id}/count",
        headers=_auth(token),
        timeout=TIMEOUT,
    )
    if r.status_code == 200:
        return r.json().get("count", 0)
    return 0

def enrollments_for_course(token, course_id):
    r = httpx.get(
        f"{ENROLLMENTS_URL}/api/enrollments/course/{course_id}",
        headers=_auth(token),
        timeout=TIMEOUT,
    )
    if r.status_code == 200:
        return r.json()
    return []


def get_reports_dashboard(token):
    r = httpx.get(f"{REPORTS_URL}/api/reports/dashboard", headers=_auth(token), timeout=20)
    return r.status_code, r.json()


def get_course_enrollments(token, course_id, q="", page=1, page_size=20):
    params = {"page": page, "page_size": page_size}
    if q:
        params["q"] = q
    r = httpx.get(
        f"{REPORTS_URL}/api/reports/courses/{course_id}/enrollments",
        headers=_auth(token),
        params=params,
        timeout=10,
    )
    return r.status_code, r.json()
