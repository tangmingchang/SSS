/**
 * 用户作品集 API（导出视频保存、列表、改标题、删除）
 */
import { getToken } from './authService';
import { API_BASE } from '../utils/api';

function headers() {
  const token = getToken();
  return {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
  };
}

export async function listWorks() {
  const res = await fetch(`${API_BASE}/api/user/works`, { headers: headers() });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.error || '获取作品列表失败');
  }
  const data = await res.json();
  return data.works || [];
}

export async function addWork({ title, video_url }) {
  const res = await fetch(`${API_BASE}/api/user/works`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ title: title || undefined, video_url }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.error || '保存到作品集失败');
  }
  return res.json();
}

export async function updateWork(id, { title }) {
  const res = await fetch(`${API_BASE}/api/user/works/${id}`, {
    method: 'PATCH',
    headers: headers(),
    body: JSON.stringify({ title }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.error || '修改标题失败');
  }
  return res.json();
}

export async function deleteWork(id) {
  const res = await fetch(`${API_BASE}/api/user/works/${id}`, {
    method: 'DELETE',
    headers: headers(),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.error || '删除失败');
  }
  return res.json();
}
