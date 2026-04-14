import React, { useEffect, useState } from 'react';
import {
  apiCourseGet,
  apiCourseMaterialResources,
} from '../services/teachApi';
import { getRecommendedLessonResources } from '../data/shadowPuppetSupplementResources';
import './LessonPage.css';

const DEFAULT_PROBE_CARDS = [
  { id: 'light', title: '灯光', questions: ['灯要几个？', '灯放哪里更清楚？', '举灯太累怎么解决？'] },
  { id: 'prop', title: '道具', questions: ['背景要不要做成可移动？', '用什么颜料不易刮花？', '关节如何更灵活？'] },
  { id: 'perform', title: '表演', questions: ['站着还是坐着？', '两手如何控三根杆？', '如何快速切换场景？'] },
  { id: 'music', title: '音乐', questions: ['配乐如何配合节奏？', '锣鼓点和丝竹如何搭配？'] },
  { id: 'promo', title: '宣传', questions: ['海报怎么做？', '如何记录与复盘？'] },
];

const RESOURCE_TYPE_LABELS = {
  video: '视频',
  article: '文章',
  image: '图片',
  audio: '音乐',
};

function normalizeLessonResourceItem(item, index) {
  if (!item) return null;
  if (typeof item === 'string') {
    return {
      id: `custom-link-${index}`,
      title: `拓展资源 ${index + 1}`,
      url: item,
      type: 'article',
      source: '课程资源',
      summary: '',
      usage: '',
    };
  }
  const url = item.url || item.link || item.href;
  if (!url) return null;
  return {
    id: item.id || `custom-link-${index}`,
    title: item.title || item.name || `拓展资源 ${index + 1}`,
    url,
    type: item.type || 'article',
    source: item.source || '课程资源',
    summary: item.summary || item.description || '',
    usage: item.usage || item.recommendedUse || '',
  };
}

function mapExtToType(ext = '') {
  const e = String(ext || '').toLowerCase();
  if (['.jpg', '.jpeg', '.png', '.gif', '.webp'].includes(e)) return 'image';
  if (['.mp4'].includes(e)) return 'video';
  if (['.mp3', '.wav'].includes(e)) return 'audio';
  return 'article';
}

function normalizeCourseMaterialResource(item) {
  if (!item || !item.url) return null;
  return {
    id: `course-material-${item.id}`,
    title: item.name || item.relativePath || '课程资源',
    type: mapExtToType(item.ext),
    source: '教学资源文件夹',
    summary: `${item.category || '其他'}${item.section ? ` / ${item.section}` : ''} · ${item.relativePath || ''}`,
    usage: '来自本地教学资源目录，可直接用于课程展示与备课。',
    url: item.url,
  };
}

export default function LessonPage({ lessonId, courseId, lesson: lessonProp, onOpenStage, onBack }) {
  const [lesson, setLesson] = useState(lessonProp || null);
  const [course, setCourse] = useState(null);
  const [loading, setLoading] = useState(!lessonProp && (!!lessonId || !!courseId));
  const [error, setError] = useState(null);

  const [courseMaterialResources, setCourseMaterialResources] = useState([]);

  useEffect(() => {
    if (lessonProp) {
      setLesson(lessonProp);
      return;
    }
    if (!courseId && !lessonId) return;

    let cancelled = false;
    (async () => {
      try {
        if (courseId) {
          const c = await apiCourseGet(courseId);
          if (!cancelled) {
            setCourse(c);
            const found = (c.lessons || []).find((l) => l.id === lessonId) || (c.lessons || [])[0];
            setLesson(found || null);
          }
        }
      } catch (e) {
        if (!cancelled) setError(e.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => { cancelled = true; };
  }, [courseId, lessonId, lessonProp]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await apiCourseMaterialResources(500);
        if (!cancelled) {
          const items = Array.isArray(data?.items) ? data.items : [];
          setCourseMaterialResources(items.map(normalizeCourseMaterialResource).filter(Boolean));
        }
      } catch (_) {
        if (!cancelled) setCourseMaterialResources([]);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (loading) return <div className="lesson-page">加载中...</div>;
  if (error) return <div className="lesson-page lesson-error">错误：{error}</div>;
  if (!lesson) return <div className="lesson-page">未找到课时</div>;

  const steps = lesson.content?.steps || [
    '导入：回顾上节，提出问题',
    '探究：分组尝试（灯光/道具/表演/音乐/宣传）',
    '编排：在舞台中拖拽角色与动作',
    '排练与演出',
    '复盘与记录',
  ];

  const probeCards = lesson.content?.probeCards ?? DEFAULT_PROBE_CARDS;

  const explicitResources = Array.isArray(lesson.content?.resources)
    ? lesson.content.resources.map(normalizeLessonResourceItem).filter(Boolean)
    : [];

  const recommendedResources = explicitResources.length > 0
    ? explicitResources
    : getRecommendedLessonResources(lesson.title);

  const mergedResourceList = [
    ...courseMaterialResources,
    ...recommendedResources,
  ];

  return (
    <div className="lesson-page">
      <div className="lesson-header">
        {onBack && (
          <button type="button" className="lesson-back" onClick={onBack} aria-label="返回上一页">
            ← 返回
          </button>
        )}
        <h1>{lesson.title}</h1>
        {course && <p className="lesson-course">{course.title}</p>}
      </div>

      <section className="lesson-steps">
        <h2>步骤</h2>
        <ol className="lesson-steps-list">
          {steps.map((s, i) => (
            <li key={i}>{typeof s === 'string' ? s : s.label || s.title}</li>
          ))}
        </ol>
      </section>

      <section className="lesson-probe">
        <h2>探究卡</h2>
        <div className="lesson-probe-cards">
          {probeCards.map((card) => (
            <div key={card.id} className="probe-card">
              <div className="probe-title">{card.title}</div>
              <ul>
                {(card.questions || []).map((q, i) => (
                  <li key={i}>{q}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      <section className="lesson-resources">
        <div className="lesson-resources-head">
          <h2>拓展资源</h2>
          <p>你 `教学资源` 文件夹与外部补充资源会统一显示在这里。</p>
        </div>
        <div className="lesson-resource-grid">
          {mergedResourceList.map((resource) => (
            <article key={resource.id} className="lesson-resource-card">
              <div className="lesson-resource-meta">
                <span className="lesson-resource-type">
                  {RESOURCE_TYPE_LABELS[resource.type] || '资源'}
                </span>
                <span className="lesson-resource-source">{resource.source}</span>
              </div>
              <h3 className="lesson-resource-title">{resource.title}</h3>
              {resource.summary && <p className="lesson-resource-summary">{resource.summary}</p>}
              {resource.usage && <p className="lesson-resource-usage">教学建议：{resource.usage}</p>}
              <a className="lesson-resource-link" href={resource.url} target="_blank" rel="noopener noreferrer">
                打开资源
              </a>
            </article>
          ))}
        </div>
      </section>

      <div className="lesson-actions">
        <button
          type="button"
          className="lesson-btn-stage"
          onClick={() => onOpenStage && onOpenStage({ lessonId: lesson.id, mode: 'practice' })}
        >
          进入舞台练习
        </button>
      </div>
    </div>
  );
}
