"""
皮影动画生成平台 - 后端主入口
"""

from flask import Flask, render_template, request, jsonify, send_file, session
import os
import json
import uuid
import base64
import time

# 加载 .env（项目根目录，与 backend 同级）
from pathlib import Path
_env_path = Path(__file__).resolve().parent.parent / '.env'
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path)

import io
import sys
from urllib.parse import quote, unquote
from werkzeug.utils import secure_filename

sys.path.insert(0, str(Path(__file__).parent))

from src.integration.script_generator import ScriptGenerator
from src.motion_capture.full_body_detector import FullBodyDetector
from src.motion_capture.bvh_24_joints import BVH24JointsConverter
from src.motion_capture.realtime_pose_mapper import RealtimePoseMapper
from src.data.action_library import ActionLibrary
from src.models.user_model import UserModel, generate_jwt_token, verify_jwt_token

try:
    import cv2
except Exception:
    cv2 = None

try:
    import numpy as np
except Exception:
    np = None

user_model = UserModel()

# 创建测试账号（教师 / 学生），若已存在则跳过
def _ensure_test_accounts():
    for username, email, password, account_type in [
        ('teacher_test', 'teacher@test.local', 'teacher123', 'teacher'),
        ('student_test', 'student@test.local', 'student123', 'student'),
    ]:
        try:
            user_model.create_user(username, email, password, account_type=account_type)
        except Exception:
            pass  # 已存在或其它错误则忽略

_ensure_test_accounts()

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['AVATARS_FOLDER'] = 'uploads/avatars'
app.config['OUTPUT_FOLDER'] = 'outputs/web'
app.config['GENERATED_IMAGES_FOLDER'] = 'outputs/generated_images'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

# 创建必要的目录
Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)
Path(app.config['AVATARS_FOLDER']).mkdir(parents=True, exist_ok=True)
Path(app.config['OUTPUT_FOLDER']).mkdir(parents=True, exist_ok=True)
Path(app.config['GENERATED_IMAGES_FOLDER']).mkdir(parents=True, exist_ok=True)

# 初始化组件（通义千问 API Key 从 .env 的 DASHSCOPE_API_KEY 读取）
action_library = ActionLibrary()
script_generator = ScriptGenerator(tongyi_api_key=os.environ.get('DASHSCOPE_API_KEY'))

try:
    realtime_pose_mapper = RealtimePoseMapper()
    realtime_pose_mapper_error = ''
except Exception as _e:
    realtime_pose_mapper = None
    realtime_pose_mapper_error = str(_e)
    print(f"[WARN] realtime pose mapper unavailable: {_e}")

# Unity -> Web 实时骨骼桥（最新一帧缓存）
unity_pose_latest = {
    'updatedAt': 0.0,
    'source': 'unity',
    'puppet_pose': None,
    'joints': None,
}

# CORS（若未安装 flask-cors 可注释）
try:
    from flask_cors import CORS
    CORS(app, origins=['http://localhost:3000', 'http://localhost:5173', 'http://127.0.0.1:3000', 'http://127.0.0.1:5173'])
except ImportError:
    pass


# ========== 认证 API（与前端 authService、教学后端 JWT 共用） ==========

@app.route('/api/auth/register', methods=['POST'])
def auth_register():
    """注册"""
    try:
        data = request.get_json() or {}
        username = (data.get('username') or '').strip()
        email = (data.get('email') or '').strip()
        password = (data.get('password') or '').strip()
        account_type = (data.get('account_type') or 'student').strip().lower()
        if not username or not email or not password:
            return jsonify({'error': '用户名、邮箱、密码不能为空'}), 400
        user_id, err = user_model.create_user(username, email, password, account_type=account_type)
        if err:
            return jsonify({'error': err}), 400
        user_data, _ = user_model.authenticate_user(username, password)
        token = generate_jwt_token(user_data)
        return jsonify({'token': token, 'user': {**user_data, 'id': user_data['id']}})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    """登录"""
    try:
        data = request.get_json() or {}
        username = (data.get('username') or '').strip()
        password = (data.get('password') or '').strip()
        if not username or not password:
            return jsonify({'error': '用户名、密码不能为空'}), 400
        user_data, err = user_model.authenticate_user(username, password)
        if err:
            return jsonify({'error': err}), 401
        token = generate_jwt_token(user_data)
        return jsonify({'token': token, 'user': {**user_data, 'id': user_data['id']}})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/verify', methods=['POST'])
def auth_verify():
    """验证 token，返回用户信息"""
    try:
        data = request.get_json() or {}
        token = (data.get('token') or request.headers.get('Authorization') or '').replace('Bearer ', '').strip()
        if not token:
            return jsonify({'error': '未提供 token'}), 401
        payload, err = verify_jwt_token(token)
        if err:
            return jsonify({'error': err}), 401
        user = user_model.get_user_by_id(payload.get('user_id'))
        if not user:
            return jsonify({'error': '用户不存在'}), 401
        return jsonify({'user': {**user, 'account_type': user.get('account_type', 'student')}})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/me', methods=['GET'])
def auth_me():
    """获取当前用户（需 Authorization: Bearer <token>）"""
    try:
        auth = request.headers.get('Authorization') or ''
        token = auth.replace('Bearer ', '').strip()
        if not token:
            return jsonify({'error': '未登录'}), 401
        payload, err = verify_jwt_token(token)
        if err:
            return jsonify({'error': err}), 401
        user = user_model.get_user_by_id(payload.get('user_id'))
        if not user:
            return jsonify({'error': '用户不存在'}), 401
        stats = user_model.get_user_stats(payload.get('user_id'))
        return jsonify({'user': {**user, 'account_type': user.get('account_type', 'student'), 'stats': stats}})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/update', methods=['POST'])
def auth_update():
    """更新当前用户信息"""
    try:
        auth = request.headers.get('Authorization') or ''
        token = auth.replace('Bearer ', '').strip()
        if not token:
            return jsonify({'error': '未登录'}), 401
        payload, err = verify_jwt_token(token)
        if err:
            return jsonify({'error': err}), 401
        data = request.get_json() or {}
        ok, err = user_model.update_user_info(
            payload['user_id'],
            username=data.get('username'),
            email=data.get('email'),
        )
        if not ok:
            return jsonify({'error': err or '更新失败'}), 400
        user = user_model.get_user_by_id(payload['user_id'])
        return jsonify({'user': {**user, 'account_type': user.get('account_type', 'student')}})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/upload_avatar', methods=['POST'])
def auth_upload_avatar():
    """上传头像：保存文件并更新用户 avatar_url"""
    try:
        auth = request.headers.get('Authorization') or ''
        token = auth.replace('Bearer ', '').strip()
        if not token:
            return jsonify({'error': '未登录'}), 401
        payload, err = verify_jwt_token(token)
        if err:
            return jsonify({'error': err}), 401
        user_id = payload['user_id']
        user = user_model.get_user_by_id(user_id)
        if not user:
            return jsonify({'error': '用户不存在'}), 401

        file = request.files.get('avatar')
        if not file or file.filename == '':
            return jsonify({'error': '请选择头像文件'}), 400
        allowed = ('image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp')
        if file.content_type and file.content_type not in allowed:
            return jsonify({'error': '仅支持 PNG/JPG/GIF/WEBP'}), 400
        if file.content_length and file.content_length > 5 * 1024 * 1024:
            return jsonify({'error': '头像不能超过 5MB'}), 400

        ext = (Path(file.filename).suffix or '.png').lower()
        if ext not in ('.png', '.jpg', '.jpeg', '.gif', '.webp'):
            ext = '.png'
        avatar_filename = f'{user_id}{ext}'
        avatars_dir = Path(app.config['AVATARS_FOLDER'])
        if not avatars_dir.is_absolute():
            avatars_dir = Path(app.root_path) / avatars_dir
        avatars_dir.mkdir(parents=True, exist_ok=True)
        filepath = avatars_dir / avatar_filename
        file.save(str(filepath))

        avatar_url = f'/api/avatar/{avatar_filename}'
        ok, err = user_model.update_user_info(user_id, avatar_url=avatar_url)
        if not ok:
            return jsonify({'error': err or '更新失败'}), 500
        user = user_model.get_user_by_id(user_id)
        return jsonify({'user': {**user, 'account_type': user.get('account_type', 'student')}})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/avatar/<path:filename>')
