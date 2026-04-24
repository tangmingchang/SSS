import { useState, useEffect } from 'react';
import './App.css';
import AuthModal from './components/shared/AuthModal';
import PrivacyModal from './components/shared/PrivacyModal';
import { getToken, getUser, verifyToken, logout as logoutAPI } from './services/authService';
import API_BASE from './utils/api';

import HomePage from './pages/HomePage';
import StationBasedWorkbench from './pages/StationBasedWorkbench';
import DocsPage from './pages/DocsPage';
import PublicLibraryPage from './pages/PublicLibraryPage';
import PersonalLibraryPage from './pages/PersonalLibraryPage';
import AiGeneratorPage from './pages/AiGeneratorPage';
import UserProfilePage from './pages/UserProfilePage';
import TeachPage from './pages/TeachPage';
import ClassPage from './pages/ClassPage';
import LessonPage from './pages/LessonPage';
import StagePage from './pages/StagePage';
import PortfolioPage from './pages/PortfolioPage';

const PAGES = {
  HOME: 'home',
  WORKBENCH: 'workbench',
  DOCS: 'docs',
  PUBLIC: 'public',
  PERSONAL: 'personal',
  AI: 'ai',
  USER: 'user',
  TEACH: 'teach',
  CLASS: 'class',
  LESSON: 'lesson',
  STAGE: 'stage',
  PORTFOLIO: 'portfolio',
};

const trainedPuppetUrl = (encodedFileName) =>
  `${API_BASE}/api/resources/trained-puppets/file/${encodedFileName}`;

const extractTrainedStem = (value) => {
  if (!value || typeof value !== 'string') return '';
  let input = value;
  const apiSeg = '/api/resources/trained-puppets/file/';
  const idx = value.indexOf(apiSeg);
  if (idx >= 0) {
    input = value.slice(idx + apiSeg.length);
  } else {
    const parts = value.split('/');
    input = parts[parts.length - 1] || value;
  }
  const decoded = decodeURIComponent(input).split('?')[0];
  return decoded.replace(/\.[^/.]+$/, '').trim().toLowerCase();
};

const DECOMPOSED_CHARACTER_PARTS_BY_ID = {
  guanyin: { folder: '人物-2', head: '1.png', body: '2.png', leftArm: '3.png', rightArm: '4.png', leftLeg: '图层 5.png', rightLeg: '图层 6.png' },
  'longpao-wangmao': { folder: '人物-3', head: '1.png', body: '2.png', leftArm: '3.png', rightArm: '4.png', leftLeg: '图层 4.png', rightLeg: '图层 5.png' },
  'lanpi-yaodan': { folder: '人物-4', head: '1.png', body: '2.png', leftArm: '3.png', rightArm: '4.png', leftLeg: '图层 5.png', rightLeg: '图层 6.png' },
  'fuhua-yahuan': { folder: '人物-6', head: '图层 8.png', body: '图层 2.png', leftArm: '图层 3.png', rightArm: '图层 4.png', leftLeg: '图层 5.png', rightLeg: '图层 6.png' },
  'xuehua-daogu': { folder: '人物-7', head: '图层 8.png', body: '图层 2.png', leftArm: '图层 4.png', rightArm: '图层 5.png', leftLeg: '图层 6.png', rightLeg: '图层 7.png' },
  'heilongpao-chou': { folder: '人物-8', head: '图层 8.png', body: '图层 2.png', leftArm: '图层 3.png', rightArm: '图层 4.png', leftLeg: '图层 5.png', rightLeg: '图层 6.png' },
  'fuhua-fengmao': { folder: '人物-9', head: '1.png', body: '2.png', leftArm: '3.png', rightArm: '4.png', leftLeg: '图层 7.png', rightLeg: '图层 8.png' },
  'yang-guifei': { folder: '人物-10', head: '1.png', body: '2.png', leftArm: '3.png', rightArm: '4.png', leftLeg: '图层 4.png', rightLeg: '图层 5.png' },
  'fanwen-jikui': { folder: '人物-11', head: '1.png', body: '2.png', leftArm: '3.png', rightArm: '4.png', leftLeg: '图层 5.png', rightLeg: '图层 6.png' },
};

