/**
 * 用户认证服务
 */
import { API_BASE } from '../utils/api';

const TOKEN_KEY = 'piying_auth_token';
const USER_KEY = 'piying_user';

/**
 * 保存token和用户信息到localStorage
 */
export const saveAuth = (token, user) => {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
};

/**
 * 获取保存的token
 */
export const getToken = () => {
  return localStorage.getItem(TOKEN_KEY);
};

/**
 * 获取保存的用户信息
 */
export const getUser = () => {
  const userStr = localStorage.getItem(USER_KEY);
  if (!userStr) return null;
  try {
    return JSON.parse(userStr);
  } catch {
    return null;
  }
};

/**
 * 清除认证信息
 */
export const clearAuth = () => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
};

/**
 * 用户注册
 */
export const register = async (username, email, password) => {
  try {
    const response = await fetch(`${API_BASE}/api/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, email, password }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || '注册失败');
    }

    // 保存token和用户信息
    if (data.token && data.user) {
      saveAuth(data.token, data.user);
    }

    return { success: true, data };
  } catch (error) {
    return { success: false, error: error.message };
  }
};

/**
 * 用户登录
 */
export const login = async (username, password) => {
  try {
    const response = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, password }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || '登录失败');
    }

    // 保存token和用户信息
    if (data.token && data.user) {
      saveAuth(data.token, data.user);
    }

    return { success: true, data };
  } catch (error) {
    return { success: false, error: error.message };
  }
};

/**
 * 验证token并获取用户信息
 */
export const verifyToken = async () => {
  const token = getToken();
  if (!token) {
    return { success: false, error: '未登录' };
  }

  try {
    const response = await fetch(`${API_BASE}/api/auth/verify`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ token }),
    });

    const data = await response.json();

    if (!response.ok) {
      clearAuth();
      throw new Error(data.error || 'Token验证失败');
    }

    // 更新用户信息
    if (data.user) {
      localStorage.setItem(USER_KEY, JSON.stringify(data.user));
    }

    return { success: true, data };
  } catch (error) {
    clearAuth();
    return { success: false, error: error.message };
  }
};

/**
 * 获取当前用户信息（需要token）
 */
export const getCurrentUser = async () => {
  const token = getToken();
  if (!token) {
    return { success: false, error: '未登录' };
  }

  try {
    const response = await fetch(`${API_BASE}/api/auth/me`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();

    if (!response.ok) {
      if (response.status === 401) {
        clearAuth();
      }
      throw new Error(data.error || '获取用户信息失败');
    }

    // 更新用户信息
    if (data.user) {
      localStorage.setItem(USER_KEY, JSON.stringify(data.user));
    }

    return { success: true, data };
  } catch (error) {
    return { success: false, error: error.message };
  }
};

/**
 * 用户登出
 */
export const logout = () => {
  clearAuth();
};

/**
 * 更新用户信息
 */
export const updateUserInfo = async (username, email) => {
  const token = getToken();
  if (!token) {
    return { success: false, error: '未登录' };
  }

  try {
    const response = await fetch(`${API_BASE}/api/auth/update`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, email }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || '更新失败');
    }

    // 更新本地存储的用户信息
    if (data.user) {
      localStorage.setItem(USER_KEY, JSON.stringify(data.user));
    }

    return { success: true, data };
  } catch (error) {
    return { success: false, error: error.message };
  }
};

/**
 * 上传头像
 */
export const uploadAvatar = async (file) => {
  const token = getToken();
  if (!token) {
    return { success: false, error: '未登录' };
  }

  try {
    const formData = new FormData();
    formData.append('avatar', file);

    const response = await fetch(`${API_BASE}/api/auth/upload_avatar`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || '上传失败');
    }

    // 更新本地存储的用户信息
    if (data.user) {
      localStorage.setItem(USER_KEY, JSON.stringify(data.user));
    }

    return { success: true, data };
  } catch (error) {
    return { success: false, error: error.message };
  }
};