def serve_avatar(filename):
    """提供头像图片访问"""
    try:
        from flask import send_from_directory
        avatars_dir = Path(app.config['AVATARS_FOLDER'])
        if not avatars_dir.is_absolute():
            avatars_dir = Path(app.root_path) / avatars_dir
        return send_from_directory(str(avatars_dir), filename)
    except Exception:
        return jsonify({'error': '文件不存在'}), 404


# ========== 用户作品集（导出视频保存到个人账户，支持改标题、删除） ==========

def _current_user_id():
    """从 Authorization 获取当前用户 id，返回 (user_id, None) 或 (None, (jsonify_resp, status_code))"""
    auth = request.headers.get('Authorization') or ''
    token = auth.replace('Bearer ', '').strip()
    if not token:
        return None, (jsonify({'error': '未登录'}), 401)
    payload, err = verify_jwt_token(token)
    if err:
        return None, (jsonify({'error': err}), 401)
    user_id = payload.get('user_id')
    user = user_model.get_user_by_id(user_id)
    if not user:
        return None, (jsonify({'error': '用户不存在'}), 401)
    return str(user_id), None


def _user_works_path():
    p = Path(app.root_path) / 'data' / 'user_works.json'
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_user_works():
    path = _user_works_path()
    if not path.exists():
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('works') if isinstance(data, dict) else (data if isinstance(data, list) else [])
    except Exception:
        return []


def _save_user_works(works):
    path = _user_works_path()
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'works': works}, f, ensure_ascii=False, indent=2)


@app.route('/api/user/works', methods=['GET'])
def user_works_list():
    """当前用户的视频作品列表"""
    user_id, err = _current_user_id()
    if err:
        return err[0], err[1]
    works = _load_user_works()
    mine = [w for w in works if str(w.get('user_id')) == str(user_id)]
    mine.sort(key=lambda x: (x.get('created_at') or ''), reverse=True)
    return jsonify({'works': mine})


@app.route('/api/user/works', methods=['POST'])
def user_works_add():
    """保存一条视频作品（标题 + 视频 URL）"""
    user_id, err = _current_user_id()
    if err:
        return err[0], err[1]
    data = request.get_json() or {}
    from datetime import datetime
    default_title = '皮影作品 ' + datetime.utcnow().strftime('%Y-%m-%d %H:%M')
    title = (data.get('title') or '').strip() or default_title
    video_url = (data.get('video_url') or '').strip()
    if not video_url:
        return jsonify({'error': '缺少 video_url'}), 400
    works = _load_user_works()
    work_id = str(uuid.uuid4())
    now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    works.append({
        'id': work_id,
        'user_id': user_id,
        'title': title,
        'video_url': video_url,
        'created_at': now,
    })
    _save_user_works(works)
    return jsonify({'id': work_id, 'title': title, 'video_url': video_url, 'created_at': now})


@app.route('/api/user/works/<work_id>', methods=['PATCH'])
def user_works_update(work_id):
    """修改作品标题"""
    user_id, err = _current_user_id()
    if err:
        return err[0], err[1]
    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({'error': '标题不能为空'}), 400
    works = _load_user_works()
    for w in works:
        if str(w.get('id')) == str(work_id) and str(w.get('user_id')) == str(user_id):
            w['title'] = title
            _save_user_works(works)
            return jsonify({'id': work_id, 'title': title})
    return jsonify({'error': '作品不存在'}), 404


@app.route('/api/user/works/<work_id>', methods=['DELETE'])
def user_works_delete(work_id):
    """删除一条作品"""
    user_id, err = _current_user_id()
    if err:
        return err[0], err[1]
    works = _load_user_works()
    new_list = [w for w in works if not (str(w.get('id')) == str(work_id) and str(w.get('user_id')) == str(user_id))]
    if len(new_list) == len(works):
        return jsonify({'error': '作品不存在'}), 404
    _save_user_works(new_list)
    return jsonify({'ok': True})


# ========== 教学 API（课程/班级/作业，本地文件存储，无需 PostgreSQL） ==========

def _teach_current_user():
    """从 Authorization 获取当前用户，返回 (user_id, user_dict) 或 (None, jsonify_error)"""
    auth = request.headers.get('Authorization') or ''
    token = auth.replace('Bearer ', '').strip()
    if not token:
        return None, (jsonify({'message': '未登录'}), 401)
    payload, err = verify_jwt_token(token)
    if err:
        return None, (jsonify({'message': err}), 401)
    user_id = payload.get('user_id')
    user = user_model.get_user_by_id(user_id)
    if not user:
        return None, (jsonify({'message': '用户不存在'}), 401)
    return user_id, user


@app.route('/api/teach/courses', methods=['GET'])
def teach_courses_list():
    """我的课程（我创建的 + 我加入的班级所属课程）"""
    try:
        out = _teach_current_user()
        if out[0] is None:
            return out[1][0], out[1][1]
        user_id = out[0]
        from src.teach_store import list_courses
        data = list_courses(user_id)
        return jsonify(data)
    except Exception as e:
        return jsonify({'message': str(e)}), 500


@app.route('/api/teach/courses', methods=['POST'])
def teach_courses_create():
    """创建课程（仅教师）"""
    try:
        out = _teach_current_user()
        if out[0] is None:
            return out[1][0], out[1][1]
        user_id = out[0]
        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        if not title:
            return jsonify({'message': '课程名称不能为空'}), 400
        from src.teach_store import create_course
        c = create_course(user_id, title, data.get('gradeBand'), data.get('description'))
        if not c:
            return jsonify({'message': '创建失败'}), 500
        return jsonify(c)
    except Exception as e:
        return jsonify({'message': str(e)}), 500


@app.route('/api/teach/courses/<course_id>', methods=['GET'])
def teach_course_get(course_id):
    """课程详情（含课时列表）"""
    try:
        out = _teach_current_user()
        if out[0] is None:
            return out[1][0], out[1][1]
        from src.teach_store import get_course
        c = get_course(course_id)
        if not c:
            return jsonify({'message': '课程不存在'}), 404
        return jsonify(c)
    except Exception as e:
        return jsonify({'message': str(e)}), 500


@app.route('/api/teach/courses/<course_id>/lessons', methods=['POST'])
def teach_lesson_create(course_id):
    """创建课时"""
    try:
        out = _teach_current_user()
        if out[0] is None:
            return out[1][0], out[1][1]
        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        if not title:
            return jsonify({'message': '课时名称不能为空'}), 400
        from src.teach_store import create_lesson
        lesson = create_lesson(course_id, title, data.get('content'), data.get('order', 0))
        if not lesson:
            return jsonify({'message': '课程不存在或创建失败'}), 400
        return jsonify(lesson)
    except Exception as e:
        return jsonify({'message': str(e)}), 500


@app.route('/api/teach/classes', methods=['GET'])
def teach_classes_list():
    """班级列表（可选 courseId 筛选）"""
    try:
        out = _teach_current_user()
        if out[0] is None:
            return out[1][0], out[1][1]
        from src.teach_store import list_classes
        course_id = request.args.get('courseId')
        items = list_classes(course_id)
        return jsonify(items)
    except Exception as e:
        return jsonify({'message': str(e)}), 500


