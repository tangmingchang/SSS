/**
 * 鏁欏骞冲彴 API 灏佽锛堣蛋涓诲悗绔紝鏈湴鏂囦欢瀛樺偍锛屾棤闇€ PostgreSQL锛?
 * 鍩哄潃涓庝富绔欎竴鑷达細API_BASE锛堝 http://localhost:5000锛?
 */
import { getToken } from './authService';
import { API_BASE } from '../utils/api';

const TEACH_API_BASE = API_BASE;
const TEACH_PREFIX = `${TEACH_API_BASE}/api/teach`;

function headers() {
  const token = getToken();
  return {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
  };
}

export async function apiCoursesList() {
  const res = await fetch(`${TEACH_PREFIX}/courses`, { headers: headers() });
  if (!res.ok) throw new Error((await res.json()).message || '鑾峰彇璇剧▼澶辫触');
  return res.json();
}

export async function apiCourseCreate(body) {
  const res = await fetch(`${TEACH_PREFIX}/courses`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error((await res.json()).message || '鍒涘缓璇剧▼澶辫触');
  return res.json();
}

export async function apiCourseGet(id) {
  const res = await fetch(`${TEACH_PREFIX}/courses/${id}`, { headers: headers() });
  if (!res.ok) throw new Error((await res.json()).message || '鑾峰彇璇剧▼澶辫触');
  return res.json();
}

export async function apiLessonCreate(courseId, body) {
  const res = await fetch(`${TEACH_PREFIX}/courses/${courseId}/lessons`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error((await res.json()).message || '鍒涘缓璇炬椂澶辫触');
  return res.json();
}

export async function apiClassesList(courseId) {
  const q = courseId ? `?courseId=${encodeURIComponent(courseId)}` : '';
  const res = await fetch(`${TEACH_PREFIX}/classes${q}`, { headers: headers() });
  if (!res.ok) throw new Error((await res.json()).message || '鑾峰彇鐝骇鍒楄〃澶辫触');
  return res.json();
}

export async function apiClassCreate(body) {
  const res = await fetch(`${TEACH_PREFIX}/classes`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error((await res.json()).message || '鍒涘缓鐝骇澶辫触');
  return res.json();
}

export async function apiClassJoin(joinCode) {
  const res = await fetch(`${TEACH_PREFIX}/classes/join`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ joinCode }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.message || '鍔犲叆鐝骇澶辫触');
  return data;
}

export async function apiClassGet(id) {
  const res = await fetch(`${TEACH_PREFIX}/classes/${id}`, { headers: headers() });
  if (!res.ok) throw new Error((await res.json()).message || '鑾峰彇鐝骇澶辫触');
  return res.json();
}

export async function apiAssignmentsList(classId) {
  const q = classId ? `?classId=${encodeURIComponent(classId)}` : '';
  const res = await fetch(`${TEACH_PREFIX}/assignments${q}`, { headers: headers() });
  if (!res.ok) throw new Error((await res.json()).message || '鑾峰彇浣滀笟鍒楄〃澶辫触');
  return res.json();
}

export async function apiAssignmentCreate(body) {
  const res = await fetch(`${TEACH_PREFIX}/assignments`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error((await res.json()).message || '鍙戝竷浣滀笟澶辫触');
  return res.json();
}

export async function apiSubmissionsList(assignmentId, studentId) {
  const params = new URLSearchParams();
  if (assignmentId) params.set('assignmentId', assignmentId);
  if (studentId) params.set('studentId', studentId);
  const q = params.toString() ? `?${params.toString()}` : '';
  const res = await fetch(`${TEACH_PREFIX}/submissions${q}`, { headers: headers() });
  if (!res.ok) throw new Error((await res.json()).message || '鑾峰彇鎻愪氦鍒楄〃澶辫触');
  return res.json();
}

export async function apiSubmissionCreate(assignmentId, payload) {
  const res = await fetch(`${TEACH_PREFIX}/submissions`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ assignmentId, payload }),
  });
  if (!res.ok) throw new Error((await res.json()).message || '鎻愪氦澶辫触');
  return res.json();
}

export async function apiSubmissionGrade(submissionId, body) {
  const res = await fetch(`${TEACH_PREFIX}/submissions/${submissionId}/grade`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error((await res.json()).message || '璇勫垎澶辫触');
  return res.json();
}

export async function apiPerformanceSave(body) {
  const res = await fetch(`${TEACH_PREFIX}/performances`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error((await res.json()).message || '淇濆瓨鑸炲彴澶辫触');
  return res.json();
}

export async function apiPerformanceGet(id) {
  const res = await fetch(`${TEACH_PREFIX}/performances/${id}`, { headers: headers() });
  if (!res.ok) throw new Error((await res.json()).message || '鑾峰彇鑸炲彴澶辫触');
  return res.json();
}

export async function apiPerformanceRender(id, format = 'mp4') {
  const res = await fetch(`${TEACH_PREFIX}/performances/${id}/render`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ format }),
  });
  if (!res.ok) throw new Error((await res.json()).message || '鎻愪氦娓叉煋澶辫触');
  return res.json();
}

export async function apiMotionAnimatedDrawings(file, action = 'walk') {
  const token = getToken();
  const form = new FormData();
  form.append('image', file);
  form.append('action', action);
  const res = await fetch(`${TEACH_PREFIX}/motion/animated-drawings`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.message || '鐢熸垚鍔ㄧ敾澶辫触');
  return data;
}

/** 教学资源列表（静态+上传），师生均可见 */
export async function apiResourcesList() {
  const res = await fetch(`${TEACH_PREFIX}/resources`, { headers: headers() });
  if (!res.ok) throw new Error((await res.json()).message || '获取教学资源失败');
  return res.json();
}

/** 教师上传教学资源，学生端同步可见 */
export async function apiResourcesUpload(file) {
  const token = getToken();
  const form = new FormData();
  form.append('file', file, file.name);
  const res = await fetch(`${TEACH_PREFIX}/resources/upload`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.message || '上传失败');
  return data;
}

export async function apiCourseMaterialResources(limit = 300) {
  const params = new URLSearchParams();
  if (limit) params.set('limit', String(limit));
  const q = params.toString() ? `?${params.toString()}` : '';
  const res = await fetch(`${TEACH_API_BASE}/api/resources/course-materials${q}`, { headers: headers() });
  const data = await res.json();
  if (!res.ok) throw new Error(data.message || '获取课程资源失败');
  const toAbs = (url) => (typeof url === 'string' && url.startsWith('/api/') ? `${TEACH_API_BASE}${url}` : url);
  if (Array.isArray(data?.items)) {
    data.items = data.items.map((item) => ({ ...item, url: toAbs(item.url) }));
  }
  return data;
}

