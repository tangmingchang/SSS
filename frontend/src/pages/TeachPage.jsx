import React, { useEffect, useMemo, useState } from 'react';
import {
  apiClassCreate,
  apiClassesList,
  apiCourseCreate,
  apiCourseMaterialResources,
  apiCoursesList,
  apiResourcesList,
  apiResourcesUpload,
} from '../services/teachApi';
import { API_BASE } from '../utils/api';
import './TeachPage.css';

const IMAGE_EXT_RE = /\.(png|jpe?g|gif|webp|bmp|svg)$/i;
const FALLBACK_COVER = '/首页.png';

const BILIBILI_COURSES = [
  { id: 'BV16b4y1H7Mq', title: '皮影的制作流程', url: 'https://www.bilibili.com/video/BV16b4y1H7Mq/' },
  { id: 'BV1GS4y1f723', title: '皮影戏的表演方式', url: 'https://www.bilibili.com/video/BV1GS4y1f723/' },
  { id: 'BV1YevDeLEMC', title: '非遗里的中国：皮影戏', url: 'https://www.bilibili.com/video/BV1YevDeLEMC/' },
  { id: 'BV154TfzxEwZ', title: '传承人纪录：北京皮影戏', url: 'https://www.bilibili.com/video/BV154TfzxEwZ/' },
  { id: 'BV11RExzjEdv', title: '科普短片：皮影戏起源', url: 'https://www.bilibili.com/video/BV11RExzjEdv/' },
  { id: 'BV1as411K7yx', title: '皮影戏知识与赏析', url: 'https://www.bilibili.com/video/BV1as411K7yx/' },
];

const ONLINE_SUPPLEMENT_RESOURCES = [
  {
    id: 'ihchina-data',
    title: '国家级非遗代表性项目：皮影戏（数据与项目概览）',
    source: '中国非物质文化遗产网',
    url: 'https://www.ihchina.cn/art/detail/id/18619.html',
  },
  {
    id: 'ihchina-hunan',
    title: '皮影戏（湖南皮影戏）项目介绍',
    source: '中国非物质文化遗产网',
    url: 'https://www.ihchina.cn/art/detail/id/13415.html',
  },
  {
    id: 'ihchina-taishan',
    title: '皮影戏（泰山皮影戏）项目介绍',
    source: '中国非物质文化遗产网',
    url: 'https://www.ihchina.cn/art/detail/id/13411.html',
  },
  {
    id: 'cdstm-activity',
    title: '“银灯照影 舞动光阴”非遗+科技线上体验活动',
    source: '中国数字科技馆',
    url: 'https://www.cdstm.cn/activity/dtcj/202201/t20220120_1063530.html',
  },
  {
    id: 'liaoning-training',
    title: '2024年皮影戏传承人研修培训班开班',
    source: '辽宁省人民政府',
    url: 'https://www.ln.gov.cn/web/ywdt/tjdt/2024051409425794423/index.shtml',
  },
  {
    id: 'ihchina-hand',
    title: '影偶之本：影偶操作与教学体系研究',
    source: '中国非物质文化遗产网',
    url: 'https://www.ihchina.cn/art/detail/id/28032.html',
  },
];

function toAbsUrl(url) {
  if (!url) return '';
  return String(url).startsWith('http') ? String(url) : `${API_BASE}${url}`;
}

function isImageFile(name = '') {
  return IMAGE_EXT_RE.test(String(name || ''));
}

function createTreeNode(name, path) {
  return { name, path, children: [], files: [] };
}

function countNodeItems(node) {
  const childCount = (node.children || []).reduce((sum, child) => sum + countNodeItems(child), 0);
  return (node.files?.length || 0) + childCount;
}