function applyDecomposedCharacterImages(resources) {
  if (!resources?.characters) return resources;
  const withParts = resources.characters.map((char) => {
    const cfg = DECOMPOSED_CHARACTER_PARTS_BY_ID[char.id];
    if (!cfg?.folder) return char;
    const base = `/教学资源/人物分解/${cfg.folder}`;
    const images = { ...(char.images || {}) };
    images.head = `${base}/${cfg.head}`;
    images.body = `${base}/${cfg.body}`;
    images.leftArm = `${base}/${cfg.leftArm}`;
    images.rightArm = `${base}/${cfg.rightArm}`;
    images.leftLeg = `${base}/${cfg.leftLeg}`;
    images.rightLeg = `${base}/${cfg.rightLeg}`;
    images.full = `${base}/main.png`;
    return { ...char, images, thumbnail: char.thumbnail || images.full };
  });
  return { ...resources, characters: withParts };
}

const initialPublicResources = applyDecomposedCharacterImages({
  characters: [
    { id: 'guanyin', name: '观音菩萨', type: 'character', style: '文戏', tags: ['经典', '菩萨'], thumbnail: '/人物/观音菩萨.png', images: { full: '/人物/观音菩萨.png' } },
    { id: 'longpao-wangmao', name: '龙袍王帽生', type: 'character', style: '生角', tags: ['经典', '皇帝'], thumbnail: '/人物/龙袍王帽生.png', images: { full: '/人物/龙袍王帽生.png' } },
    { id: 'yang-guifei', name: '杨贵妃', type: 'character', style: '旦角', tags: ['经典', '贵妃'], thumbnail: '/人物/杨贵妃.png', images: { full: '/人物/杨贵妃.png' } },
    { id: 'lanpi-yaodan', name: '蓝皮尧旦', type: 'character', style: '旦角', tags: ['传统', '旦角'], thumbnail: '/人物/蓝皮尧旦.png', images: { full: '/人物/蓝皮尧旦.png' } },
    { id: 'xuehua-daogu', name: '雪花纹道姑旦', type: 'character', style: '旦角', tags: ['传统', '道姑'], thumbnail: '/人物/雪花纹道姑旦.png', images: { full: '/人物/雪花纹道姑旦.png' } },
    { id: 'fuhua-yahuan', name: '富花纹丫鬟旦', type: 'character', style: '旦角', tags: ['传统', '丫鬟'], thumbnail: '/人物/富花纹丫鬟旦.png', images: { full: '/人物/富花纹丫鬟旦.png' } },
    { id: 'fanwen-jikui', name: '蕃纹鸡盔净', type: 'character', style: '丑角', tags: ['传统', '武将'], thumbnail: '/人物/蕃纹鸡盔净.png', images: { full: '/人物/蕃纹鸡盔净.png' } },
    { id: 'fuhua-fengmao', name: '富花纹风帽老生', type: 'character', style: '老生', tags: ['传统', '老生'], thumbnail: '/人物/富花纹风帽老生.png', images: { full: '/人物/富花纹风帽老生.png' } },
    { id: 'heilongpao-chou', name: '黑龙袍相貌丑', type: 'character', style: '武角', tags: ['传统', '武角'], thumbnail: '/人物/黑龙袍相貌丑.png', images: { full: '/人物/黑龙袍相貌丑.png' } },
    { id: 'trained-2', name: 'Trained Puppet 2', type: 'character', style: 'mocap', tags: ['trained', 'recommended', 'unity-assets'], thumbnail: trainedPuppetUrl('2%E5%8F%B7.png'), images: { full: trainedPuppetUrl('2%E5%8F%B7.png') }, mocapPreferred: true },
    { id: 'trained-5', name: 'Trained Puppet 5', type: 'character', style: 'mocap', tags: ['trained', 'recommended', 'unity-assets'], thumbnail: trainedPuppetUrl('5%E5%8F%B7.png'), images: { full: trainedPuppetUrl('5%E5%8F%B7.png') }, mocapPreferred: true },
    { id: 'trained-7', name: 'Trained Puppet 7', type: 'character', style: 'mocap', tags: ['trained', 'recommended', 'unity-assets'], thumbnail: trainedPuppetUrl('7%E5%8F%B7.png'), images: { full: trainedPuppetUrl('7%E5%8F%B7.png') }, mocapPreferred: true },
    { id: 'trained-8', name: 'Trained Puppet 8', type: 'character', style: 'mocap', tags: ['trained', 'recommended', 'unity-assets'], thumbnail: trainedPuppetUrl('8%E5%8F%B7.png'), images: { full: trainedPuppetUrl('8%E5%8F%B7.png') }, mocapPreferred: true },
  ],
  scenes: [
    { id: 'scene-1', name: '舞台', type: 'scene', url: '/场景/场景1-舞台.png', tags: ['经典', '戏台'] },
    { id: 'scene-2', name: '教室', type: 'scene', url: '/场景/场景2-教室.png', tags: ['现代', '室内'] },
    { id: 'scene-3', name: '卧房', type: 'scene', url: '/场景/场景3-卧房.png', tags: ['古典', '室内'] },
    { id: 'scene-4', name: '海边', type: 'scene', url: '/场景/场景4-海边.png', tags: ['自然', '风景'] },
    { id: 'scene-5', name: '夕阳', type: 'scene', url: '/场景/场景5-夕阳.png', tags: ['自然', '风景'] },
    { id: 'scene-6', name: '沙漠', type: 'scene', url: '/场景/场景6-沙漠.png', tags: ['自然', '风景'] },
    { id: 'scene-7', name: '树林', type: 'scene', url: '/场景/场景7-树林.png', tags: ['自然', '风景'] },
    { id: 'scene-8', name: '街道', type: 'scene', url: '/场景/场景8-街道.png', tags: ['现代', '城市'] },
    { id: 'scene-9', name: '竹林', type: 'scene', url: '/场景/场景9-竹林.png', tags: ['古典', '自然'] },
    { id: 'scene-10', name: '沙漠2', type: 'scene', url: '/场景/场景10-沙漠.png', tags: ['自然', '风景'] },
    { id: 'scene-11', name: '桥上', type: 'scene', url: '/场景/场景11-桥上.png', tags: ['古典', '建筑'] },
    { id: 'scene-12', name: '墙外', type: 'scene', url: '/场景/场景12-墙外.png', tags: ['古典', '建筑'] },
    { id: 'scene-curtain', name: '幕布', type: 'scene', url: '/场景/幕布.png', tags: ['经典', '幕布'] },
  ],
  motions: [
    { id: 'pub-motion-1', name: '持枪三连刺', type: 'motion', tags: ['打斗', '武戏'] },
    { id: 'pub-motion-2', name: '惊惶后退', type: 'motion', tags: ['文戏', '反派'] },
    { id: 'pub-motion-3', name: '出场亮相', type: 'motion', tags: ['文戏', '开场'] },
    { id: 'pub-motion-4', name: '展袖起舞', type: 'motion', tags: ['舞蹈', '文戏'] },
    { id: 'pub-motion-5', name: '望月思君', type: 'motion', tags: ['文戏', '情感'] },
    { id: 'pub-motion-6', name: '醉舞旋转', type: 'motion', tags: ['舞蹈', '高难'] },
    { id: 'pub-motion-7', name: '收势行礼', type: 'motion', tags: ['文戏', '结尾'] },
    { id: 'pub-motion-8', name: '起身站定', type: 'motion', tags: ['基础', '开场'] },
    { id: 'pub-motion-9', name: '行走接近', type: 'motion', tags: ['基础', '移动'] },
    { id: 'pub-motion-10', name: '持手指意', type: 'motion', tags: ['基础', '互动'] },
    { id: 'pub-motion-11', name: '拱手致意', type: 'motion', tags: ['基础', '仪式'] },
    { id: 'pub-motion-12', name: '跃步踢空', type: 'motion', tags: ['武戏', '动作'] },
  ],
  music: [
    { id: 'pub-music-1', name: '平台示例配乐（本地）', type: 'music', duration: '03:07', url: '/配乐.mp3', tags: ['本地可用', '示例'] },
    { id: 'pub-music-2', name: '平台示例配乐（片段）', type: 'music', duration: '00:45', url: '/配乐.mp3#t=20', tags: ['本地可用', '片段'] },
  ],
});