@app.route('/api/teach/classes', methods=['POST'])
def teach_classes_create():
    """创建班级"""
    try:
        out = _teach_current_user()
        if out[0] is None:
            return out[1][0], out[1][1]
        data = request.get_json() or {}
        course_id = data.get('courseId')
        name = (data.get('name') or '').strip()
        if not course_id or not name:
            return jsonify({'message': '请选择课程并填写班级名称'}), 400
        from src.teach_store import create_class
        cl = create_class(course_id, name)
        if not cl:
            return jsonify({'message': '课程不存在或创建失败'}), 400
        return jsonify(cl)
    except Exception as e:
        return jsonify({'message': str(e)}), 500


@app.route('/api/teach/classes/join', methods=['POST'])
def teach_classes_join():
    """学生通过邀请码加入班级"""
    try:
        out = _teach_current_user()
        if out[0] is None:
            return out[1][0], out[1][1]
        user_id = out[0]
        data = request.get_json() or {}
        join_code = data.get('joinCode') or ''
        from src.teach_store import join_class
        result = join_class(user_id, join_code)
        if not result:
            return jsonify({'message': '邀请码无效'}), 400
        if result.get('already'):
            return jsonify({'message': '已在班级中', 'class': result['class']})
        return jsonify(result['class'])
    except Exception as e:
        return jsonify({'message': str(e)}), 500


@app.route('/api/teach/classes/<class_id>', methods=['GET'])
def teach_class_get(class_id):
    """班级详情（含成员、作业）"""
    try:
        out = _teach_current_user()
        if out[0] is None:
            return out[1][0], out[1][1]
        from src.teach_store import get_class
        cl = get_class(class_id)
        if not cl:
            return jsonify({'message': '班级不存在'}), 404
        return jsonify(cl)
    except Exception as e:
        return jsonify({'message': str(e)}), 500


@app.route('/api/teach/assignments', methods=['GET'])
def teach_assignments_list():
    """作业列表（可选 classId）"""
    try:
        out = _teach_current_user()
        if out[0] is None:
            return out[1][0], out[1][1]
        from src.teach_store import list_assignments
        class_id = request.args.get('classId')
        items = list_assignments(class_id)
        return jsonify(items)
    except Exception as e:
        return jsonify({'message': str(e)}), 500


@app.route('/api/teach/assignments', methods=['POST'])
def teach_assignments_create():
    """发布作业"""
    try:
        out = _teach_current_user()
        if out[0] is None:
            return out[1][0], out[1][1]
        data = request.get_json() or {}
        class_id = data.get('classId')
        title = (data.get('title') or '').strip()
        if not class_id or not title:
            return jsonify({'message': '请选择班级并填写作业标题'}), 400
        from src.teach_store import create_assignment
        a = create_assignment(class_id, title, data.get('spec'), data.get('dueAt'))
        return jsonify(a)
    except Exception as e:
        return jsonify({'message': str(e)}), 500


@app.route('/api/teach/submissions', methods=['GET'])
def teach_submissions_list():
    """提交列表（assignmentId / studentId）"""
    try:
        out = _teach_current_user()
        if out[0] is None:
            return out[1][0], out[1][1]
        from src.teach_store import list_submissions
        assignment_id = request.args.get('assignmentId')
        student_id = request.args.get('studentId')
        items = list_submissions(assignment_id, student_id)
        return jsonify(items)
    except Exception as e:
        return jsonify({'message': str(e)}), 500


@app.route('/api/teach/submissions', methods=['POST'])
def teach_submissions_create():
    """提交作业"""
    try:
        out = _teach_current_user()
        if out[0] is None:
            return out[1][0], out[1][1]
        user_id = out[0]
        data = request.get_json() or {}
        assignment_id = data.get('assignmentId')
        payload = data.get('payload', {})
        if not assignment_id:
            return jsonify({'message': '请选择作业'}), 400
        from src.teach_store import create_submission
        s = create_submission(assignment_id, user_id, payload)
        return jsonify(s)
    except Exception as e:
        return jsonify({'message': str(e)}), 500


@app.route('/api/teach/submissions/<submission_id>/grade', methods=['POST'])
def teach_submissions_grade(submission_id):
    """教师评分"""
    try:
        out = _teach_current_user()
        if out[0] is None:
            return out[1][0], out[1][1]
        data = request.get_json() or {}
        score = data.get('score')
        if score is None:
            return jsonify({'message': '请填写分数'}), 400
        from src.teach_store import grade_submission
        s = grade_submission(submission_id, score, data.get('feedback'), data.get('rubricScores'))
        if not s:
            return jsonify({'message': '提交不存在'}), 404
        return jsonify(s)
    except Exception as e:
        return jsonify({'message': str(e)}), 500


@app.route('/api/teach/performances', methods=['POST'])
def teach_performances_save():
    """保存舞台工程（占位，存到本地文件即可）"""
    try:
        out = _teach_current_user()
        if out[0] is None:
            return out[1][0], out[1][1]
        data = request.get_json() or {}
        pid = str(uuid.uuid4())
        out_dir = Path(app.config['OUTPUT_FOLDER']) / 'teach_performances'
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f'{pid}.json'
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return jsonify({'id': pid})
    except Exception as e:
        return jsonify({'message': str(e)}), 500


@app.route('/api/teach/performances/<perf_id>', methods=['GET'])
def teach_performances_get(perf_id):
    """获取舞台工程"""
    try:
        out = _teach_current_user()
        if out[0] is None:
            return out[1][0], out[1][1]
        out_dir = Path(app.config['OUTPUT_FOLDER']) / 'teach_performances'
        path = out_dir / f'{perf_id}.json'
        if not path.exists():
            return jsonify({'message': '作品不存在'}), 404
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({'message': str(e)}), 500


@app.route('/api/teach/performances/<perf_id>/render', methods=['POST'])
def teach_performances_render(perf_id):
    """舞台导出渲染（占位：返回 taskId，后续可接真实渲染）"""
    try:
        out = _teach_current_user()
        if out[0] is None:
            return out[1][0], out[1][1]
        task_id = str(uuid.uuid4())
        return jsonify({'taskId': task_id, 'message': '已提交渲染任务（当前为占位）'})
    except Exception as e:
        return jsonify({'message': str(e)}), 500


@app.route('/api/teach/motion/animated-drawings', methods=['POST'])
def teach_motion_animated_drawings():
    """AnimatedDrawings 代理（占位：后续可接真实服务）"""
    try:
        return jsonify({'message': '功能占位，后续可接入 AnimatedDrawings 服务', 'url': None}), 501
    except Exception as e:
        return jsonify({'message': str(e)}), 500


# ---------- 教学资源（frontend/public/教学资源，与课程资源共用；+ 教师上传） ----------

def _teaching_resources_root() -> Path:
    """教学资源目录：已挪到 frontend/public/教学资源"""
    return (Path(app.root_path).parent / 'frontend' / 'public' / '教学资源').resolve()

def _teach_resources_static_dir():
    """教学资源静态目录（与课程资源同一文件夹）"""
    return _teaching_resources_root()

def _teach_resources_uploads_dir():
    """教师上传存放目录，与学生端共用同一列表即同步可见"""
    d = Path(__file__).resolve().parent / "data" / "teach_resources"
    d.mkdir(parents=True, exist_ok=True)
    return d

def _build_static_tree(base_path, relative_path=""):
    """递归构建静态资源目录树，用于前端按文件夹折叠展示。relative_path 为相对 base_path 的路径。"""
    base_path = Path(base_path)
    current = (base_path / relative_path) if relative_path else base_path
    exclude_root_files = {'皮影戏的由来_百度百科.html', '补充资源清单.md', '皮影戏的由来 百度百科.html'}
    children = []
    files = []
    if not current.exists() or not current.is_dir():
        name = Path(relative_path).name if relative_path else '教学资源'
        return {'name': name, 'path': relative_path, 'children': [], 'files': []}
    for f in sorted(current.iterdir()):
        if f.name.startswith('.'):
            continue
        if f.is_file():
            if f.suffix.lower() == '.xlsx':
                continue
            if not relative_path and f.name in exclude_root_files:
                continue
            rel = f"{relative_path}/{f.name}" if relative_path else f.name
            files.append({'name': f.name, 'url': f'/api/teach/resources/file/static/{rel}', 'type': 'static'})
        else:
            child_rel = f"{relative_path}/{f.name}" if relative_path else f.name
            child = _build_static_tree(base_path, child_rel)
            child['name'] = f.name
            children.append(child)
    name = Path(relative_path).name if relative_path else '教学资源'
    return {'name': name, 'path': relative_path, 'children': children, 'files': files}