function buildCourseTree(items) {
  const root = createTreeNode('教学资源', '');
  for (const item of items || []) {
    const rel = String(item.relativePath || item.name || '').replace(/\\/g, '/').replace(/^\/+/, '');
    if (!rel) continue;
    const parts = rel.split('/').filter(Boolean);
    if (!parts.length) continue;

    let current = root;
    let currentPath = '';
    for (let i = 0; i < parts.length - 1; i += 1) {
      const seg = parts[i];
      currentPath = currentPath ? `${currentPath}/${seg}` : seg;
      let next = current.children.find((child) => child.name === seg);
      if (!next) {
        next = createTreeNode(seg, currentPath);
        current.children.push(next);
      }
      current = next;
    }

    const fileName = parts[parts.length - 1];
    current.files.push({
      ...item,
      name: item.name || fileName,
      relativePath: rel,
    });
  }

  const sortNode = (node) => {
    node.children.sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'));
    node.files.sort((a, b) => String(a.name).localeCompare(String(b.name), 'zh-CN'));
    node.children.forEach(sortNode);
  };
  sortNode(root);
  return root;
}

function findFirstImageUrlInNode(node) {
  if (!node) return '';
  const firstFile = (node.files || []).find((f) => isImageFile(f.name || f.relativePath));
  if (firstFile) return toAbsUrl(firstFile.url);
  for (const child of node.children || []) {
    const found = findFirstImageUrlInNode(child);
    if (found) return found;
  }
  return '';
}

function decodeTextBuffer(buffer) {
  try {
    const utf8 = new TextDecoder('utf-8', { fatal: false }).decode(buffer);
    if (!utf8.includes('\ufffd')) return utf8;
  } catch (_) {}
  try {
    return new TextDecoder('gb18030', { fatal: false }).decode(buffer);
  } catch (_) {
    return '';
  }
}

