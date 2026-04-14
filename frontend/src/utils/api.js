/**
 * 后端 API 基址（开发环境默认 localhost:5000，生产可通过 VITE_API_BASE 配置）
 */
export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:5000';

/**
 * 解析图片 URL：以 /api/ 开头的后端接口路径需加上 API_BASE，否则前端无法跨端口加载
 * 前端静态资源如 /人物/xxx.png 保持不变
 */
export function resolveImageUrl(url) {
  if (!url) return url;
  if (url.startsWith('http')) return url;
  if (url.startsWith('/api/')) return `${API_BASE}${url}`;
  return url;
}

export default API_BASE;