const STORAGE_KEY_PERSONAL = 'piying_personal_resources';
const emptyPersonal = () => ({ characters: [], scenes: [], motions: [], music: [] });

function loadPersonalFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY_PERSONAL);
    if (!raw) return emptyPersonal();
    const parsed = JSON.parse(raw);
    return {
      characters: Array.isArray(parsed.characters) ? parsed.characters : [],
      scenes: Array.isArray(parsed.scenes) ? parsed.scenes : [],
      motions: Array.isArray(parsed.motions) ? parsed.motions : [],
      music: Array.isArray(parsed.music) ? parsed.music : [],
    };
  } catch (_) {
    return emptyPersonal();
  }
}

function App() {
  const [activePage, setActivePage] = useState(PAGES.HOME);
  const [pagePayload, setPagePayload] = useState(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState('login');
  const [showPrivacyModal, setShowPrivacyModal] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);

  const [publicResources, setPublicResources] = useState(initialPublicResources);
  const [personalResources, setPersonalResources] = useState(loadPersonalFromStorage);

  useEffect(() => {
    let canceled = false;
    const loadAssetsPuppets = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/resources/trained-puppets`);
        if (!res.ok) return;
        const data = await res.json().catch(() => null);
        const items = Array.isArray(data?.items) ? data.items : [];
        if (!items.length || canceled) return;

        setPublicResources((prev) => {
          const existed = new Set((prev.characters || []).map((c) => c.id));
          const existingStems = new Set(
            (prev.characters || [])
              .map((c) => extractTrainedStem(c.images?.full || c.thumbnail || c.image_url || c.id))
              .filter(Boolean)
          );
          const merged = [...(prev.characters || [])];
          items.forEach((item) => {
            const encoded = encodeURIComponent(item.fileName || '');
            const id = `trained-${item.id || encoded}`;
            const url = item.url || trainedPuppetUrl(encoded);
            const stem = extractTrainedStem(item.fileName || item.id || url);
            if (existed.has(id) || (stem && existingStems.has(stem))) return;
            merged.push({
              id,
              name: item.name || item.id || 'Assets 皮影',
              type: 'character',
              style: 'mocap',
              tags: ['trained', 'unity-assets'],
              thumbnail: url,
              images: { full: url },
              mocapPreferred: true,
            });
            existed.add(id);
            if (stem) existingStems.add(stem);
          });
          return { ...prev, characters: merged };
        });
      } catch (_) {
        // 忽略联网失败，保持本地默认角色可用
      }
    };
    loadAssetsPuppets();
    return () => {
      canceled = true;
    };
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY_PERSONAL, JSON.stringify(personalResources));
    } catch (e) {
      console.warn('[涓汉璧勬簮搴揮 鍐欏叆 localStorage 澶辫触', e);
    }
  }, [personalResources]);

  const resolveBlobUrlsInItem = async (item) => {
    if (!item || typeof item !== 'object') return item;
    const out = { ...item };
    for (const key of ['url', 'image_url', 'thumbnail']) {
      const v = out[key];
      if (typeof v === 'string' && v.startsWith('blob:')) {
        try {
          const res = await fetch(v);
          const blob = await res.blob();
          const dataUrl = await new Promise((resolve, reject) => {
            const r = new FileReader();
            r.onload = () => resolve(r.result);
            r.onerror = reject;
            r.readAsDataURL(blob);
          });
          out[key] = dataUrl;
        } catch (_) {}
      }
    }
    if (out.images && typeof out.images === 'object' && out.images.full && typeof out.images.full === 'string' && out.images.full.startsWith('blob:')) {
      try {
        const res = await fetch(out.images.full);
        const blob = await res.blob();
        const dataUrl = await new Promise((resolve, reject) => {
          const r = new FileReader();
          r.onload = () => resolve(r.result);
          r.onerror = reject;
          r.readAsDataURL(blob);
        });
        out.images = { ...out.images, full: dataUrl };
      } catch (_) {}
    }
    return out;
  };

  const addToPersonal = async (type, item) => {
    const resolved = await resolveBlobUrlsInItem(item);
    setPersonalResources((prev) => ({
      ...prev,
      [type]: [...(prev[type] || []), resolved],
    }));
  };

  useEffect(() => {
    const checkAuth = async () => {
      const token = getToken();
      const savedUser = getUser();
      if (token && savedUser) {
        const result = await verifyToken();
        if (result.success) {
          setIsLoggedIn(true);
          setCurrentUser(result.data.user);
        } else {
          setIsLoggedIn(false);
          setCurrentUser(null);
        }
      } else {
        setIsLoggedIn(false);
        setCurrentUser(null);
      }
      setIsCheckingAuth(false);
    };
    checkAuth();
  }, []);

  const handleLogin = (user) => {
    setIsLoggedIn(true);
    setCurrentUser(user);
    setIsAuthModalOpen(false);
  };

  const handleRegister = (user) => {
    setIsLoggedIn(true);
    setCurrentUser(user);
    setIsAuthModalOpen(false);
  };

  const handleLogout = () => {
    logoutAPI();
    setIsLoggedIn(false);
    setCurrentUser(null);
  };

  if (isCheckingAuth) {
    return <div className="app"><main className="app-main">加载中...</main></div>;
  }

  return (
    <div className="app">
      <header className="app-header fade-in">
        <div className="header-content">
          <div className="header-left">
            <div className="app-title">
              <span className="title-icon">影</span>
              动智坊·皮影戏智能生成与教学平台
            </div>
            <div className="app-subtitle">AI 动作生成 × 物理仿真 × 非遗数字化</div>
          </div>

          <nav className="app-nav">
            <NavItem label="首页" active={activePage === PAGES.HOME} onClick={() => setActivePage(PAGES.HOME)} />
            <NavItem label="工作台" active={activePage === PAGES.WORKBENCH} onClick={() => setActivePage(PAGES.WORKBENCH)} />
            <NavItem label="使用文档" active={activePage === PAGES.DOCS} onClick={() => setActivePage(PAGES.DOCS)} />
            <NavItem label="公共资源库" active={activePage === PAGES.PUBLIC} onClick={() => setActivePage(PAGES.PUBLIC)} />
            <NavItem
              label={currentUser?.account_type === 'teacher' ? '教学' : '课程'}
              active={activePage === PAGES.TEACH}
              onClick={() => { setPagePayload(null); setActivePage(PAGES.TEACH); }}
            />
            <NavItem label="个人中心" active={activePage === PAGES.USER} onClick={() => setActivePage(PAGES.USER)} />
          </nav>

          <div className="header-auth">
            {isLoggedIn ? (
              <div className="user-menu">
                <span className="user-name">{currentUser?.username || '用户'}</span>
                <button className="btn-logout" onClick={handleLogout}>退出</button>
              </div>
            ) : (
              <div className="auth-buttons">
                <button className="btn-login" onClick={() => { setAuthModalMode('login'); setIsAuthModalOpen(true); }}>登录</button>
                <button className="btn-register" onClick={() => { setAuthModalMode('register'); setIsAuthModalOpen(true); }}>注册</button>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="app-main fade-in">
        {activePage === PAGES.HOME && <HomePage onStart={() => setActivePage(PAGES.WORKBENCH)} />}

        {activePage === PAGES.WORKBENCH && (
          <StationBasedWorkbench
            publicResources={publicResources}
            personalResources={personalResources}
            onAddToPersonal={addToPersonal}
          />
        )}

        {activePage === PAGES.DOCS && <DocsPage />}

        {activePage === PAGES.PUBLIC && <PublicLibraryPage publicResources={publicResources} />}

        {activePage === PAGES.PERSONAL && (
          <PersonalLibraryPage
            personalResources={personalResources}
            onUpload={addToPersonal}
          />
        )}

        {activePage === PAGES.AI && (
          <AiGeneratorPage onGenerateToPersonal={addToPersonal} />
        )}

        {activePage === PAGES.USER && (
          <UserProfilePage
            publicResources={publicResources}
            personalResources={personalResources}
            onAddToPersonal={addToPersonal}
            currentUser={currentUser}
          />
        )}

        {activePage === PAGES.TEACH && (
          <TeachPage
            currentUser={currentUser}
            onOpenClass={(classId) => {
              setPagePayload({ classId });
              setActivePage(PAGES.CLASS);
            }}
            onOpenLesson={(opts) => {
              const lessonId = opts?.lessonId ?? opts;
              const courseId = opts?.courseId;
              setPagePayload((p) => ({ ...p, lessonId, courseId }));
              setActivePage(PAGES.LESSON);
            }}
          />
        )}

        {activePage === PAGES.CLASS && (
          <ClassPage
            classId={pagePayload?.classId}
            onBack={() => setActivePage(PAGES.TEACH)}
            onOpenStage={({ classId, mode }) => {
              setPagePayload((p) => ({ ...p, classId, performanceId: p?.performanceId, mode }));
              setActivePage(PAGES.STAGE);
            }}
            onOpenLesson={(opts) => {
              const lessonId = opts?.lessonId ?? opts;
              const courseId = opts?.courseId;
              setPagePayload((p) => ({ ...p, lessonId, courseId }));
              setActivePage(PAGES.LESSON);
            }}
          />
        )}

        {activePage === PAGES.LESSON && (
          <LessonPage
            lessonId={pagePayload?.lessonId}
            courseId={pagePayload?.courseId}
            onBack={() => setActivePage(pagePayload?.classId ? PAGES.CLASS : PAGES.TEACH)}
            onOpenStage={({ lessonId, mode }) => {
              setPagePayload((p) => ({ ...p, lessonId, mode: mode || 'practice' }));
              setActivePage(PAGES.STAGE);
            }}
          />
        )}

        {activePage === PAGES.STAGE && (
          <StagePage
            performanceId={pagePayload?.performanceId}
            mode={pagePayload?.mode || 'practice'}
            classId={pagePayload?.classId}
            onBack={() => setActivePage(pagePayload?.classId ? PAGES.CLASS : PAGES.TEACH)}
          />
        )}

        {activePage === PAGES.PORTFOLIO && <PortfolioPage />}
      </main>

      <footer className="app-footer">
        <p>© 2026 MyPiying - 非遗文化数字化传承 · <button type="button" className="footer-privacy-link" onClick={() => setShowPrivacyModal(true)}>隐私条款</button></p>
      </footer>

      <PrivacyModal isOpen={showPrivacyModal} onClose={() => setShowPrivacyModal(false)} />

      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onLogin={handleLogin}
        onRegister={handleRegister}
        initialMode={authModalMode}
        onOpenPrivacyPolicy={() => setShowPrivacyModal(true)}
      />
    </div>
  );
}

function NavItem({ label, active, onClick }) {
  return (
    <button className={`nav-item ${active ? 'nav-item-active' : ''}`} onClick={onClick}>
      {label}
    </button>
  );
}

export default App;