function TxtContentItem({ file }) {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const loadText = async () => {
      setLoading(true);
      setError(false);
      try {
        const res = await fetch(toAbsUrl(file.url));
        if (!res.ok) throw new Error('load-failed');
        const buffer = await res.arrayBuffer();
        const content = decodeTextBuffer(buffer).trim();
        if (!cancelled) setText(content || '(空文件)');
      } catch (_) {
        if (!cancelled) {
          setError(true);
          setText('');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    loadText();
    return () => { cancelled = true; };
  }, [file.url]);

  return (
    <li className="teach-text-item teach-text-block">
      <div className="teach-text-title">{file.name}</div>
      {loading && <div className="teach-text-body">加载中...</div>}
      {!loading && error && <div className="teach-text-body">读取失败</div>}
      {!loading && !error && <pre className="teach-text-body">{text}</pre>}
    </li>
  );
}

function PlainFileList({ files }) {
  if (!Array.isArray(files) || files.length === 0) return null;
  const imageFiles = files.filter((f) => isImageFile(f.name || f.relativePath));
  const txtFiles = files.filter((f) => /\.txt$/i.test(String(f.name || f.relativePath || '')));
  const otherFiles = files.filter((f) => !isImageFile(f.name || f.relativePath) && !/\.txt$/i.test(String(f.name || f.relativePath || '')));

  return (
    <div className="teach-file-block">
      {imageFiles.length > 0 && (
        <div className="teach-file-image-grid">
          {imageFiles.map((file, idx) => (
            <div key={`${file.relativePath || file.name}-${idx}`} className="teach-file-image-item">
              <img src={toAbsUrl(file.url)} alt={file.name} loading="lazy" />
              <span>{file.name}</span>
            </div>
          ))}
        </div>
      )}
      {txtFiles.length > 0 && (
        <ul className="teach-text-list">
          {txtFiles.map((file, idx) => (
            <TxtContentItem key={`${file.relativePath || file.name}-${idx}`} file={file} />
          ))}
        </ul>
      )}
      {otherFiles.length > 0 && (
        <ul className="teach-text-list">
          {otherFiles.map((file, idx) => (
            <li key={`${file.relativePath || file.name}-${idx}`} className="teach-text-item">{file.name}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function FolderBranch({ node, expandedNodes, onToggleNode, depth = 0 }) {
  const key = `node:${node.path || '__root__'}`;
  const open = expandedNodes.has(key);
  const total = countNodeItems(node);
  const hasContent = (node.files?.length || 0) > 0 || (node.children?.length || 0) > 0;

  return (
    <div className="teach-branch" style={{ '--branch-depth': depth }}>
      <button type="button" className="teach-branch-head" onClick={() => hasContent && onToggleNode(key)}>
        <span className="teach-branch-arrow">{open ? '▼' : '▶'}</span>
        <span className="teach-branch-name">{node.name}</span>
        <span className="teach-branch-count">({total})</span>
      </button>
      {open && hasContent && (
        <div className="teach-branch-body">
          <PlainFileList files={node.files} />
          {node.children.map((child) => (
            <FolderBranch
              key={child.path}
              node={child}
              expandedNodes={expandedNodes}
              onToggleNode={onToggleNode}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function FolderCard({ title, node, rootFiles, expandedCards, onToggleCard, expandedNodes, onToggleNode }) {
  const cardKey = `card:${node ? node.path : '__root_files__'}`;
  const open = expandedCards.has(cardKey);
  const count = node ? countNodeItems(node) : (rootFiles?.length || 0);
  const rootImage = Array.isArray(rootFiles)
    ? rootFiles.find((file) => isImageFile(file.name || file.relativePath))
    : null;
  const cover = node ? (findFirstImageUrlInNode(node) || FALLBACK_COVER) : (toAbsUrl(rootImage?.url) || FALLBACK_COVER);

  return (
    <article className="teach-folder-card">
      <button type="button" className="teach-folder-card-preview" onClick={() => onToggleCard(cardKey)}>
        <img src={cover} alt={title} loading="lazy" onError={(e) => { e.currentTarget.src = FALLBACK_COVER; }} />
        <div className="teach-folder-card-caption">
          <span>{title}</span>
          <span>{open ? `收起（${count}）` : `展开（${count}）`}</span>
        </div>
      </button>
      {open && (
        <div className="teach-folder-card-detail">
          {node ? (
            <>
              <PlainFileList files={node.files} />
              {node.children.map((child) => (
                <FolderBranch
                  key={child.path}
                  node={child}
                  expandedNodes={expandedNodes}
                  onToggleNode={onToggleNode}
                />
              ))}
            </>
          ) : (
            <PlainFileList files={rootFiles} />
          )}
        </div>
      )}
    </article>
  );
}

function BiliCard({ item }) {
  const [cover, setCover] = useState(item.cover || FALLBACK_COVER);
  return (
    <a className="teach-bili-card" href={item.url} target="_blank" rel="noopener noreferrer">
      <img src={cover} alt={item.title} loading="lazy" onError={() => setCover(FALLBACK_COVER)} />
      <div className="teach-bili-title">{item.title}</div>
    </a>
  );
}

function OnlineResourceCard({ item }) {
  return (
    <a className="teach-bili-card" href={item.url} target="_blank" rel="noopener noreferrer">
      <img src={FALLBACK_COVER} alt={item.title} loading="lazy" />
      <div className="teach-bili-title">{item.title}</div>
      <div className="teach-bili-source">{item.source}</div>
    </a>
  );
}

export default function TeachPage({ currentUser, onOpenClass }) {
  const isTeacher = currentUser?.account_type === 'teacher';

  const [courses, setCourses] = useState({ taught: [], enrolled: [] });
  const [classesByCourse, setClassesByCourse] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [creatingCourse, setCreatingCourse] = useState(false);
  const [newCourseTitle, setNewCourseTitle] = useState('');
  const [newClassCourseId, setNewClassCourseId] = useState('');
  const [newClassName, setNewClassName] = useState('');

  const [resourcesLoading, setResourcesLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [resources, setResources] = useState({
    uploadFiles: [],
    courseItems: [],
  });
  const [biliCourses, setBiliCourses] = useState(
    BILIBILI_COURSES.map((item) => ({ ...item, cover: '' })),
  );

  const [expandedCards, setExpandedCards] = useState(() => new Set());
  const [expandedNodes, setExpandedNodes] = useState(() => new Set());

  const courseTree = useMemo(() => buildCourseTree(resources.courseItems), [resources.courseItems]);

  const toggleCard = (key) => {
    setExpandedCards((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const toggleNode = (key) => {
    setExpandedNodes((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const loadCourses = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiCoursesList();
      setCourses(data);
    } catch (e) {
      setCourses({ taught: [], enrolled: [] });
      setError(e.message || '请求失败');
    } finally {
      setLoading(false);
    }
  };

  const loadResources = async () => {
    setResourcesLoading(true);
    try {
      const [teachResult, courseResult] = await Promise.allSettled([
        apiResourcesList(),
        apiCourseMaterialResources(2000),
      ]);

      const teachData = teachResult.status === 'fulfilled' ? teachResult.value : { uploadFiles: [] };
      const courseItems = courseResult.status === 'fulfilled' ? (courseResult.value?.items || []) : [];

      setResources({
        uploadFiles: Array.isArray(teachData.uploadFiles) ? teachData.uploadFiles : [],
        courseItems: Array.isArray(courseItems) ? courseItems : [],
      });
    } catch (_) {
      setResources({
        uploadFiles: [],
        courseItems: [],
      });
    } finally {
      setResourcesLoading(false);
    }
  };

  useEffect(() => {
    loadCourses();
    loadResources();
  }, []);

  // 直接使用静态列表，不请求 B 站 API（浏览器直连会 CORS 被拒，需后端代理才能拉取封面等信息）
  useEffect(() => {
    setBiliCourses(BILIBILI_COURSES.map((item) => ({ ...item, cover: '' })));
  }, []);

  const handleCreateCourse = async (e) => {
    e.preventDefault();
    if (!newCourseTitle.trim()) return;
    setCreatingCourse(true);
    try {
      await apiCourseCreate({ title: newCourseTitle.trim() });
      setNewCourseTitle('');
      loadCourses();
    } catch (e) {
      setError(e.message);
    } finally {
      setCreatingCourse(false);
    }
  };

  const handleCreateClass = async (e) => {
    e.preventDefault();
    if (!newClassCourseId || !newClassName.trim()) return;
    try {
      const c = await apiClassCreate({ courseId: newClassCourseId, name: newClassName.trim() });
      alert(`班级已创建，邀请码：${c.joinCode}`);
      setNewClassName('');
      loadCourses();
    } catch (e) {
      setError(e.message);
    }
  };

  if (loading) return <div className="teach-page">加载中...</div>;

  const isNetworkError = error && (error.includes('Failed to fetch') || error.includes('CONNECTION_REFUSED') || error.includes('NetworkError'));
  const isUnauth = error && (error.includes('未登录') || error.includes('401'));
  if (error && !isNetworkError && !isUnauth) {
    return <div className="teach-page teach-error">错误：{error}</div>;
  }

  const hasRootFiles = courseTree.files.length > 0;
  const hasFolderCards = courseTree.children.length > 0;
  const hasUploads = resources.uploadFiles.length > 0;

  return (
    <div className="teach-page">
      <h1 className="teach-heading">{isTeacher ? '教学中心' : '我的课程'}</h1>

      {isUnauth && (
        <div className="teach-hint">
          请先登录后再查看课程与班级。测试账号：教师 <code>teacher_test</code>，学生 <code>student_test</code>。
        </div>
      )}
      {isNetworkError && (
        <div className="teach-hint">
          无法连接服务端，请先启动后端（`cd backend && python app.py`）。
        </div>
      )}

      {isTeacher && (
        <section className="teach-section">
          <h2>我创建的课程</h2>
          <form onSubmit={handleCreateCourse} className="teach-form">
            <input
              type="text"
              value={newCourseTitle}
              onChange={(e) => setNewCourseTitle(e.target.value)}
              placeholder="新课程名称"
              disabled={creatingCourse}
            />
            <button type="submit" disabled={creatingCourse}>创建课程</button>
          </form>
          <ul className="teach-list">
            {(courses.taught || []).map((c) => (
              <li key={c.id} className="teach-item teach-item-course">
                <span>{c.title}</span>
                <button
                  type="button"
                  onClick={async () => {
                    if (!classesByCourse[c.id]) {
                      try {
                        const list = await apiClassesList(c.id);
                        setClassesByCourse((prev) => ({ ...prev, [c.id]: list }));
                      } catch (_) {}
                    } else {
                      setClassesByCourse((prev) => ({ ...prev, [c.id]: null }));
                    }
                  }}
                >
                  {(classesByCourse[c.id] ? '收起' : '') + '班级'}
                </button>
                {Array.isArray(classesByCourse[c.id]) && (
                  <ul className="teach-sublist">
                    {classesByCourse[c.id].map((cls) => (
                      <li key={cls.id}>
                        <span>{cls.name}</span>
                        <span className="teach-join">邀请码 {cls.joinCode}</span>
                        <button type="button" onClick={() => onOpenClass && onOpenClass(cls.id)}>进入</button>
                      </li>
                    ))}
                    {classesByCourse[c.id].length === 0 && <li className="teach-empty">暂无班级</li>}
                  </ul>
                )}
              </li>
            ))}
            {(courses.taught || []).length === 0 && <li className="teach-empty">暂无课程，请先创建</li>}
          </ul>
        </section>
      )}

      {isTeacher && (
        <section className="teach-section">
          <h2>创建班级</h2>
          <form onSubmit={handleCreateClass} className="teach-form">
            <select value={newClassCourseId} onChange={(e) => setNewClassCourseId(e.target.value)}>
              <option value="">选择课程</option>
              {(courses.taught || []).map((c) => (
                <option key={c.id} value={c.id}>{c.title}</option>
              ))}
            </select>
            <input
              type="text"
              value={newClassName}
              onChange={(e) => setNewClassName(e.target.value)}
              placeholder="班级名称"
            />
            <button type="submit">创建班级</button>
          </form>
        </section>
      )}

      <section className="teach-section">
        <h2>我加入的班级</h2>
        <ul className="teach-list">
          {(courses.enrolled || []).map((item) => {
            const cls = item.class;
            const course = item.course;
            if (!cls) return null;
            return (
              <li key={cls.id} className="teach-item">
                <span>{cls.name}（{course?.title || ''}）</span>
                <button type="button" onClick={() => onOpenClass && onOpenClass(cls.id)}>进入</button>
              </li>
            );
          })}
          {(courses.enrolled || []).length === 0 && <li className="teach-empty">暂无</li>}
        </ul>
      </section>

      <section className="teach-section teach-resources">
        <h2>教学资源目录</h2>
        {!resourcesLoading && (hasRootFiles || hasFolderCards) ? (
          <div className="teach-three-grid">
            {hasRootFiles && (
              <FolderCard
                title="根目录文件"
                rootFiles={courseTree.files}
                expandedCards={expandedCards}
                onToggleCard={toggleCard}
                expandedNodes={expandedNodes}
                onToggleNode={toggleNode}
              />
            )}
            {courseTree.children.map((node) => (
              <FolderCard
                key={node.path}
                title={node.name}
                node={node}
                expandedCards={expandedCards}
                onToggleCard={toggleCard}
                expandedNodes={expandedNodes}
                onToggleNode={toggleNode}
              />
            ))}
          </div>
        ) : (
          <p className="teach-empty">暂无教学资源目录内容</p>
        )}
      </section>

      <section className="teach-section">
        <h2>教师上传</h2>
        {hasUploads ? (
          <ul className="teach-text-list">
            {resources.uploadFiles.map((f, idx) => (
              <li key={`${f.name}-${idx}`} className="teach-text-item">{f.name}</li>
            ))}
          </ul>
        ) : (
          <p className="teach-empty">暂无上传文件</p>
        )}
        {isTeacher && (
          <form
            className="teach-upload-form"
            onSubmit={async (e) => {
              e.preventDefault();
              const input = e.target.querySelector('input[type="file"]');
              if (!input?.files?.length) return;
              setUploading(true);
              try {
                await apiResourcesUpload(input.files[0]);
                await loadResources();
                input.value = '';
              } catch (err) {
                alert(err.message || '上传失败');
              } finally {
                setUploading(false);
              }
            }}
          >
            <input type="file" name="file" />
            <button type="submit" disabled={uploading}>{uploading ? '上传中...' : '上传资源'}</button>
          </form>
        )}
      </section>

      <section className="teach-section teach-resources">
        <h2>B站相关课程</h2>
        <div className="teach-three-grid teach-bili-grid">
          {biliCourses.map((item) => (
            <BiliCard key={item.id} item={item} />
          ))}
        </div>
      </section>

      <section className="teach-section teach-resources">
        <h2>网上补充资源</h2>
        <div className="teach-three-grid teach-bili-grid">
          {ONLINE_SUPPLEMENT_RESOURCES.map((item) => (
            <OnlineResourceCard key={item.id} item={item} />
          ))}
        </div>
      </section>
    </div>
  );
}