def _read_video_links_xlsx():
    """读取 视频链接.xlsx，返回 [{ title, url }, ...]，兼容常见列名"""
    xlsx_path = _teach_resources_static_dir() / "视频链接.xlsx"
    if not xlsx_path.exists():
        return []
    try:
        import pandas as pd
        df = pd.read_excel(str(xlsx_path))
        if df.empty:
            return []
        # 兼容列名：标题/名称/题目, 链接/URL/地址/网址
        title_col = None
        url_col = None
        for c in df.columns:
            c_lower = str(c).strip().lower()
            if c_lower in ('标题', '名称', '题目', 'title', '视频名'):
                title_col = c
            if c_lower in ('链接', 'url', '地址', '网址', '视频链接', 'link'):
                url_col = c
        if title_col is None:
            title_col = df.columns[0]
        if url_col is None:
            for c in df.columns:
                if c != title_col and df[c].astype(str).str.match(r'https?://', na=False).any():
                    url_col = c
                    break
            if url_col is None and len(df.columns) >= 2:
                url_col = df.columns[1]
        if url_col is None:
            return []
        out = []
        for _, row in df.iterrows():
            title = str(row.get(title_col, '')).strip()
            url = str(row.get(url_col, '')).strip()
            if url and (url.startswith('http://') or url.startswith('https://')):
                out.append({'title': title or '视频链接', 'url': url})
        return out
    except Exception:
        return []

@app.route('/api/teach/resources', methods=['GET'])
def teach_resources_list():
    """教学资源：按目录树返回静态资源 + 视频链接 + 教师上传列表，便于前端分板块折叠展示"""
    try:
        out = _teach_current_user()
        if out[0] is None:
            return out[1][0], out[1][1]
        static_dir = _teach_resources_static_dir()
        uploads_dir = _teach_resources_uploads_dir()
        static_tree = _build_static_tree(static_dir) if static_dir.exists() else {'name': '教学资源', 'path': '', 'children': [], 'files': []}
        upload_files = []
        if uploads_dir.exists():
            for f in uploads_dir.iterdir():
                if f.is_file() and not f.name.startswith('.'):
                    upload_files.append({
                        'name': f.name,
                        'url': f'/api/teach/resources/file/upload/{f.name}',
                        'type': 'upload',
                    })
        video_links = _read_video_links_xlsx()
        return jsonify({'videoLinks': video_links, 'staticTree': static_tree, 'uploadFiles': upload_files})
    except Exception as e:
        return jsonify({'message': str(e)}), 500


@app.route('/api/teach/resources/file/<path:subpath>', methods=['GET'])
def teach_resources_file(subpath):
    """下载/查看教学资源文件。subpath 为 static/相对路径 或 upload/文件名（静态支持子目录如 static/子文件夹/文件.png）"""
    try:
        out = _teach_current_user()
        if out[0] is None:
            return out[1][0], out[1][1]
        parts = subpath.split('/', 1)
        if len(parts) < 2:
            return jsonify({'message': '无效路径'}), 400
        kind, rest = parts[0], parts[1]
        if '..' in rest or rest.startswith('/'):
            return jsonify({'message': '无效路径'}), 400
        if kind == 'static':
            base = _teach_resources_static_dir()
            path = (base / rest).resolve()
        elif kind == 'upload':
            base = _teach_resources_uploads_dir()
            path = (base / secure_filename(os.path.basename(rest))).resolve()
        else:
            return jsonify({'message': '无效类型'}), 400
        try:
            path.relative_to(base.resolve())
        except ValueError:
            return jsonify({'message': '文件不存在'}), 404
        if not path.is_file():
            return jsonify({'message': '文件不存在'}), 404
        from flask import send_file
        download_name = path.name
        return send_file(str(path), as_attachment=False, download_name=download_name)
    except Exception as e:
        return jsonify({'message': str(e)}), 500


@app.route('/api/teach/resources/upload', methods=['POST'])
def teach_resources_upload():
    """教师上传文件，存入 teach_resources，学生端列表自动同步可见"""
    try:
        out = _teach_current_user()
        if out[0] is None:
            return out[1][0], out[1][1]
        user_id, user = out[0], out[1]
        if user.get('account_type') != 'teacher':
            return jsonify({'message': '仅教师可上传教学资源'}), 403
        if 'file' not in request.files:
            return jsonify({'message': '请选择文件'}), 400
        f = request.files['file']
        if not f or not f.filename:
            return jsonify({'message': '请选择文件'}), 400
        filename = secure_filename(f.filename)
        if not filename:
            return jsonify({'message': '文件名无效'}), 400
        uploads_dir = _teach_resources_uploads_dir()
        path = uploads_dir / filename
        f.save(str(path))
        return jsonify({'name': filename, 'url': f'/api/teach/resources/file/upload/{filename}'})
    except Exception as e:
        return jsonify({'message': str(e)}), 500


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


# 作品集示例视频：优先 backend/static/demo.mp4（英文路径），便于稳定播放
def _find_case_video_path():
    """返回示例视频的绝对路径。若有 生成结果.mp4 会尝试复制为 static/demo.mp4。"""
    base = Path(__file__).resolve().parent
    project_root = base.parent
    static_dir = base / 'static'
    demo_mp4 = static_dir / 'demo.mp4'
    src_cn = project_root / 'frontend' / 'public' / '视频' / '生成结果.mp4'

    if demo_mp4.is_file():
        return demo_mp4
    if src_cn.is_file():
        try:
            import shutil
            static_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src_cn), str(demo_mp4))
            return demo_mp4
        except Exception:
            return src_cn

    for p in [
        project_root / 'frontend' / 'public' / '视频' / '生成结果.mp4',
        Path.cwd() / 'frontend' / 'public' / '视频' / '生成结果.mp4',
        base / 'static' / '生成结果.mp4',
    ]:
        try:
            if p.is_file():
                return p
        except Exception:
            continue
    return None


