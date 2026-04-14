import React, { useState, useEffect, useCallback } from 'react';
import { apiSubmissionsList } from '../services/teachApi';
import { listWorks, updateWork, deleteWork } from '../services/userWorksApi';
import { resolveImageUrl } from '../utils/api';
import './PortfolioPage.css';

/** 作品集示例视频地址：Vite(3000) 用 public 路径，Flask(5000) 用后端 API，保证同源可播 */
function getDemoVideoSrc() {
  if (typeof window === 'undefined') return '/api/public/video/case';
  if (window.location.port === '3000') return '/视频/生成结果.mp4';
  return '/api/public/video/case';
}
const DEMO_WORK = { id: '__demo__', title: '皮影戏视频示例', video_url: getDemoVideoSrc(), created_at: null, isDemo: true };

/**
 * 作品集：我的视频作品（导出视频）+ 学习档案/作业提交
 * studentId 可选，不传则展示当前用户自己的
 */
export default function PortfolioPage({ studentId: propStudentId, currentUserId }) {
  const studentId = propStudentId || currentUserId;
  const isOwnPortfolio = !propStudentId || propStudentId === currentUserId;

  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(!!studentId);
  const [error, setError] = useState(null);

  const [works, setWorks] = useState([]);
  const [loadingWorks, setLoadingWorks] = useState(false);
  const [editingWorkId, setEditingWorkId] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const [demoVideoError, setDemoVideoError] = useState(false);
  const [demoVideoKey, setDemoVideoKey] = useState(0);

  const loadWorks = useCallback(() => {
    if (!isOwnPortfolio) return;
    setLoadingWorks(true);
    listWorks()
      .then((list) => setWorks(Array.isArray(list) ? list : []))
      .catch(() => setWorks([]))
      .finally(() => setLoadingWorks(false));
  }, [isOwnPortfolio]);

  useEffect(() => {
    if (!studentId) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    apiSubmissionsList(undefined, studentId)
      .then((list) => {
        if (!cancelled) setSubmissions(Array.isArray(list) ? list : []);
      })
      .catch((e) => { if (!cancelled) setError(e.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [studentId]);

  useEffect(() => {
    if (isOwnPortfolio) loadWorks();
  }, [isOwnPortfolio, loadWorks]);

  const handleStartEdit = (work) => {
    setEditingWorkId(work.id);
    setEditTitle(work.title || '');
  };

  const handleSaveTitle = async (workId) => {
    const title = editTitle.trim();
    if (!title) {
      setEditingWorkId(null);
      return;
    }
    try {
      await updateWork(workId, { title });
      setWorks((prev) => prev.map((w) => (w.id === workId ? { ...w, title } : w)));
    } catch (e) {
      console.error(e);
    }
    setEditingWorkId(null);
  };

  const handleDelete = async (workId) => {
    if (!window.confirm('确定删除该作品？')) return;
    try {
      await deleteWork(workId);
      setWorks((prev) => prev.filter((w) => w.id !== workId));
    } catch (e) {
      console.error(e);
    }
  };

  if (!studentId) return <div className="portfolio-page">请先登录或选择学生</div>;
  if (loading) return <div className="portfolio-page">加载中…</div>;
  if (error) return <div className="portfolio-page portfolio-error">错误：{error}</div>;

  return (
    <div className="portfolio-page">
      <h1 className="portfolio-heading">作品集</h1>

      {isOwnPortfolio && (
        <section className="portfolio-works-section">
          <h2 className="portfolio-subheading">我的视频作品</h2>
          {loadingWorks ? (
            <p className="portfolio-empty">加载中…</p>
          ) : (
            <ul className="portfolio-works-list">
              {/* 固定展示：平台示例视频 */}
              <li key={DEMO_WORK.id} className="portfolio-work-item portfolio-work-demo">
                <div className="portfolio-work-video">
                  {demoVideoError ? (
                    <div className="portfolio-demo-video-error">
                      <p>示例视频加载失败</p>
                      <p className="portfolio-demo-video-hint">请将 <strong>生成结果.mp4</strong> 放入 <code>frontend/public/视频/</code>。开发时用 localhost:3000 打开页面可直接从 public 加载。</p>
                      <button type="button" className="portfolio-btn-retry" onClick={() => { setDemoVideoError(false); setDemoVideoKey((k) => k + 1); }}>重试</button>
                    </div>
                  ) : (
                    <video
                      key={demoVideoKey}
                      src={getDemoVideoSrc()}
                      controls
                      preload="metadata"
                      playsInline
                      className="portfolio-demo-video"
                      onError={() => setDemoVideoError(true)}
                    />
                  )}
                </div>
                <div className="portfolio-work-info">
                  <div className="portfolio-work-title-row">
                    <span className="portfolio-work-title">{DEMO_WORK.title}</span>
                    <span className="portfolio-work-badge">示例</span>
                  </div>
                  <div className="portfolio-work-meta">平台示例，不可编辑</div>
                  <p className="portfolio-demo-video-codec-hint">若有声无画面，多为浏览器不兼容当前编码，可用 ffmpeg 转为 H.264 后替换（见本目录 README.txt）。</p>
                </div>
              </li>
              {works.map((w) => (
                <li key={w.id} className="portfolio-work-item">
                  <div className="portfolio-work-video">
                    <video
                      src={resolveImageUrl(w.video_url)}
                      controls
                      preload="metadata"
                      style={{ width: '100%', maxHeight: 200, objectFit: 'contain' }}
                    />
                  </div>
                  <div className="portfolio-work-info">
                    {editingWorkId === w.id ? (
                      <div className="portfolio-work-title-edit">
                        <input
                          type="text"
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          onBlur={() => handleSaveTitle(w.id)}
                          onKeyDown={(e) => e.key === 'Enter' && handleSaveTitle(w.id)}
                          autoFocus
                          className="portfolio-work-input"
                        />
                      </div>
                    ) : (
                      <div className="portfolio-work-title-row">
                        <span className="portfolio-work-title">{w.title || '未命名'}</span>
                        <button type="button" className="portfolio-btn-edit" onClick={() => handleStartEdit(w)}>修改标题</button>
                      </div>
                    )}
                    <div className="portfolio-work-meta">
                      {w.created_at && new Date(w.created_at).toLocaleString('zh-CN')}
                    </div>
                    <button type="button" className="portfolio-btn-delete" onClick={() => handleDelete(w.id)}>删除</button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      <section className="portfolio-submissions-section">
        <h2 className="portfolio-subheading">学习档案</h2>
        <ul className="portfolio-list">
          {submissions.map((s) => (
            <li key={s.id} className="portfolio-item">
              <div className="portfolio-title">{s.assignment?.title ?? '作业'}</div>
              <div className="portfolio-meta">
                {s.createdAt && new Date(s.createdAt).toLocaleString()}
              </div>
              {s.feedback && (
                <div className="portfolio-feedback">评语：{s.feedback}</div>
              )}
              {s.score != null && (
                <div className="portfolio-score">得分：{s.score}</div>
              )}
            </li>
          ))}
          {submissions.length === 0 && <li className="portfolio-empty">暂无提交记录</li>}
        </ul>
      </section>
    </div>
  );
}
