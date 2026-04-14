"""
教学数据文件存储：课程、班级、作业、提交等，存于本地 JSON 文件，无需 PostgreSQL。
数据目录：backend/data/teach/teach_data.json
"""
import json
import os
import threading
import random
import string
from pathlib import Path
from datetime import datetime

def _short_id(prefix=""):
    s = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"{prefix}{s}" if prefix else s

def _join_code():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

# 数据目录
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "teach"
DATA_FILE = DATA_DIR / "teach_data.json"
_lock = threading.Lock()

def _load():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        return {
            "courses": [],
            "lessons": [],
            "classes": [],
            "enrollments": [],
            "assignments": [],
            "submissions": [],
        }
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save(data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _run(fn):
    with _lock:
        data = _load()
        result = fn(data)
        if result is not None:
            _save(data)
        return result

# ---------- 课程 ----------
def list_courses(user_id):
    """当前用户创建的课程 + 已加入的班级（含课程信息，便于前端展示与进入）"""
    def fn(data):
        uid = str(user_id)
        taught = [c for c in data["courses"] if c.get("ownerId") == uid]
        enrollments = [e for e in data["enrollments"] if e.get("userId") == uid]
        class_ids = {e["classId"] for e in enrollments}
        classes = [c for c in data["classes"] if c.get("id") in class_ids]
        courses_by_id = {c["id"]: c for c in data["courses"]}
        enrolled = []
        for cl in classes:
            course = courses_by_id.get(cl.get("courseId"))
            if course:
                enrolled.append({"course": course, "class": cl})
        return {"taught": taught, "enrolled": enrolled}
    return _run(fn)

def create_course(owner_id, title, grade_band=None, description=None):
    def fn(data):
        c = {
            "id": _short_id("c"),
            "title": title,
            "gradeBand": grade_band,
            "description": description,
            "ownerId": str(owner_id),
            "createdAt": datetime.now().isoformat(),
        }
        data["courses"].append(c)
        return c
    return _run(fn)

def get_course(course_id):
    def fn(data):
        for c in data["courses"]:
            if c.get("id") == course_id:
                lessons = [l for l in data["lessons"] if l.get("courseId") == course_id]
                c = dict(c)
                c["lessons"] = sorted(lessons, key=lambda x: x.get("order", 0))
                return c
        return None
    return _run(fn)

def create_lesson(course_id, title, content=None, order=0):
    def fn(data):
        for c in data["courses"]:
            if c.get("id") == course_id:
                lesson = {
                    "id": _short_id("l"),
                    "courseId": course_id,
                    "title": title,
                    "content": content if content is not None else {},
                    "order": order,
                    "createdAt": datetime.now().isoformat(),
                }
                data["lessons"].append(lesson)
                return lesson
        return None
    return _run(fn)

# ---------- 班级 ----------
def list_classes(course_id=None):
    def fn(data):
        if course_id:
            return [c for c in data["classes"] if c.get("courseId") == course_id]
        return data["classes"]
    return _run(fn)

def create_class(course_id, name):
    def fn(data):
        for co in data["courses"]:
            if co.get("id") == course_id:
                join_code = _join_code()
                while any(c.get("joinCode") == join_code for c in data["classes"]):
                    join_code = _join_code()
                cl = {
                    "id": _short_id("k"),
                    "courseId": course_id,
                    "name": name,
                    "joinCode": join_code,
                    "createdAt": datetime.now().isoformat(),
                }
                data["classes"].append(cl)
                return cl
        return None
    return _run(fn)

def join_class(user_id, join_code):
    def fn(data):
        join_code = (join_code or "").strip().upper()
        for cl in data["classes"]:
            if (cl.get("joinCode") or "").upper() == join_code:
                e = {
                    "id": _short_id("e"),
                    "userId": str(user_id),
                    "classId": cl["id"],
                    "createdAt": datetime.now().isoformat(),
                }
                if any(x.get("userId") == e["userId"] and x.get("classId") == e["classId"] for x in data["enrollments"]):
                    return {"already": True, "class": cl}
                data["enrollments"].append(e)
                return {"class": cl}
        return None
    return _run(fn)

def get_class(class_id):
    def fn(data):
        for cl in data["classes"]:
            if cl.get("id") == class_id:
                enrollments = [e for e in data["enrollments"] if e.get("classId") == class_id]
                assignments = [a for a in data["assignments"] if a.get("classId") == class_id]
                cl = dict(cl)
                cl["enrollments"] = enrollments
                cl["assignments"] = assignments
                return cl
        return None
    return _run(fn)

# ---------- 作业 ----------
def list_assignments(class_id=None):
    def fn(data):
        if class_id:
            return [a for a in data["assignments"] if a.get("classId") == class_id]
        return data["assignments"]
    return _run(fn)

def create_assignment(class_id, title, spec=None, due_at=None):
    def fn(data):
        a = {
            "id": _short_id("a"),
            "classId": class_id,
            "title": title,
            "spec": spec if spec is not None else {},
            "dueAt": due_at,
            "createdAt": datetime.now().isoformat(),
        }
        data["assignments"].append(a)
        return a
    return _run(fn)

# ---------- 提交 ----------
def list_submissions(assignment_id=None, student_id=None):
    def fn(data):
        out = data["submissions"]
        if assignment_id:
            out = [s for s in out if s.get("assignmentId") == assignment_id]
        if student_id:
            out = [s for s in out if s.get("userId") == str(student_id)]
        return out
    return _run(fn)

def create_submission(assignment_id, user_id, payload):
    def fn(data):
        s = {
            "id": _short_id("s"),
            "assignmentId": assignment_id,
            "userId": str(user_id),
            "payload": payload if payload is not None else {},
            "score": None,
            "feedback": None,
            "rubricScores": None,
            "createdAt": datetime.now().isoformat(),
        }
        data["submissions"].append(s)
        return s
    return _run(fn)

def grade_submission(submission_id, score, feedback=None, rubric_scores=None):
    def fn(data):
        for s in data["submissions"]:
            if s.get("id") == submission_id:
                s["score"] = score
                s["feedback"] = feedback
                s["rubricScores"] = rubric_scores
                s["gradedAt"] = datetime.now().isoformat()
                return s
        return None
    return _run(fn)