@app.route('/api/public/video/case')
def serve_public_case_video():
    """作品集示例视频：返回 MP4 文件流"""
    from flask import send_file
    path = _find_case_video_path()
    if not path:
        return jsonify({
            'error': '未找到示例视频。请将 生成结果.mp4 放入 frontend/public/视频/ 或复制为 backend/static/demo.mp4 后重启后端。'
        }), 404
    try:
        resp = send_file(
            str(path),
            mimetype='video/mp4',
            as_attachment=False,
            conditional=True,
        )
        resp.headers['Accept-Ranges'] = 'bytes'
        resp.headers['Cache-Control'] = 'public, max-age=3600'
        return resp
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate_script', methods=['POST'])
def generate_script():
    """生成剧本API"""
    try:
        data = request.json
        theme = data.get('theme', '')
        character = data.get('character', '孙悟空')
        length = int(data.get('length', 5))
        api_key = data.get('api_key', None)
        
        if not theme:
            return jsonify({'error': '主题不能为空'}), 400
        
        generator = ScriptGenerator(api_key=api_key) if api_key else script_generator
        script = generator.generate_script(theme, character, length)
        action_sequence = generator.convert_script_to_actions(script)
        
        session_id = str(uuid.uuid4())
        session['script_' + session_id] = json.dumps(script, ensure_ascii=False)
        session['actions_' + session_id] = json.dumps(action_sequence, ensure_ascii=False)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'script': script,
            'action_sequence': action_sequence
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/capture_motion', methods=['POST'])
def capture_motion():
    """动作捕捉API"""
    try:
        if 'video' not in request.files:
            return jsonify({'error': '没有上传视频文件'}), 400
        
        file = request.files['video']
        if file.filename == '':
            return jsonify({'error': '文件名为空'}), 400
        
        filename = secure_filename(file.filename)
        session_id = str(uuid.uuid4())
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f'{session_id}_{filename}')
        file.save(filepath)
        
        try:
            detector = FullBodyDetector()
            joints_sequence = detector.detect_video_24_joints(filepath)
            
            if not joints_sequence or len(joints_sequence) == 0:
                return jsonify({'error': '未检测到动作，请检查视频文件'}), 400
            
            converter = BVH24JointsConverter()
            bvh_path = os.path.join(app.config['OUTPUT_FOLDER'], f'{session_id}.bvh')
            converter.convert_24_joints_to_bvh(joints_sequence, bvh_path, frame_rate=30.0)
            session['bvh_' + session_id] = bvh_path
            
            return jsonify({
                'success': True,
                'session_id': session_id,
                'bvh_path': bvh_path,
                'frames': len(joints_sequence)
            })
        except Exception as e:
            return jsonify({'error': f'处理失败: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/camera_pose_frame', methods=['POST'])
def camera_pose_frame():
    """Realtime single-frame pose mapping for webcam."""
    try:
        if realtime_pose_mapper is None:
            detail = realtime_pose_mapper_error or 'unknown init error'
            return jsonify({'success': False, 'error': f'realtime pose tracker unavailable: {detail}'}), 503
        if cv2 is None or np is None:
            return jsonify({'success': False, 'error': 'opencv/numpy unavailable in backend runtime'}), 503

        data = request.get_json(silent=True) or {}
        image_data = data.get('image') or data.get('frame')
        if not image_data or not isinstance(image_data, str):
            return jsonify({'success': False, 'error': 'missing image frame'}), 400

        # data URL support: data:image/jpeg;base64,....
        if ',' in image_data:
            image_data = image_data.split(',', 1)[1]

        try:
            raw = base64.b64decode(image_data)
        except Exception:
            return jsonify({'success': False, 'error': 'invalid base64 image'}), 400

        frame = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            return jsonify({'success': False, 'error': 'unable to decode image'}), 400

        result = realtime_pose_mapper.process_bgr(frame)
        if not result:
            return jsonify({'success': True, 'detected': False})

        return jsonify({
            'success': True,
            'detected': True,
            'joints': result.get('joints', {}),
            'puppet_pose': result.get('puppet_pose', {}),
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/unity_pose_frame', methods=['POST'])
def unity_pose_frame():
    """接收 Unity 每帧姿态数据（桥接到 Web）。"""
    try:
        data = request.get_json(silent=True) or {}
        puppet_pose = data.get('puppet_pose') or data.get('pose')
        joints = data.get('joints')
        if not isinstance(puppet_pose, dict):
            return jsonify({'success': False, 'error': 'missing puppet_pose object'}), 400

        normalized = dict(puppet_pose)
        # 兼容未携带置信度的 Unity 帧
        if not isinstance(normalized.get('confidence'), (int, float)):
            normalized['confidence'] = 1.0

        unity_pose_latest['updatedAt'] = time.time()
        unity_pose_latest['source'] = 'unity'
        unity_pose_latest['puppet_pose'] = normalized
        unity_pose_latest['joints'] = joints if isinstance(joints, dict) else None

        return jsonify({'success': True, 'updatedAt': unity_pose_latest['updatedAt']})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/unity_pose_frame_latest', methods=['GET'])
def unity_pose_frame_latest():
    """读取 Unity 最新姿态帧。"""
    try:
        now = time.time()
        updated_at = float(unity_pose_latest.get('updatedAt') or 0.0)
        stale_after = 1.5
        stale = (now - updated_at) > stale_after
        has_pose = isinstance(unity_pose_latest.get('puppet_pose'), dict)
        return jsonify({
            'success': True,
            'detected': bool(has_pose and not stale),
            'stale': stale,
            'source': unity_pose_latest.get('source') or 'unity',
            'updatedAt': updated_at,
            'puppet_pose': unity_pose_latest.get('puppet_pose') if has_pose else None,
            'joints': unity_pose_latest.get('joints') if isinstance(unity_pose_latest.get('joints'), dict) else None,
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/label_actions', methods=['POST'])
def label_actions():
    """动作标签API"""
    try:
        data = request.json
        action_sequence = data.get('action_sequence', [])
        if not action_sequence:
            return jsonify({'error': '动作序列为空'}), 400
        
        import numpy as np
        labeled_actions = []
        for action in action_sequence:
            action_data = action['action_data']
            params = np.array([list(action_data['parameters'].values())[:3]])
            similar = action_library.find_similar_action(params, top_k=1)
            if similar:
                action_name, similarity = similar[0]
                emotion = action_library.get_emotion(action_name)
                action['action_name'] = action_name
                action['emotion'] = emotion
                action['similarity'] = float(similarity)
            labeled_actions.append(action)
        
        return jsonify({'success': True, 'labeled_actions': labeled_actions})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download/<session_id>')
def download_file(session_id):
    """下载文件API"""
    try:
        file_type = request.args.get('type', 'bvh')
        file_param = request.args.get('file')
        
        if file_type == 'video' and file_param:
            filepath = os.path.join(app.config['OUTPUT_FOLDER'], session_id, file_param)
            download_name = file_param
        elif file_type == 'bvh':
            filepath = os.path.join(app.config['OUTPUT_FOLDER'], f'{session_id}.bvh')
            download_name = f'piying_motion_{session_id[:8]}.bvh'
        elif file_type == 'script':
            script_key = 'script_' + session_id
            if script_key in session:
                script_data = json.loads(session[script_key])
                filepath = os.path.join(app.config['OUTPUT_FOLDER'], f'{session_id}_script.json')
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(script_data, f, indent=2, ensure_ascii=False)
                download_name = f'piying_script_{session_id[:8]}.json'
            else:
                return jsonify({'error': '剧本数据不存在'}), 404
        else:
            return jsonify({'error': '不支持的文件类型'}), 400
        
        if not os.path.exists(filepath):
            return jsonify({'error': '文件不存在'}), 404
        
        return send_file(filepath, as_attachment=True, download_name=download_name)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/action_library')
def get_action_library():
    """获取动作库信息"""
    try:
        emotions = action_library.get_all_emotions()
        emotion_info = {e: action_library.EMOTION_LABELS.get(e, {}) for e in emotions}
        return jsonify({
            'success': True,
            'emotions': emotions,
            'emotion_info': emotion_info,
            'action_count': len(action_library.actions)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# 数字人/体感交互已改用 Unity 皮影体感成品项目，见 backend/Assets（PiYing + Kinect）


# ========== 文生图 API（豆包/火山方舟，需配置 DOUBAO_API_KEY） ==========

# 豆包文生图接口地址（火山方舟）
DOUBAO_IMAGE_URL = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
# 文生图模型：.env 的 DOUBAO_IMAGE_MODEL 为推理接入点 ID（如 ep-20260215202359-9t5lz）
DOUBAO_IMAGE_MODEL_DEFAULT = "ep-20260215202359-9t5lz"

# 皮影人物通用 Prompt 模板（分片缀合+镂空雕刻）
PROMPT_TEMPLATE_PIYING_CHARACTER = (
    "中国传统皮影戏人物，单人全身，__ROLE_DESC__。"
    "核心结构与工艺：人物由多个独立部件分片缀合而成，头、胸腹、腰腿、大小臂、手为明确分开的片状结构，"
    "关节处（肩/肘/腕/髋/膝/踝）非一体连接，用线环或铆钉串联，形成明显的分段感。身体为平面剪影，无体积感。"
    "雕刻特征：镂空雕刻，内部纹样（花卉、云纹、卷草）多为透雕/阳刻，即纹样轮廓以实线保留，其余部分完全剔除，"
    "形成光影穿透效果；服饰边缘及内部有大量镂空图案，非实心填色。人物轮廓边缘清晰锐利。"
    "视角与造型：严格正侧面，仅见一只眼、半边脸，肩膀与躯干不转向观众。"
    "姿态：四肢细长，呈行走或表演姿态，背后可见三根细操纵杆（胸部、手部连接）。"
    "色彩与质感：半透明皮革质感（驴皮/牛皮），低饱和度传统配色（朱红、胭脂、暗黄、灰蓝、墨绿、黑金），色彩沉稳不刺眼。黑色/深棕色勾边，勾边线条清晰。"
    "构图：角色居中，纯黑色背景，无场景、无阴影、无文字水印，高清。"
)
# 负面描述（豆包无单独 negative_prompt 时拼入 prompt 末尾）
NEGATIVE_PROMPT_PIYING = (
    "避免：照片写实、3D、一体成型无分段、实心填色、正面脸、半侧面、高饱和、背景复杂、文字水印。"
)


def _try_remove_background(save_path: Path) -> None:
    """人物抠图：将图片背景变为透明，原地覆盖为 PNG。依赖 rembg。"""
    try:
        from rembg import remove as rembg_remove
        from PIL import Image
        with open(str(save_path), 'rb') as f:
            inp = f.read()
        out = rembg_remove(inp)
        img = Image.open(io.BytesIO(out))
        img.save(str(save_path), 'PNG')
    except ImportError as e:
        print(f"[rembg] 未安装或依赖缺失，角色图将保留原背景。请执行: pip install \"rembg[cpu]\"。详情: {e}")
    except Exception as e:
        print(f"[rembg] 抠图跳过: {e}")


def _doubao_bearer_token():
    """从 .env 读取 DOUBAO_API_KEY（或 ARK_API_KEY），原样作为 Bearer 使用，与官方 curl 一致。"""
    raw = (os.environ.get('DOUBAO_API_KEY') or os.environ.get('ARK_API_KEY') or '').strip()
    return raw or None


def _generate_image_via_maas(prompt: str, gen_type: str, output_dir: Path, session_id: str):
    """火山引擎 MaaS 文生图：使用 AK/SK + endpoint_id，调用 images.quick_gen（与官方示例一致）。"""
    ak = os.environ.get('VOLC_ACCESSKEY', '').strip()
    sk = os.environ.get('VOLC_SECRETKEY', '').strip()
    endpoint_id = os.environ.get('DOUBAO_IMAGE_MODEL', '').strip()
    if not ak or not sk or not endpoint_id:
        return None
    try:
        from volcengine.maas.v2 import MaasService
        from volcengine.maas import MaasException
        import base64 as b64
        maas = MaasService('maas-api.ml-platform-cn-beijing.volces.com', 'cn-beijing')
        maas.set_ak(ak)
        maas.set_sk(sk)
        if gen_type == 'characters':
            role_desc = prompt.strip() or "旦角"
            full_prompt = PROMPT_TEMPLATE_PIYING_CHARACTER.replace("__ROLE_DESC__", role_desc)
            neg = NEGATIVE_PROMPT_PIYING
        else:
            full_prompt = f"皮影戏舞台背景，{prompt}"
            neg = "避免：现代、照片写实、3D、复杂场景、文字水印。"
        req = {
            "prompt": full_prompt,
            "negative_prompt": neg,
            "control_image_list": [],  # 纯文生图不传图
            "parameters": {},
        }
        resp = maas.images.quick_gen(endpoint_id, req)
        # 响应里通常有 images 或 data，需按实际 SDK 返回解析
        images = (resp or {}).get("images") or (resp or {}).get("data") or []
        if isinstance(images, dict):
            images = images.get("image_list") or images.get("images") or []
        raw_b64 = None
        if isinstance(images, list) and len(images) > 0:
            first = images[0]
            if isinstance(first, dict):
                raw_b64 = first.get("b64_image") or first.get("image") or first.get("content")
            elif isinstance(first, str):
                raw_b64 = first
        if not raw_b64:
            print("[MaaS 文生图] 响应中未找到图片:", resp)
            return None
        filename = "generated.png"
        save_path = output_dir / filename
        raw = b64.b64decode(raw_b64)
        with open(save_path, "wb") as f:
            f.write(raw)
        if gen_type == 'characters':
            _try_remove_background(save_path)
        return f"/api/generated_image/{session_id}/{filename}"
    except Exception as e:
        print(f"[MaaS 文生图] 失败: {e}")
    return None


def _generate_image_via_doubao(prompt: str, gen_type: str, output_dir: Path, session_id: str):
    """火山方舟 Ark 文生图：与官方 curl 一致，Bearer + /api/v3/images/generations。"""
    api_key = _doubao_bearer_token()
    if not api_key:
        return None
    model = os.environ.get('DOUBAO_IMAGE_MODEL', '').strip() or DOUBAO_IMAGE_MODEL_DEFAULT
    try:
        import urllib.request
        import urllib.error
        import base64
        if gen_type == 'characters':
            role_desc = prompt.strip() or "旦角"
            enhanced = PROMPT_TEMPLATE_PIYING_CHARACTER.replace("__ROLE_DESC__", role_desc) + " " + NEGATIVE_PROMPT_PIYING
        else:
            enhanced = f"皮影戏舞台背景，{prompt}"
        # 与官方示例一致：sequential_image_generation, response_format, size, stream, watermark
        body = {
            "model": model,
            "prompt": enhanced,
            "sequential_image_generation": "disabled",
            "response_format": "url",
            "size": "2K",
            "stream": False,
            "watermark": True,
        }
        req = urllib.request.Request(
            DOUBAO_IMAGE_URL,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as rsp:
            data = json.loads(rsp.read().decode())
        results = (data.get("data") or data.get("results")) or []
        if not results:
            return None
        first = results[0] if isinstance(results, list) else results
        img_url = first.get("url")
        b64 = first.get("b64_json")
        filename = "generated.png"
        save_path = output_dir / filename
        if img_url:
            urllib.request.urlretrieve(img_url, str(save_path))
        elif b64:
            raw = base64.b64decode(b64)
            with open(save_path, "wb") as f:
                f.write(raw)
        else:
            return None
        if gen_type == 'characters':
            _try_remove_background(save_path)
        return f"/api/generated_image/{session_id}/{filename}"
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode()[:500]
        except Exception:
            pass
        print(f"[方舟文生图] HTTP {e.code}: {e.reason}. {body}")
    except Exception as e:
        print(f"[方舟文生图] 失败: {e}")
    return None


def _do_generate_image(gen_type='characters'):
    """文生图：优先 MaaS（AK/SK + endpoint_id），否则豆包 Bearer API Key。"""
    data = request.get_json() or {}
    prompt = data.get('prompt', '').strip()
    if not prompt:
        return None, 400, '请提供描述文本 (prompt)'

    has_maas = (
        os.environ.get('VOLC_ACCESSKEY', '').strip()
        and os.environ.get('VOLC_SECRETKEY', '').strip()
        and os.environ.get('DOUBAO_IMAGE_MODEL', '').strip()
    )
    has_bearer = bool((os.environ.get('DOUBAO_API_KEY') or os.environ.get('ARK_API_KEY') or '').strip())
    if not has_maas and not has_bearer:
        return None, 500, (
            '文生图需配置其一：'
            '① MaaS：在 .env 中设置 VOLC_ACCESSKEY、VOLC_SECRETKEY、DOUBAO_IMAGE_MODEL（接入点 ID）；'
            '② 方舟 Bearer：设置 DOUBAO_API_KEY'
        )

    base_dir = Path(app.config['GENERATED_IMAGES_FOLDER'])
    if not base_dir.is_absolute():
        base_dir = Path(app.root_path) / base_dir
    session_id = str(uuid.uuid4())
    output_dir = base_dir / session_id
    output_dir.mkdir(parents=True, exist_ok=True)

    image_url = None
    if has_maas:
        image_url = _generate_image_via_maas(prompt, gen_type, output_dir, session_id)
    if not image_url and has_bearer:
        image_url = _generate_image_via_doubao(prompt, gen_type, output_dir, session_id)

    if image_url:
        result = {
            'success': True,
            'id': f"ai-{gen_type}-{session_id[:8]}",
            'name': f"AI生成{('角色' if gen_type == 'characters' else '场景')}：{prompt[:20]}",
            'prompt': prompt,
            'type': gen_type,
            'image_url': image_url,
            'thumbnail': image_url,
        }
        if gen_type == 'scenes':
            result['url'] = image_url
        return result, 200, None

    return None, 500, (
        '文生图失败。若用 MaaS：请确认 VOLC_ACCESSKEY/VOLC_SECRETKEY 为「访问控制→API 访问密钥」，'
        'DOUBAO_IMAGE_MODEL 为 MaaS 接入点 ID（如 ep-m-xxx）。若用方舟：请确认 DOUBAO_API_KEY 为接入点 API Key。'
    )


@app.route('/api/generate_image', methods=['POST'])
def generate_image():
    """文生图统一入口（支持 type: characters | scenes）"""
    gen_type = (request.get_json() or {}).get('type', 'characters')
    result, status, err = _do_generate_image(gen_type)
    if err:
        return jsonify({'error': err}), status
    return jsonify(result)


@app.route('/api/generated_image/<session_id>/<filename>')
def serve_generated_image(session_id, filename):
    """提供生成的图片静态访问"""
    try:
        from flask import send_from_directory
        base_dir = Path(app.config['GENERATED_IMAGES_FOLDER'])
        if not base_dir.is_absolute():
            base_dir = Path(app.root_path) / base_dir
        folder = base_dir / session_id
        return send_from_directory(str(folder), filename)
    except Exception:
        return jsonify({'error': '文件不存在'}), 404


@app.route('/api/generate_character', methods=['POST'])
def generate_character():
    """AI 生成角色（Workbench / AiGenerator 对接）"""
    result, status, err = _do_generate_image('characters')
    if err:
        return jsonify({'error': err}), status
    return jsonify(result)


@app.route('/api/generate_background', methods=['POST'])
def generate_background():
    """AI 生成背景（Workbench 对接）"""
    result, status, err = _do_generate_image('scenes')
    if err:
        return jsonify({'error': err}), status
    return jsonify(result)


# ========== 演出导出流水线（念白 TTS + 音乐混音） ==========
PERFORMANCE_OUTPUT_DIR = Path(app.config['OUTPUT_FOLDER']) / 'performance'


@app.route('/api/tts/generate', methods=['POST'])
def api_tts_generate():
    """念白 TTS：传入台词数组，返回生成的 WAV 的 URL（或错误）。"""
    try:
        data = request.get_json() or {}
        lines = data.get('lines') or []
        if isinstance(lines, str):
            lines = [lines] if lines.strip() else []
        if not lines:
            return jsonify({'success': False, 'error': '请提供台词 lines 数组'}), 400
        session_id = str(uuid.uuid4())
        out_dir = PERFORMANCE_OUTPUT_DIR / session_id
        out_dir.mkdir(parents=True, exist_ok=True)
        from src.pipeline.performance_export import generate_tts_audio
        tts_path, tts_error = generate_tts_audio(lines, out_dir, session_id)
        if not tts_path or not os.path.exists(tts_path):
            return jsonify({'success': False, 'error': tts_error or 'TTS 生成失败'}), 500
        import shutil
        dest = out_dir / "performance.wav"
        if Path(tts_path).resolve() != dest.resolve():
            shutil.copy(tts_path, dest)
        return jsonify({'success': True, 'audio_url': f'/api/performance_audio/{session_id}/performance.wav'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/export/performance', methods=['POST'])
def api_export_performance():
    """
    演出导出（阶段一）：剧本台词 → TTS 念白 → 与上传的背景音乐混音 → 返回音频 URL。
    表单字段：script（JSON 字符串）、music（文件，可选）
    """
    try:
        script_str = request.form.get('script')
        if not script_str:
            return jsonify({'success': False, 'error': '缺少 script'}), 400
        script = json.loads(script_str)
        session_id = str(uuid.uuid4())
        PERFORMANCE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        music_path = None
        if 'music' in request.files:
            f = request.files['music']
            if f.filename:
                ext = Path(f.filename).suffix or '.mp3'
                music_path = str(PERFORMANCE_OUTPUT_DIR / f"{session_id}_music{ext}")
                f.save(music_path)
        from src.pipeline.performance_export import run_performance_export
        out_dir = PERFORMANCE_OUTPUT_DIR / session_id
        result = run_performance_export(script, out_dir, session_id, music_path)
        if not result.get('success'):
            return jsonify({'success': False, 'error': result.get('error', '导出失败')}), 500
        audio_url = result.get('audio_url')
        if not audio_url.startswith('http'):
            audio_url = request.host_url.rstrip('/') + audio_url
        return jsonify({'success': True, 'audio_url': audio_url, 'session_id': session_id})
    except json.JSONDecodeError as e:
        return jsonify({'success': False, 'error': f'script 不是合法 JSON: {e}'}), 400
    except (ConnectionAbortedError, ConnectionError, OSError) as e:
        err_msg = str(e)
        if '10053' in err_msg or 'aborted' in err_msg.lower() or 'Connection aborted' in err_msg:
            return jsonify({
                'success': False,
                'error': '连接已中断。念白生成约需 30 秒，请重试并保持页面不要关闭或刷新。'
            }), 500
        return jsonify({'success': False, 'error': err_msg}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/export/video', methods=['POST'])
def api_export_video():
    """
    阶段三：演出视频导出。

    默认（旧方案）：
    - 剧本 → 念白+音乐（阶段一，可选 MusicGen）→ 静态场景图+音频合成 MP4。

    新方案（图生视频，仅使用一张图+台词+动作/情绪）：
    - 若设置 USE_IMAGE2VIDEO_ONLY=1，则不会再生成念白和混音，
      而是将场景图 + 台词 + 动作序列发送到外部图生视频服务（IMAGE2VIDEO_API_URL），
      由外部服务直接返回完整视频。

    表单字段：
    - script（JSON，必填）
    - frame（可选图片，优先作为场景图；未提供时仍尝试使用背景/角色/占位图，供旧方案或后续扩展使用）
    - music / background / character / action_sequence / video_*：旧方案兼容保留
    """
    try:
        script_str = request.form.get('script')
        if not script_str:
            return jsonify({'success': False, 'error': '缺少 script'}), 400
        script = json.loads(script_str)
        session_id = str(uuid.uuid4())
        PERFORMANCE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_dir = PERFORMANCE_OUTPUT_DIR / session_id
        out_dir.mkdir(parents=True, exist_ok=True)

        music_path = None
        if 'music' in request.files:
            f = request.files['music']
            if f.filename:
                ext = Path(f.filename).suffix or '.mp3'
                music_path = str(out_dir / f"music{ext}")
                f.save(music_path)

        background_path = None
        if 'background' in request.files:
            f = request.files['background']
            if f.filename:
                ext = Path(f.filename).suffix or '.png'
                background_path = str(out_dir / f"background{ext}")
                f.save(background_path)

        character_path = None
        if 'character' in request.files:
            f = request.files['character']
            if f.filename:
                ext = Path(f.filename).suffix or '.png'
                character_path = str(out_dir / f"character{ext}")
                f.save(character_path)

        # 优先使用「场景图/舞台截图」：用户上传的整幅舞台画面
        frame_path = None
        if 'frame' in request.files:
            f = request.files['frame']
            if f.filename:
                ext = Path(f.filename).suffix or '.png'
                frame_path = str(out_dir / f"frame{ext}")
                f.save(frame_path)

        action_sequence = None
        action_str = request.form.get('action_sequence')
        if action_str:
            try:
                action_sequence = json.loads(action_str)
                if not isinstance(action_sequence, list):
                    action_sequence = None
            except Exception:
                pass

        # 视频可调参数（可选）
        def _int_form(key, default=None):
            v = request.form.get(key)
            if v is None or v == '':
                return default
            try:
                return int(v)
            except ValueError:
                return default
        def _float_form(key, default=None):
            v = request.form.get(key)
            if v is None or v == '':
                return default
            try:
                return float(v)
            except ValueError:
                return default
        video_width = _int_form('video_width')
        video_height = _int_form('video_height')
        video_fps = _float_form('video_fps')
        video_bitrate = request.form.get('video_bitrate') or None  # 如 "2M"

        # 优先使用通义万相图生视频（有声视频），通过环境变量 USE_WANX_I2V 控制。
        use_wanx_i2v = os.environ.get("USE_WANX_I2V", "").strip() == "1"
        if use_wanx_i2v:
            from src.pipeline.wanx_image2video import run_wanx_image2video

            # 通义万相图生视频：需要一张场景图；优先使用用户上传 frame，
            # 若没有则回退到 background/character。
            wanx_frame = frame_path or background_path or character_path or ""
            result = run_wanx_image2video(
                script,
                out_dir,
                session_id,
                frame_image_path=wanx_frame,
                action_sequence=action_sequence,
            )
        else:
            # 旧方案：本地念白 + 背景音乐 + 静态/Unity 场景图合成 MP4。
            use_image2video_only = os.environ.get("USE_IMAGE2VIDEO_ONLY", "").strip() == "1"
            if use_image2video_only:
                from src.pipeline.image2video_only import run_image2video_only

                result = run_image2video_only(
                    script,
                    out_dir,
                    session_id,
                    frame_image_path=frame_path or background_path or character_path or "",
                    action_sequence=action_sequence,
                )
            else:
                from src.pipeline.video_export import run_video_export
                backend_root = Path(__file__).resolve().parent
                result = run_video_export(
                    script, out_dir, session_id,
                    music_file_path=music_path,
                    background_image_path=background_path,
                    character_image_path=character_path,
                    frame_image_path=frame_path,
                    action_sequence=action_sequence,
                    video_width=video_width,
                    video_height=video_height,
                    video_fps=video_fps,
                    video_bitrate=video_bitrate,
                    backend_root=backend_root,
                )
        if not result.get('success'):
            return jsonify({'success': False, 'error': result.get('error', '视频导出失败')}), 500

        video_url = result.get('video_url') or ""
        audio_url = result.get('audio_url') or ""
        if video_url and not video_url.startswith('http'):
            video_url = request.host_url.rstrip('/') + video_url
        if audio_url and not audio_url.startswith('http'):
            audio_url = request.host_url.rstrip('/') + audio_url
        return jsonify({
            'success': True,
            'video_url': video_url,
            'audio_url': audio_url,
            'session_id': session_id,
        })
    except json.JSONDecodeError as e:
        return jsonify({'success': False, 'error': f'script 不是合法 JSON: {e}'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/performance_audio/<session_id>/<filename>')
def serve_performance_audio(session_id, filename):
    """提供演出导出的音频/视频文件（念白或念白+音乐混音、或 performance.mp4）"""
    try:
        from flask import send_from_directory
        base = Path(app.config['OUTPUT_FOLDER']) / 'performance'
        folder = base / session_id
        if not folder.exists():
            return jsonify({'error': '文件不存在'}), 404
        return send_from_directory(str(folder), filename)
    except Exception:
        return jsonify({'error': '文件不存在'}), 404


def _trained_puppets_root() -> Path:
    return (Path(app.root_path) / 'Assets' / 'PiYing' / 'Mew').resolve()


def _list_trained_puppet_pngs():
    root = _trained_puppets_root()
    if not root.exists():
        return []
    # Exclude UI/background sprites in the Unity demo folder.
    excluded = {'bbg.png', 'btn.png', 'kuang.png', 'newbg.png', 'river.png', 'startbtn.png'}
    files = []
    for p in root.iterdir():
        if not p.is_file() or p.suffix.lower() != '.png':
            continue
        if p.name.lower() in excluded:
            continue
        files.append(p)
    return sorted(files, key=lambda p: p.name)


@app.route('/api/resources/trained-puppets', methods=['GET'])
def api_trained_puppets_list():
    """List trained puppet images from backend/Assets/PiYing/Mew."""
    try:
        pngs = _list_trained_puppet_pngs()
        items = [
            {
                'id': p.stem,
                'name': p.stem,
                'fileName': p.name,
                'url': f"/api/resources/trained-puppets/file/{quote(p.name)}",
                'previewUrl': f"/api/resources/trained-puppets/file/{quote(p.name)}",
                'source': 'unity-assets',
            }
            for p in pngs
        ]
        return jsonify({
            'root': str(_trained_puppets_root()),
            'total': len(items),
            'items': items,
        })
    except Exception as e:
        return jsonify({'message': str(e)}), 500


@app.route('/api/resources/trained-puppets/file/<path:filename>', methods=['GET'])
def api_trained_puppets_file(filename):
    """Read one trained puppet image from backend/Assets/PiYing/Mew."""
    try:
        root = _trained_puppets_root()
        decoded = unquote(filename)
        file_map = {p.name: p for p in _list_trained_puppet_pngs()}
        if decoded not in file_map:
            return jsonify({'message': '文件不存在'}), 404
        target = file_map[decoded].resolve()
        if not str(target).startswith(str(root)):
            return jsonify({'message': '非法路径'}), 400
        return send_file(str(target))
    except Exception as e:
        return jsonify({'message': str(e)}), 500


def _course_resources_root() -> Path:
    """课程资源/人物分解等：与教学资源共用 frontend/public/教学资源"""
    return _teaching_resources_root()


def _iter_course_material_files():
    root = _course_resources_root()
    if not root.exists():
        return []
    allowed = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.mp3', '.wav', '.txt', '.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xlsx', '.xls'}
    files = []
    for path in root.rglob('*'):
        if not path.is_file():
            continue
        if path.suffix.lower() not in allowed:
            continue
        files.append(path)
    return sorted(files, key=lambda p: str(p))


@app.route('/api/resources/course-materials', methods=['GET'])
def api_course_materials_list():
    """课程资源：读取项目根目录/教学资源 下的素材"""
    try:
        limit = request.args.get('limit', type=int) or 500
        if limit <= 0:
            limit = 500
        root = _course_resources_root()
        files = _iter_course_material_files()[:limit]
        items = []
        for file_path in files:
            rel = file_path.relative_to(root)
            rel_str = str(rel).replace('\\', '/')
            parts = rel_str.split('/')
            category = parts[0] if parts else '其他'
            section = parts[1] if len(parts) > 1 else ''
            items.append({
                'id': rel_str,
                'name': file_path.name,
                'relativePath': rel_str,
                'category': category,
                'section': section,
                'ext': file_path.suffix.lower(),
                'size': file_path.stat().st_size,
                'url': f"/api/resources/course-materials/file/{quote(rel_str)}",
            })
        return jsonify({
            'root': str(root),
            'total': len(items),
            'items': items,
        })
    except Exception as e:
        return jsonify({'message': str(e)}), 500


@app.route('/api/resources/course-materials/file/<path:relative_path>', methods=['GET'])
def api_course_materials_file(relative_path):
    """课程资源：按相对路径读取文件"""
    try:
        root = _course_resources_root()
        decoded = unquote(relative_path)
        target = (root / decoded).resolve()
        if not str(target).startswith(str(root)):
            return jsonify({'message': '非法路径'}), 400
        if not target.exists() or not target.is_file():
            return jsonify({'message': '文件不存在'}), 404
        return send_file(str(target))
    except Exception as e:
        return jsonify({'message': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
