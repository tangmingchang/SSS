import { useState } from 'react';
import ScriptInput from '../components/ScriptInput';
import PuppetStage from '../components/PuppetStage';
import Controls from '../components/Controls';
import CameraCapture from '../components/CameraCapture';
import ActionEditor from '../components/ActionEditor';
import { API_BASE, resolveImageUrl } from '../utils/api';
import './WorkbenchPage.css';

/**
 * 鍚庣 action_sequence 鐨?emotion/action 鏄犲皠涓鸿垶鍙扮敤 action id锛堝鎺ヨ鑼?v1锛? */
function mapBackendActionsToFrontend(actionSequence) {
  if (!Array.isArray(actionSequence) || actionSequence.length === 0) return [];
  const emotionToId = {
    鎵撴枟: 'attack', 鏀诲嚮: 'attack', 琛岃蛋: 'walk', 鎸ユ墜: 'wave', 闉犺含: 'bow',
    璺宠穬: 'jump', 搴嗙: 'jump', 鏃嬭浆: 'jump', 鎮叉€? 'stand', 闃插尽: 'stand',
    闈欐: 'stand', 淇濇寔: 'stand', 閫冭窇: 'run', 娆㈠揩: 'wave',
  };
  return actionSequence.map((item) => {
    const emotion = item.emotion || '';
    const actionText = (item.action || '').slice(0, 6);
    if (emotionToId[emotion]) return emotionToId[emotion];
    if (/鎸戠嚎|涓婃寫/.test(actionText)) return 'jump';
    if (/鍘嬬|涓嬪帇/.test(actionText)) return 'bow';
    if (/杞|鏃嬭浆/.test(actionText)) return 'wave';
    return 'stand';
  });
}

/**
 * 灏嗗悗绔繑鍥炵殑 script 瀵硅薄鏍煎紡鍖栦负鍙睍绀虹殑瀛楃涓? */
function formatScriptForDisplay(script) {
  if (!script || typeof script !== 'object') return '';
  const lines = [];
  if (script.title) lines.push(script.title);
  if (script.theme) lines.push(`涓婚锛?{script.theme}`);
  if (script.character) lines.push(`瑙掕壊锛?{script.character}`);
  if (Array.isArray(script.scenes)) {
    script.scenes.forEach((s) => {
      lines.push(`\n銆愬満鏅?${s.scene_number}銆?{s.description || ''}`);
      if (s.actions && s.actions.length) lines.push(`鍔ㄤ綔锛?{s.actions.join(' 鈫?')}`);
      if (s.emotion) lines.push(`鎯呯华锛?{s.emotion}`);
    });
  }
  return lines.length ? lines.join('\n') : JSON.stringify(script, null, 2);
}

// 鍋囬€昏緫鍑芥暟锛氭兂娉?-> 鍓ф湰
function fakeGenerateSceneScript(idea) {
  if (!idea.trim()) {
    return '銆愬崟鍦烘櫙鍓ф湰銆慭n浜虹墿锛氫富瑙掋€佸弽娲綷n鍦烘櫙锛氭垙鍙癨n鍔ㄤ綔锛氳捣韬€佸宄欍€佹墦鏂椼€佹敹鍔裤€?;
  }
  
  // 濡傛灉杈撳叆鍖呭惈"鏉ㄨ吹濡?鎴?闇撹３"绛夊叧閿瘝锛岃繑鍥炲畬鏁村墽鏈?  const lowerIdea = idea.toLowerCase();
  if (lowerIdea.includes('鏉ㄨ吹濡?) || lowerIdea.includes('闇撹３') || lowerIdea.includes('璐靛')) {
    return `銆婇湏瑁崇窘琛Ｂ疯吹濡冪嫭鑸炪€?
銆愪汉鐗╄璁°€?
鏉ㄨ吹濡冪毊褰遍€犲瀷锛?
鏈嶉グ锛氬崕涓藉瑁咃紝闀胯椋橀锛岃鎽嗗灞?
澶撮グ锛氶噾鍑ゆ鎽囷紝鐝犱覆鍨傝惤

鍏宠妭锛氶閮ㄣ€佽偐閮ㄣ€佽倶閮ㄣ€佽厱閮ㄣ€佽叞閮ㄣ€佽啙閮ㄣ€佽笣閮ㄤ竷澶勬椿鍔ㄥ叧鑺?
銆愬満鏅竷缃€?
鑳屾櫙锛氬娈胯疆寤?
銆愬墽鏈唴瀹广€?
銆愬紑鍦恒€?
鍞辫瘝锛?
"鏈堢収瀹鑺卞奖鏂滐紝闇撹３涓€鏇查唹娴侀湠銆傜帀闃剁敓闇叉槬澶滄殩锛岀嫭鍊氭爮鏉嗘€濈墿鍗庛€?

銆愮涓€娈碉細鍑哄満銆?
鏉ㄨ吹濡冪毊褰卞湪鑸炲彴涓ぎ

澶撮儴寰綆锛岃〃鐜板惈缇炲甫鎬?
鍔ㄤ綔鎸囦护锛?
棰堥儴杞绘憜锛岀彔涓叉檭鍔?
鑵伴儴缂撴參杞姩锛岄暱瑁欐憜鍔?
銆愮浜屾锛氬睍琚栥€?鍞辫瘝锛?
"閲戠紩琛ｅ棣欑綏甯︼紝鐜夎噦杞昏垝闆綔鑲屻€傞暱琚栦竴灞曞崈灞傛氮锛屽洖韬浆浣撶櫨铦堕銆?

鍔ㄤ綔璁捐锛?
鍙岃噦鍚屾椂涓婃壃锛岄暱琚栧畬鍏ㄥ睍寮€

鍘熷湴鏃嬭浆锛岃鎽嗘垚鍦嗗舰缁芥斁

韬綋鍓嶅€惧悗浠帮紝琛ㄧ幇鑸炶箞闊靛緥

銆愮涓夋锛氭湜鏈堛€?鍞辫瘝锛?
"涓惧ご鏈涙湀鏈堝閽╋紝浣庡ご鎬濆悰鍚涗笉鐭ャ€備絾鎰块暱閱変笉鎰块啋锛屾ⅵ閲岀浉闅忓埌澶╂睜銆?

鍔ㄤ綔鎸囦护锛?
鎶ご鏈涙湀锛岄閮ㄥ畬鍏ㄤ几灞?
鍥㈡墖鎸囧悜鏈堜寒锛岃韩浣撳悗鍊?
鍗曡吙鎶捣锛岃〃鐜拌交鐩堣烦璺?
闀胯浠庡ご椤剁紦缂撹惤涓嬶紝濡傛湀鍏夊€炬郴

銆愮鍥涙锛氶唹鑸炪€?鍞辫瘝锛?
"閰掍笉閱変汉浜鸿嚜閱夛紝鑺变笉杩蜂汉浜鸿嚜杩枫€傞湏瑁崇窘琛ｅぉ涓婃洸锛屽嚒闂村摢寰楀嚑鍥為椈锛?

鍔ㄤ綔璁捐锛?
蹇€熸棆杞紝瑁欐憜椋炴壃

鍙岃噦浜ゅ弶鎽嗗姩锛岄暱琚栦氦缁?
韬綋澶у箙搴﹀墠鍚庢憜鍔?
銆愮浜旀锛氭敹鍔裤€?鍞辫瘝锛?
"鏇茬粓浜烘暎鏈堣タ鏂滐紝棣欐秷鐜夊噺楝撲簯鏂溿€傜暀寰楅湏瑁冲崈鍙ら煹锛屽悗浜轰紶鍞卞埌澶╂动銆?

鍔ㄤ綔鎸囦护锛?
鍔ㄤ綔閫愭笎鏀剧紦锛屽洖褰掍紭闆?
缂撶紦涓嬭共琛岀ぜ锛屽睍鐜板寤风ぜ浠猔;
  }
  
  return `銆愭牴鎹兂娉曡嚜鍔ㄧ敓鎴愮殑鍗曞満鏅墽鏈€慭n\n鎯虫硶鎽樿锛?{idea.slice(
    0,
    30
  )}...\n\n浜虹墿锛氳闊宠彥钀ㄣ€侀緳琚嶇帇甯界敓\n鍦烘櫙锛氳崚灞卞彜搴欏鏅歕n鎯呰妭锛氳闊宠彥钀ㄨ拷韪嚦鍙ゅ簷锛屼袱浜哄睍寮€涓€杞璇濅笌浜掑姩锛屾渶缁堣揪鎴愬拰瑙ｃ€俓n鍔ㄤ綔锛氳捣韬珯瀹?鈫?琛岃蛋鎺ヨ繎 鈫?鎸ユ墜绀烘剰 鈫?闉犺含鑷存剰 鈫?鏀跺娍銆俙;
}

// 鍋囬€昏緫鍑芥暟锛氬満鏅垎鏋?function fakeAnalyzeScene(state) {
  const selectedScene = state.background;
  const selectedCharacter = state.selectedCharacter;
  
  // 鏍规嵁閫夋嫨鐨勫満鏅敓鎴愪笉鍚岀殑鍒嗘瀽
  if (selectedScene?.id === 'scene-1' || selectedScene?.name === '鑸炲彴') {
    return {
      summary: '骞冲彴瀵瑰綋鍓嶅満鏅仛浜嗚涔夊拰鍔ㄤ綔鍒嗘瀽锛岀粨鏋滃涓嬶細',
      highlights: [
        '鍦烘櫙鍖归厤锛氱粡鍏歌垶鍙板満鏅紝閫傚悎灞曠幇浼犵粺鐨奖鎴忕殑琛ㄦ紨姘涘洿锛岀伅鍏夋晥鏋滅獊鍑?,
        '瑙掕壊閫傞厤锛氭潹璐靛鐨勫崕涓藉瑁呬笌鑸炲彴鑳屾櫙褰㈡垚瀹岀編鍛煎簲锛岀獊鍑哄寤疯垶韫堢殑搴勯噸鎰?,
        '鑺傚缁撴瀯锛氬紑鍦哄惈缇炲甫鎬?鈫?灞曡璧疯垶 鈫?鏈涙湀鎬濆悰 鈫?閱夎垶楂樻疆 鈫?浼橀泤鏀跺娍锛屼簲娈靛紡缁撴瀯娓呮櫚',
        '鍏夊奖寤鸿锛氳垶鍙板満鏅€傚悎浣跨敤涓瓑寮哄害鐏厜锛岀獊鍑鸿鑹茶疆寤撳拰鍔ㄤ綔缁嗚妭',
        '鍔ㄤ綔寤鸿锛氬睍琚栥€佹棆杞€佹湜鏈堢瓑鍔ㄤ綔鍦ㄨ垶鍙拌儗鏅笅瑙嗚鏁堟灉鏈€浣筹紝寤鸿淇濇寔鍔ㄤ綔娴佺晠杩炶疮',
      ],
    };
  }
  
  if (selectedCharacter?.name?.includes('鏉ㄨ吹濡?)) {
    return {
      summary: '骞冲彴瀵瑰綋鍓嶅満鏅仛浜嗚涔夊拰鍔ㄤ綔鍒嗘瀽锛岀粨鏋滃涓嬶細',
      highlights: [
        '瑙掕壊鐗圭偣锛氭潹璐靛瑙掕壊閫傚悎鏂囨垙鍜岃垶韫堢被鍔ㄤ綔锛岄暱琚栭椋樼殑閫犲瀷閫傚悎灞曡銆佹棆杞瓑鍔ㄤ綔',
        '鑺傚缁撴瀯锛氬紑鍦烘枃鎴忛摵鍨紝涓鑸炶箞楂樻疆锛岀粨灏句紭闆呮敹鏉?,
        '鍦烘櫙鍖归厤锛氬娈跨被鍦烘櫙涓庢潹璐靛瑙掕壊楂樺害鍖归厤锛岃惀閫犲寤锋皼鍥?,
        '寤鸿锛氬彲鍦ㄥ紑澶村鍔犱竴涓參閫熴€屼寒鐩搞€嶅姩浣滐紝璁╄浼楁洿濂借瘑鍒鑹?,
      ],
    };
  }
  
  return {
    summary: '骞冲彴瀵瑰綋鍓嶅満鏅仛浜嗚涔夊拰鍔ㄤ綔鍒嗘瀽锛岀粨鏋滃涓嬶細',
    highlights: [
      '鑺傚缁撴瀯锛氬紑澶存枃鎴忛摵鍨紝涓瀵硅瘽浜掑姩锛岀粨灏炬敹鏉熷喎闈?,
      '瑙掕壊鍏崇郴锛氳闊宠彥钀ㄤ负涓诲姩寮曞鏂癸紝榫欒鐜嬪附鐢熷姩浣滃亸銆屾伃鏁?/ 鍥炲簲銆?,
      '鍦烘櫙鍖归厤锛氳崚灞卞彜搴?+ 澶滄櫙 + 寮哄姣斿厜褰憋紝閫傚悎琛ㄧ幇绁炵姘涘洿',
      '寤鸿锛氬彲鍦ㄥ紑澶村鍔犱竴涓參閫熴€屼寒鐩搞€嶅姩浣滐紝璁╄浼楁洿濂借瘑鍒鑹?,
    ],
  };
}

// 鍋囬€昏緫鍑芥暟锛氬姩浣滃簭鍒?function fakeActionSequenceForMotion(motion) {
  if (!motion) return [];
  if (motion.name?.includes('涓夎繛鍑?)) {
    return ['stand', 'attack', 'attack', 'attack', 'bow'];
  }
  if (motion.name?.includes('灞曡') || motion.name?.includes('璧疯垶')) {
    return ['stand', 'wave', 'wave', 'jump', 'bow'];
  }
  if (motion.name?.includes('鏈涙湀')) {
    return ['stand', 'wave', 'jump', 'bow'];
  }
  if (motion.name?.includes('閱夎垶') || motion.name?.includes('鏃嬭浆')) {
    return ['stand', 'jump', 'jump', 'wave', 'bow'];
  }
  if (motion.name?.includes('鏀跺娍') || motion.name?.includes('琛岀ぜ')) {
    return ['stand', 'bow'];
  }
  if (motion.name?.includes('鍑哄満') || motion.name?.includes('浜浉')) {
    return ['stand'];
  }
  return ['stand', 'walk', 'wave', 'attack', 'jump', 'bow'];
}

// 鍋囬€昏緫鍑芥暟锛氱敓鎴愯棰戝崰浣?function fakeGenerateVideo(state) {
  return {
    id: 'video-1',
    title: '銆婂崟鍦烘櫙鐨奖鎴忋€?,
    url: '/鐢熸垚缁撴灉.mp4',
  };
}

function WorkbenchPage({
  workbenchState,
  updateWorkbench,
  publicResources,
  personalResources,
  actionSequence,
  setActionSequence,
  playing,
  setPlaying,
  onAddToPersonal,
}) {
  const [step, setStep] = useState(1);
  const [scriptError, setScriptError] = useState(null);
  const [characterSource, setCharacterSource] = useState('library');
  const [aiCharPrompt, setAiCharPrompt] = useState('');
  const [aiCharGenerating, setAiCharGenerating] = useState(false);
  const [aiCharGenerated, setAiCharGenerated] = useState(null);

  const [isGeneratingScript, setIsGeneratingScript] = useState(false);
  const [scriptGenerationProgress, setScriptGenerationProgress] = useState(0);
  const [isGeneratingVideo, setIsGeneratingVideo] = useState(false);
  const [videoGenerationProgress, setVideoGenerationProgress] = useState(0);
  const [backgroundSource, setBackgroundSource] = useState('library');
  const [aiBgPrompt, setAiBgPrompt] = useState('');
  const [aiBgGenerating, setAiBgGenerating] = useState(false);
  const [aiBgGenerated, setAiBgGenerated] = useState(null);
  const [livePoseData, setLivePoseData] = useState(null);
  const [liveTrackingStatus, setLiveTrackingStatus] = useState('idle');
  const [preferMocapCharacter, setPreferMocapCharacter] = useState(false);
  const [driveMode, setDriveMode] = useState('camera'); // camera | kinect

  const goToStepAtLeast = (target) => {
    setStep((prev) => Math.max(prev, target));
  };

  // 1. 鎯虫硶 鈫?鍓ф湰锛堢湡瀹炲悗绔細POST /api/generate_script锛?  const handleIdeaToScript = async () => {
    const idea = (workbenchState.idea || '').trim();
    if (!idea) return;
    setIsGeneratingScript(true);
    setScriptGenerationProgress(0);
    setScriptError(null);
    const progressInterval = setInterval(() => {
      setScriptGenerationProgress((prev) => (prev >= 90 ? 90 : prev + Math.random() * 12));
    }, 400);
    try {
      const res = await fetch(`${API_BASE}/api/generate_script`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ theme: idea, character: '', length: 1 }), // 鍗曚釜鍦烘櫙鍓ф湰
      });
      const data = await res.json().catch(() => ({}));
      clearInterval(progressInterval);
      setScriptGenerationProgress(100);
      if (!res.ok) {
        setScriptError(data.error || `璇锋眰澶辫触 ${res.status}`);
        return;
      }
      if (!data.success || !data.script) {
        setScriptError(data.error || '鏈繑鍥炲墽鏈暟鎹?);
        return;
      }
      const scriptDisplay = formatScriptForDisplay(data.script);
      const frontendActions = mapBackendActionsToFrontend(data.action_sequence || []);
      updateWorkbench({
        sceneScript: scriptDisplay,
        confirmScene: scriptDisplay,
        scriptData: data.script, // 淇濆瓨瀹屾暣鐨剆cript瀵硅薄
        actionSequenceData: data.action_sequence || [], // 淇濆瓨鍘熷鍔ㄤ綔搴忓垪鏁版嵁
      });
      setActionSequence(frontendActions.length ? frontendActions : ['stand', 'walk', 'wave', 'bow']);
      goToStepAtLeast(2);
    } catch (err) {
      clearInterval(progressInterval);
      setScriptGenerationProgress(100);
      const isConnectionRefused = err.message === 'Failed to fetch' || err.name === 'TypeError';
      setScriptError(
        isConnectionRefused
          ? '鏃犳硶杩炴帴鍚庣锛堣繛鎺ヨ鎷掔粷锛夈€傝鍏堝湪椤圭洰鏍圭洰褰曞惎鍔細python web_app.py'
          : (err.message || '缃戠粶閿欒锛岃纭鍚庣宸插惎鍔紙python web_app.py锛?)
      );
    } finally {
      setIsGeneratingScript(false);
    }
  };

  // 6. 鍒嗘瀽
  const handleAnalyze = () => {
    const analysis = fakeAnalyzeScene(workbenchState);
    updateWorkbench({ analysis });
    goToStepAtLeast(6);
  };

  // 8/9. 鐢熸垚瑙嗛锛堝甫鍔犺浇鍔ㄧ敾锛屼絾涓嶅啀閿佹鏁翠釜椤甸潰锛?  const handleGenerateVideo = () => {
    setIsGeneratingVideo(true);
    setVideoGenerationProgress(0);
    goToStepAtLeast(8);

    const progressInterval = setInterval(() => {
      setVideoGenerationProgress((prev) => {
        if (prev >= 90) {
          clearInterval(progressInterval);
          return 90;
        }
        return prev + Math.random() * 15;
      });
    }, 500);

    setTimeout(() => {
      clearInterval(progressInterval);
      setVideoGenerationProgress(100);
      const video = fakeGenerateVideo(workbenchState);
      updateWorkbench({ video });
      setIsGeneratingVideo(false);
    }, 5000);
  };

  // 鈶?AI 鐢熸垚鑳屾櫙锛氳皟鐢ㄨ眴鍖?鐏北 API锛堝悗绔?/api/generate_background锛?  const handleGenerateBackground = async () => {
    if (!aiBgPrompt.trim()) return;
    setAiBgGenerating(true);
    setAiBgGenerated(null);
    try {
      const res = await fetch(`${API_BASE}/api/generate_background`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: aiBgPrompt.trim() }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setScriptError(data.error || '鐢熸垚澶辫触');
        return;
      }
      if (data.success && data.url) {
        const scene = {
          id: data.id || `ai-bg-${Date.now()}`,
          name: data.name || 'AI鐢熸垚鑳屾櫙',
          url: data.url,
          thumbnail: data.thumbnail || data.url,
        };
        setAiBgGenerated(scene);
        updateWorkbench({ background: scene });
        goToStepAtLeast(5);
      }
    } catch (err) {
      setScriptError(err.message || '鏃犳硶杩炴帴鍚庣锛岃纭 python web_app.py 宸插惎鍔?);
    } finally {
      setAiBgGenerating(false);
    }
  };

  // 鈶?AI 鐢熸垚瑙掕壊锛氳皟鐢ㄥ熀浜庣幇鏈夋暟鎹缁冪殑妯″瀷锛堝悗绔?/api/generate_character锛?  const handleGenerateCharacter = async () => {
    if (!aiCharPrompt.trim()) return;
    setAiCharGenerating(true);
    setAiCharGenerated(null);
    try {
      const res = await fetch(`${API_BASE}/api/generate_character`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: aiCharPrompt.trim() }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setScriptError(data.error || '鐢熸垚澶辫触');
        return;
      }
      if (data.success && data.image_url) {
        const char = {
          id: data.id || `ai-${Date.now()}`,
          name: data.name || 'AI鐢熸垚瑙掕壊',
          thumbnail: data.thumbnail || data.image_url,
          images: { full: data.image_url },
        };
        setAiCharGenerated(char);
        updateWorkbench({ selectedCharacter: char });
        goToStepAtLeast(3);
      }
    } catch (err) {
      setScriptError(err.message || '鏃犳硶杩炴帴鍚庣锛岃纭 python web_app.py 宸插惎鍔?);
    } finally {
      setAiCharGenerating(false);
    }
  };

  // 鍚堝苟璧勬簮搴撴暟鎹?  const allCharacters = [
    ...publicResources.characters.map((char) => ({
      id: char.id,
      name: char.name,
      roleClass:
        char.id === 'guanyin'
          ? 'role-guanyin'
          : char.id === 'emperor'
          ? 'role-emperor'
          : 'role-default',
      thumbnail: char.thumbnail || null,
      image_url: char.image_url || null,
      images: char.images || {},
      mocapPreferred: !!char.mocapPreferred,
      description: `${char.name} - ${char.style || '浼犵粺鐨奖瑙掕壊'}`,
    })),
    ...personalResources.characters.map((char) => ({
      id: char.id,
      name: char.name,
      roleClass: 'role-default',
      thumbnail: char.thumbnail || null,
      image_url: char.image_url || null,
      images: char.images || {},
      mocapPreferred: !!char.mocapPreferred,
      description: `${char.name} - 涓汉璧勬簮`,
    })),
  ];

  const allScenes = [...publicResources.scenes, ...personalResources.scenes];
  const allMotions = [...publicResources.motions, ...personalResources.motions];

  const steps = [
    { num: 1, label: '杈撳叆鎯虫硶' },
    { num: 2, label: '鐢熸垚鍓ф湰' },
    { num: 3, label: '閫夋嫨瑙掕壊' },
    { num: 4, label: '閫夋嫨鍔ㄤ綔' },
    { num: 5, label: '閫夋嫨鑳屾櫙' },
    { num: 6, label: '鍦烘櫙鍒嗘瀽' },
    { num: 7, label: '纭鍦烘櫙' },
    { num: 8, label: '鐢熸垚瑙嗛' },
    { num: 9, label: '瀹屾垚' },
  ];

  // 涓€浜涙柟渚跨敤鐨勯粯璁ゅ€?  const videoOptions = workbenchState.videoOptions || {
    lighting: 0.7,
    useLibraryMusic: true,
  };

  return (
    <div className="workbench">
      {/* 姝ラ鏉★細鐜板湪浠呯敤浜庨珮浜睍绀猴紝鍙互鐐逛换浣曚竴椤?*/}
      <div className="step-header">
        {steps.map((s) => {
          const isActive = step >= s.num;
          const isCurrent = step === s.num;
          return (
            <button
              key={s.num}
              type="button"
              className={`step-item ${
                isActive ? 'active' : ''
              } ${isCurrent ? 'current' : ''}`}
              onClick={() => setStep(s.num)}
            >
              <div className="step-number">{s.num}</div>
              <div className="step-label">{s.label}</div>
            </button>
          );
        })}
      </div>

      <div className="workbench-grid">
        {/* 宸﹀垪锛?-5 姝?*/}
        <div className="workbench-col">
          {/* Step1 鎯虫硶杈撳叆 */}
          <section className="wb-card">
            <h3>鈶?杈撳叆鍒涗綔鎯虫硶</h3>
            <p className="wb-desc">
              鐢ㄨ嚜鐒惰瑷€鎻忚堪浣犳兂瑕佺殑鐗囨锛屼緥濡傦細瑙傞煶鑿╄惃涓庨緳琚嶇帇甯界敓鍦ㄨ崚灞卞彜搴欏璋堬紝绐佸嚭鏂囨垙涓庡簞閲嶆皼鍥淬€?            </p>
            <textarea
              className="wb-textarea"
              value={workbenchState.idea}
              onChange={(e) => updateWorkbench({ idea: e.target.value })}
              placeholder="鍦ㄨ繖閲岃緭鍏ヤ綘鐨勫垱浣滄兂娉?.."
              rows={4}
            />
            {scriptError && (
              <p className="script-error" style={{ color: '#ff6b6b', fontSize: '12px', marginTop: '8px' }}>
                {scriptError}
              </p>
            )}
            <button
              className="btn-primary"
              onClick={handleIdeaToScript}
              disabled={!workbenchState.idea.trim() || isGeneratingScript}
            >
              {isGeneratingScript ? '姝ｅ湪鐢熸垚涓?..' : '鐢熸垚鍗曞満鏅墽鏈?}
            </button>
          </section>

          {/* Step2 鍓ф湰棰勮锛堝缁堟樉绀猴紝娌＄敓鎴愬氨鏄剧ず鎻愮ず锛?*/}
          <section className="wb-card">
            <h3>鈶?鍗曚釜鍦烘櫙鍓ф湰棰勮</h3>
            <p className="wb-desc">
              骞冲彴鏍规嵁浣犵殑鎯虫硶鐢熸垚涓€娈靛崟鍦烘櫙鍓ф湰鏂囨湰锛屽寘鍚汉鐗┿€佸満鏅笌澶ц嚧鍔ㄤ綔銆?            </p>
            {isGeneratingScript ? (
              <div className="script-loading">
                <div className="script-loading-spinner">
                  <div className="spinner-ring"></div>
                  <div className="spinner-ring"></div>
                  <div className="spinner-ring"></div>
                </div>
                <div className="script-loading-text">姝ｅ湪鐢熸垚鍓ф湰...</div>
                <div className="script-loading-progress">
                  <div
                    className="script-loading-progress-bar"
                    style={{ width: `${scriptGenerationProgress}%` }}
                  ></div>
                  <span className="script-loading-progress-text">
                    {Math.round(scriptGenerationProgress)}%
                  </span>
                </div>
                <div className="script-loading-steps">
                  <div className={scriptGenerationProgress > 20 ? 'step-done' : 'step-pending'}>
                    鉁?鍒嗘瀽鍒涗綔鎯虫硶
                  </div>
                  <div className={scriptGenerationProgress > 50 ? 'step-done' : 'step-pending'}>
                    鉁?鐢熸垚鍓ф湰缁撴瀯
                  </div>
                  <div className={scriptGenerationProgress > 80 ? 'step-done' : 'step-pending'}>
                    {scriptGenerationProgress > 80 ? '鉁? : '鈼?} 瀹屽杽鍓ф湰缁嗚妭...
                  </div>
                </div>
              </div>
            ) : (
              <pre className="wb-script-preview">
                {workbenchState.sceneScript || '鏆傛湭鐢熸垚鍓ф湰锛岃鍏堝湪涓婃柟杈撳叆鎯虫硶骞剁偣鍑绘寜閽€?}
              </pre>
            )}
          </section>

          {/* Step3 瑙掕壊閫夋嫨锛氳祫婧愬簱 + AI 鐢熸垚锛堝熀浜庣幇鏈夋暟鎹缁冪殑妯″瀷锛?*/}
          <section className="wb-card">
            <h3>鈶?閫夋嫨鐨奖瑙掕壊绱犳潗</h3>
            <p className="wb-desc">
              浠庤祫婧愬簱閫夋嫨宸叉湁绱犳潗锛屾垨浣跨敤 AI 鐢熸垚锛堢敓鎴愭ā鍨嬪熀浜庣幇鏈夌毊褰辫鑹叉暟鎹缁冿級銆?            </p>
            <div className="wb-char-source-tabs" style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
              <button
                type="button"
                className={characterSource === 'library' ? 'btn-primary' : 'btn-secondary'}
                style={{ flex: 1, padding: '8px 12px' }}
                onClick={() => {
                setCharacterSource('library');
                setAiCharGenerated(null);
                if (workbenchState.selectedCharacter?.id?.startsWith?.('ai-')) {
                  updateWorkbench({ selectedCharacter: null });
                }
              }}
                disabled={!workbenchState.sceneScript}
              >
                璧勬簮搴?              </button>
              <button
                type="button"
                className={characterSource === 'ai' ? 'btn-primary' : 'btn-secondary'}
                style={{ flex: 1, padding: '8px 12px' }}
                onClick={() => { setCharacterSource('ai'); updateWorkbench({ selectedCharacter: aiCharGenerated || null }); }}
                disabled={!workbenchState.sceneScript}
              >
                AI 鐢熸垚
              </button>
            </div>

            {characterSource === 'library' && (
              <>
                <p className="wb-desc" style={{ marginBottom: '10px', fontSize: '12px', color: '#a09080' }}>
                  鐐瑰嚮涓嬫柟鍥剧墖閫変腑瑙掕壊
                </p>
                {allCharacters.length === 0 ? (
                  <p style={{ color: '#a09080', fontSize: '13px' }}>鏆傛棤瑙掕壊锛岃浣跨敤 AI 鐢熸垚鎴栦粠鍏叡璧勬簮搴撴坊鍔犮€?/p>
                ) : (
                  <div className="wb-resource-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(100px, 1fr))', gap: '10px', marginTop: '8px' }}>
                    {allCharacters.map((c) => {
                      const isSelected = workbenchState.selectedCharacter?.id === c.id;
                      const imgUrl = resolveImageUrl(c.thumbnail || c.images?.full || c.image_url);
                      return (
                        <div
                          key={c.id}
                          role="button"
                          tabIndex={0}
                          onClick={() => {
                            if (workbenchState.sceneScript) {
                              updateWorkbench({ selectedCharacter: c });
                              goToStepAtLeast(3);
                            }
                          }}
                          onKeyDown={(e) => {
                            if ((e.key === 'Enter' || e.key === ' ') && workbenchState.sceneScript) {
                              e.preventDefault();
                              updateWorkbench({ selectedCharacter: c });
                              goToStepAtLeast(3);
                            }
                          }}
                          style={{
                            cursor: workbenchState.sceneScript ? 'pointer' : 'default',
                            padding: '6px',
                            borderRadius: '8px',
                            border: isSelected ? '2px solid #E6A800' : '1px solid rgba(255, 220, 160, 0.3)',
                            background: isSelected ? 'rgba(230, 168, 0, 0.12)' : 'rgba(255,255,255,0.04)',
                            textAlign: 'center',
                          }}
                          title="鐐瑰嚮閫変腑姝よ鑹?
                        >
                          {imgUrl ? (
                            <img
                              src={imgUrl}
                              alt={c.name}
                              style={{ width: '100%', aspectRatio: '1', objectFit: 'contain', borderRadius: '6px', pointerEvents: 'none' }}
                            />
                          ) : (
                            <div style={{ width: '100%', aspectRatio: '1', background: 'rgba(255,220,160,0.1)', borderRadius: '6px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '11px', color: '#a09080' }}>鏃犲浘</div>
                          )}
                          <p style={{ marginTop: '4px', fontSize: '11px', color: '#e8dcc5', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.name}</p>
                          {isSelected && <p style={{ fontSize: '10px', color: '#E6A800' }}>宸查€変腑</p>}
                        </div>
                      );
                    })}
                  </div>
                )}
              </>
            )}

            {characterSource === 'ai' && (
              <>
                <textarea
                  className="wb-textarea"
                  value={aiCharPrompt}
                  onChange={(e) => { setAiCharPrompt(e.target.value); setScriptError(null); }}
                  placeholder="鎻忚堪鎯宠鐨勮鑹诧紝渚嬪锛氭灄榛涚帀钁姳銆佹潹璐靛闇撹３銆佽闊宠彥钀?
                  rows={2}
                  style={{ marginBottom: '8px' }}
                  disabled={!workbenchState.sceneScript}
                />
                {scriptError && (
                  <p className="script-error" style={{ color: '#ff6b6b', fontSize: '12px', marginBottom: '8px' }}>
                    {scriptError}
                  </p>
                )}
                <button
                  type="button"
                  className="btn-primary"
                  onClick={handleGenerateCharacter}
                  disabled={!aiCharPrompt.trim() || aiCharGenerating || !workbenchState.sceneScript}
                >
                  {aiCharGenerating ? '鐢熸垚涓?..' : '鐢熸垚瑙掕壊锛堝熀浜庣幇鏈夋暟鎹ā鍨嬶級'}
                </button>
                {aiCharGenerated && (
                  <div style={{ marginTop: '12px' }}>
                    <div
                      role="button"
                      tabIndex={0}
                      onClick={() => updateWorkbench({ selectedCharacter: aiCharGenerated })}
                      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); updateWorkbench({ selectedCharacter: aiCharGenerated }); } }}
                      style={{
                        textAlign: 'center',
                        marginBottom: '8px',
                        cursor: 'pointer',
                        padding: '8px',
                        borderRadius: '8px',
                        border: workbenchState.selectedCharacter?.id === aiCharGenerated?.id
                          ? '2px solid #E6A800'
                          : '1px solid rgba(255, 220, 160, 0.3)',
                        background: workbenchState.selectedCharacter?.id === aiCharGenerated?.id ? 'rgba(230, 168, 0, 0.12)' : 'transparent',
                      }}
                      title="鐐瑰嚮閫変腑姝よ鑹?
                    >
                      <img
                        src={resolveImageUrl(aiCharGenerated.thumbnail || aiCharGenerated.images?.full || aiCharGenerated.image_url)}
                        alt={aiCharGenerated.name}
                        style={{ maxWidth: '100%', maxHeight: '200px', objectFit: 'contain', borderRadius: '6px', pointerEvents: 'none', display: 'block', margin: '0 auto' }}
                      />
                      <p style={{ marginTop: '8px', fontSize: '12px', color: '#e8dcc5' }}>{aiCharGenerated.name}</p>
                      {workbenchState.selectedCharacter?.id === aiCharGenerated?.id && (
                        <p style={{ fontSize: '11px', color: '#E6A800', marginTop: '4px' }}>宸查€変腑</p>
                      )}
                    </div>
                    {onAddToPersonal && (
                      <button
                        type="button"
                        className="btn-secondary"
                        style={{ width: '100%', marginTop: '8px' }}
                        onClick={() => { onAddToPersonal('characters', aiCharGenerated); alert('宸蹭繚瀛樺埌涓汉璧勬簮搴?); }}
                      >
                        淇濆瓨鍒颁釜浜鸿祫婧愬簱
                      </button>
                    )}
                  </div>
                )}
              </>
            )}
          </section>

          {/* Step4 鍔ㄤ綔缂栬緫 */}
          <section className="wb-card">
            <h3>鈶?缂栬緫瑙掕壊鍔ㄤ綔</h3>
            <p className="wb-desc">
              浠庡墽鏈腑鎻愬彇鐨勫姩浣滆妭鐐癸紝浣犲彲浠ヨ嚜鐢辨坊鍔犮€佸垹闄ゆ垨淇敼鍔ㄤ綔锛岃繖浜涘姩浣滃皢椹卞姩鑸炲彴涓殑鐨奖瑙掕壊銆?            </p>
            {!workbenchState.selectedCharacter ? (
              <div style={{ padding: '20px', textAlign: 'center', color: '#a09080', fontSize: '13px' }}>
                璇峰厛閫夋嫨瑙掕壊
              </div>
            ) : !workbenchState.scriptData ? (
              <div style={{ padding: '20px', textAlign: 'center', color: '#a09080', fontSize: '13px' }}>
                璇峰厛鐢熸垚鍓ф湰
              </div>
            ) : (
              <ActionEditor
                script={workbenchState.scriptData}
                actionSequence={workbenchState.actionSequenceData}
                onChange={(actions) => {
                  // 灏嗙紪杈戝悗鐨勫姩浣滆浆鎹负鍓嶇鍙敤鐨勬牸寮?                  const frontendActions = actions.map((action) => {
                    const actionText = action.actionText || '';
                    // 鏍规嵁鍔ㄤ綔鏂囨湰鏄犲皠鍒板墠绔姩浣淚D
                    if (/鎸戠嚎|涓婃寫/.test(actionText)) return 'jump';
                    if (/鍘嬬|涓嬪帇/.test(actionText)) return 'bow';
                    if (/杞|鏃嬭浆/.test(actionText)) return 'wave';
                    if (/淇濇寔|闈欐/.test(actionText)) return 'stand';
                    // 鏍规嵁鎯呯华鏄犲皠
                    const emotion = action.emotion || '';
                    const emotionToId = {
                      鎵撴枟: 'attack', 鏀诲嚮: 'attack', 琛岃蛋: 'walk', 鎸ユ墜: 'wave', 闉犺含: 'bow',
                      璺宠穬: 'jump', 搴嗙: 'jump', 鏃嬭浆: 'jump', 鎮叉€? 'stand', 闃插尽: 'stand',
                      闈欐: 'stand', 淇濇寔: 'stand', 閫冭窇: 'run', 娆㈠揩: 'wave',
                    };
                    return emotionToId[emotion] || 'stand';
                  });
                  setActionSequence(frontendActions);
                  goToStepAtLeast(4);
                }}
              />
            )}
          </section>

          {/* Step5 鑳屾櫙閫夋嫨 */}
          <section className="wb-card">
            <h3>鈶?鎻愪緵鑳屾櫙鍥剧墖</h3>
            <p className="wb-desc">
              浠庤祫婧愬簱涓€夋嫨鍦烘櫙鍥剧墖锛屾垨浣跨敤 AI 鐢熸垚鑳屾櫙銆?            </p>
            <div className="wb-char-source-tabs" style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
              <button
                type="button"
                className={backgroundSource === 'library' ? 'btn-primary' : 'btn-secondary'}
                style={{ flex: 1, padding: '8px 12px' }}
                onClick={() => {
                  setBackgroundSource('library');
                  setAiBgGenerated(null);
                  if (workbenchState.background?.id?.startsWith?.('ai-bg-')) {
                    updateWorkbench({ background: null });
                  }
                }}
                disabled={!workbenchState.sceneScript}
              >
                璧勬簮搴?              </button>
              <button
                type="button"
                className={backgroundSource === 'ai' ? 'btn-primary' : 'btn-secondary'}
                style={{ flex: 1, padding: '8px 12px' }}
                onClick={() => {
                  setBackgroundSource('ai');
                  updateWorkbench({ background: aiBgGenerated || null });
                }}
                disabled={!workbenchState.sceneScript}
              >
                AI 鐢熸垚
              </button>
            </div>

            {backgroundSource === 'library' && (
              <>
                <p className="wb-desc" style={{ marginBottom: '10px', fontSize: '12px', color: '#a09080' }}>
                  鐐瑰嚮涓嬫柟鍥剧墖閫変腑鑳屾櫙
                </p>
                {allScenes.length === 0 ? (
                  <p style={{ color: '#a09080', fontSize: '13px' }}>鏆傛棤鑳屾櫙锛岃浣跨敤 AI 鐢熸垚鎴栦粠鍏叡璧勬簮搴撴坊鍔犮€?/p>
                ) : (
                  <div className="wb-resource-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(100px, 1fr))', gap: '10px', marginTop: '8px' }}>
                    {allScenes.map((s) => {
                      const isSelected = workbenchState.background?.id === s.id;
                      const imgUrl = resolveImageUrl(s.thumbnail || s.url);
                      return (
                        <div
                          key={s.id}
                          role="button"
                          tabIndex={0}
                          onClick={() => {
                            if (workbenchState.sceneScript) {
                              updateWorkbench({ background: s });
                              goToStepAtLeast(5);
                            }
                          }}
                          onKeyDown={(e) => {
                            if ((e.key === 'Enter' || e.key === ' ') && workbenchState.sceneScript) {
                              e.preventDefault();
                              updateWorkbench({ background: s });
                              goToStepAtLeast(5);
                            }
                          }}
                          style={{
                            cursor: workbenchState.sceneScript ? 'pointer' : 'default',
                            padding: '6px',
                            borderRadius: '8px',
                            border: isSelected ? '2px solid #E6A800' : '1px solid rgba(255, 220, 160, 0.3)',
                            background: isSelected ? 'rgba(230, 168, 0, 0.12)' : 'rgba(255,255,255,0.04)',
                            textAlign: 'center',
                          }}
                          title="鐐瑰嚮閫変腑姝よ儗鏅?
                        >
                          {imgUrl ? (
                            <img
                              src={imgUrl}
                              alt={s.name}
                              style={{ width: '100%', aspectRatio: '4/3', objectFit: 'cover', borderRadius: '6px', pointerEvents: 'none' }}
                            />
                          ) : (
                            <div style={{ width: '100%', aspectRatio: '4/3', background: 'rgba(255,220,160,0.1)', borderRadius: '6px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '11px', color: '#a09080' }}>鏃犲浘</div>
                          )}
                          <p style={{ marginTop: '4px', fontSize: '11px', color: '#e8dcc5', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.name}</p>
                          {isSelected && <p style={{ fontSize: '10px', color: '#E6A800' }}>宸查€変腑</p>}
                        </div>
                      );
                    })}
                  </div>
                )}
              </>
            )}

            {backgroundSource === 'ai' && (
              <>
                <textarea
                  className="wb-textarea"
                  value={aiBgPrompt}
                  onChange={(e) => setAiBgPrompt(e.target.value)}
                  placeholder="鎻忚堪鎯宠鐨勮儗鏅紝渚嬪锛氬彜鍏稿洯鏋椼€佸鏅氭槦绌恒€佽崚灞卞彜搴欍€佸娈垮唴鏅?
                  rows={2}
                  style={{ marginBottom: '8px' }}
                  disabled={!workbenchState.sceneScript}
                />
                <button
                  type="button"
                  className="btn-primary"
                  onClick={handleGenerateBackground}
                  disabled={!aiBgPrompt.trim() || aiBgGenerating || !workbenchState.sceneScript}
                >
                  {aiBgGenerating ? '鐢熸垚涓?..' : '鐢熸垚鑳屾櫙'}
                </button>
                {aiBgGenerated && (
                  <div style={{ marginTop: '12px' }}>
                    <div
                      role="button"
                      tabIndex={0}
                      onClick={() => updateWorkbench({ background: aiBgGenerated })}
                      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); updateWorkbench({ background: aiBgGenerated }); } }}
                      style={{
                        textAlign: 'center',
                        marginBottom: '8px',
                        cursor: 'pointer',
                        padding: '8px',
                        borderRadius: '8px',
                        border: workbenchState.background?.id === aiBgGenerated?.id ? '2px solid #E6A800' : '1px solid rgba(255, 220, 160, 0.3)',
                        background: workbenchState.background?.id === aiBgGenerated?.id ? 'rgba(230, 168, 0, 0.12)' : 'transparent',
                      }}
                      title="鐐瑰嚮閫変腑姝よ儗鏅?
                    >
                      <img
                        src={resolveImageUrl(aiBgGenerated.thumbnail || aiBgGenerated.url)}
                        alt={aiBgGenerated.name}
                        style={{ maxWidth: '100%', maxHeight: '200px', objectFit: 'contain', borderRadius: '6px', pointerEvents: 'none', display: 'block', margin: '0 auto' }}
                      />
                      <p style={{ marginTop: '8px', fontSize: '12px', color: '#e8dcc5' }}>{aiBgGenerated.name}</p>
                      {aiBgGenerated.note && <p style={{ marginTop: '4px', fontSize: '11px', color: '#a09080' }}>{aiBgGenerated.note}</p>}
                      {workbenchState.background?.id === aiBgGenerated?.id && <p style={{ fontSize: '11px', color: '#E6A800', marginTop: '4px' }}>宸查€変腑</p>}
                    </div>
                    {onAddToPersonal && (
                      <button
                        type="button"
                        className="btn-secondary"
                        style={{ width: '100%', marginTop: '8px' }}
                        onClick={(e) => { e.stopPropagation(); onAddToPersonal('scenes', aiBgGenerated); alert('宸蹭繚瀛樺埌涓汉璧勬簮搴?); }}
                      >
                        淇濆瓨鍒颁釜浜鸿祫婧愬簱
                      </button>
                    )}
                  </div>
                )}
              </>
            )}
          </section>

          {/* 鎽勫儚澶村姩浣滄崟鎹夊尯锛氬綍鍒跺悗 FormData 涓婁紶 /api/capture_motion锛屾垚鍔熷垯鍙笅杞?BVH */}
          <section className="wb-card">
            <div style={{ marginBottom: '12px', padding: '10px', borderRadius: '8px', background: 'rgba(0,0,0,0.15)' }}>
              <p style={{ margin: '0 0 8px 0', fontSize: '12px', color: '#e8dcc5' }}>驱动模式</p>
              <label style={{ marginRight: '14px', fontSize: '12px', color: '#d8c8a8' }}>
                <input
                  type="radio"
                  name="driveMode"
                  value="camera"
                  checked={driveMode === 'camera'}
                  onChange={() => {
                    setDriveMode('camera');
                  }}
                  style={{ marginRight: '6px' }}
                />
                普通摄像头实时驱动（无 Kinect）
              </label>
              <label style={{ fontSize: '12px', color: '#d8c8a8' }}>
                <input
                  type="radio"
                  name="driveMode"
                  value="kinect"
                  checked={driveMode === 'kinect'}
                  onChange={() => {
                    setDriveMode('kinect');
                    setLiveTrackingStatus('idle');
                    setLivePoseData(null);
                  }}
                  style={{ marginRight: '6px' }}
                />
                Kinect 驱动（保留原方案，导入 Unity）
              </label>
            </div>

            <label
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '12px',
                color: '#d8c8a8',
                marginBottom: '8px',
                opacity: driveMode === 'camera' ? 1 : 0.55,
              }}
            >
              <input
                type="checkbox"
                checked={preferMocapCharacter}
                disabled={driveMode !== 'camera'}
                onChange={(e) => setPreferMocapCharacter(e.target.checked)}
              />
              实时跟随优先训练皮影（推荐）
            </label>
            <CameraCapture
              enableLiveTracking={driveMode === 'camera'}
              onVideoCapture={(videoBlob) => {}}
              onCaptureSuccess={(data) => {
                updateWorkbench({
                  captureSessionId: data.session_id,
                  captureFrames: data.frames ?? null,
                });
              }}
              onCaptureClear={() => {
                updateWorkbench({ captureSessionId: null, captureFrames: null });
              }}
              onCaptureError={(msg) => {
                console.warn('鍔ㄤ綔鎹曟崏涓婁紶澶辫触:', msg);
              }}
              onLivePose={(data) => {
                setLivePoseData(data?.puppet_pose || null);
              }}
              onLivePoseStateChange={(active, status) => {
                setLiveTrackingStatus(status || (active ? 'tracking' : 'idle'));
                if (driveMode === 'camera' && active && preferMocapCharacter) {
                  const preferred = allCharacters.find((c) => c.mocapPreferred);
                  const selected = workbenchState.selectedCharacter;
                  if (preferred && !selected?.mocapPreferred) {
                    updateWorkbench({ selectedCharacter: preferred });
                  }
                }
                if (!active) setLivePoseData(null);
              }}
              onLivePoseError={(msg) => {
                console.warn('瀹炴椂濮挎€佸け璐?', msg);
                setLiveTrackingStatus('error');
              }}
            />
            <p style={{ marginTop: '8px', fontSize: '12px', color: '#b8a88a' }}>
              {driveMode === 'camera'
                ? '当前为普通摄像头实时驱动模式：打开摄像头后可直接实时映射到皮影。'
                : '当前为 Kinect 方案：请在 Unity 打开 backend/Assets（PiYing + Kinect），可将 BVH 导入使用。'}
            </p>
            <p style={{ marginTop: '8px', fontSize: '12px', color: '#b8a88a' }}>
              瀹炴椂鏄犲皠鐘舵€侊細{liveTrackingStatus === 'tracking' ? '璺熼殢涓? : liveTrackingStatus === 'no-person' ? '鏈娴嬪埌浜轰綋' : liveTrackingStatus === 'error' ? '寮傚父' : '绌洪棽'}
            </p>
            {workbenchState.captureSessionId && (
              <p style={{ marginTop: '12px', fontSize: '12px', color: '#e8dcc5' }}>
                宸叉崟鎹夛紝鍏?{workbenchState.captureFrames ?? '鈥?} 甯с€?              </p>
            )}
            {workbenchState.captureSessionId && (
              <>
                <a
                  href={`${API_BASE}/api/download/${workbenchState.captureSessionId}?type=bvh`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-secondary"
                  style={{ display: 'inline-block', marginTop: '8px', textDecoration: 'none', textAlign: 'center' }}
                >
                  涓嬭浇 BVH
                </a>
                <p className="wb-desc" style={{ marginTop: '12px', fontSize: '12px', color: '#b8a88a' }}>
                  鏁板瓧浜?浣撴劅浜や簰璇蜂娇鐢?Unity 鐨奖浣撴劅鎴愬搧椤圭洰锛氱敤 Unity 鎵撳紑 <code style={{ background: 'rgba(0,0,0,0.2)', padding: '2px 6px' }}>backend/Assets</code>锛圥iYing + Kinect锛夛紝鍙皢 BVH 瀵煎叆 Unity 浣跨敤銆?                </p>
              </>
            )}
          </section>
        </div>

        {/* 涓垪锛氬姩浣滈瑙?+ 鍦烘櫙鍒嗘瀽鍏ュ彛 */}
        <div className="workbench-col">
          <section className="wb-card">
            <h3>鈶?/ 鈶?瑙掕壊鍔ㄤ綔棰勮 & 鍦烘櫙鍒嗘瀽</h3>
            <p className="wb-desc">
              浣跨敤褰撳墠鍓ф湰鍜屽姩浣滃簭鍒楋紝棰勮鐨奖瑙掕壊鍦ㄨ垶鍙颁笂鐨勮〃婕旀晥鏋滐紝涓哄悗缁満鏅垎鏋愬仛鍑嗗銆?            </p>

            <ScriptInput
              onSubmit={(text, actions) => {
                setActionSequence(actions);
                if (actions && actions.length) goToStepAtLeast(4);
              }}
            />

            <div style={{ marginTop: '16px' }}>
              <PuppetStage
                currentCharacter={workbenchState.selectedCharacter}
                actionSequence={actionSequence}
                playing={playing}
                lightOn={true}
                lightIntensity={0.6}
                backgroundScene={workbenchState.background}
                livePose={livePoseData}
              />
            </div>

            <Controls
              playing={playing}
              onTogglePlay={() => setPlaying(!playing)}
              onRestart={() => {
                setPlaying(false);
                setTimeout(() => setPlaying(true), 100);
              }}
              onNextAction={() => {}}
              lightOn={true}
              onToggleLight={() => {}}
              lightIntensity={0.6}
              onLightIntensityChange={() => {}}
              hasActions={actionSequence.length > 0}
            />

            <button
              className="btn-secondary"
              onClick={handleAnalyze}
              disabled={
                !workbenchState.selectedCharacter ||
                !workbenchState.selectedMotion
              }
              style={{ marginTop: '16px', width: '100%' }}
            >
              寮€濮嬪垎鏋愬綋鍓嶅満鏅?            </button>
          </section>

          {/* Step7 鍦烘櫙纭锛氬綋鍒嗘瀽鏈夌粨鏋滄椂鏄剧ず */}
          {workbenchState.analysis && (
            <section className="wb-card">
              <h3>鈶?鍦烘櫙鍐呭纭</h3>
              <p className="wb-desc">
                璇峰啀娆＄‘璁ゆ湰娈靛姩鐢荤殑鏍稿績淇℃伅锛岀‘璁ゅ悗灏嗙敓鎴愯棰戙€?              </p>
              <textarea
                className="wb-textarea"
                value={workbenchState.confirmScene}
                onChange={(e) =>
                  updateWorkbench({ confirmScene: e.target.value })
                }
                rows={4}
              />
              <button
                className="btn-primary"
                onClick={handleGenerateVideo}
                disabled={isGeneratingVideo}
                style={{ marginTop: '12px', width: '100%' }}
              >
                {isGeneratingVideo ? '姝ｅ湪鐢熸垚涓?..' : '纭骞剁敓鎴愯棰?}
              </button>
            </section>
          )}
        </div>

        {/* 鍙冲垪锛氬垎鏋愮粨鏋?+ 鏈€缁堣棰?*/}
        <div className="workbench-col">
          {/* 鍒嗘瀽缁撴灉 */}
          {workbenchState.analysis ? (
            <section className="wb-card">
              <h3>鈶?骞冲彴鍒嗘瀽缁撴灉</h3>
              <p className="wb-desc">{workbenchState.analysis.summary}</p>
              <ul className="wb-analysis-list">
                {workbenchState.analysis.highlights.map((h, idx) => (
                  <li key={idx}>{h}</li>
                ))}
              </ul>
            </section>
          ) : (
            <section className="wb-card">
              <h3>鈶?骞冲彴鍒嗘瀽缁撴灉</h3>
              <p className="wb-desc">瀹屾垚瑙掕壊銆佸姩浣滃拰鑳屾櫙閫夋嫨鍚庯紝鐐瑰嚮"寮€濮嬪垎鏋愬綋鍓嶅満鏅?鎸夐挳锛屽钩鍙板皢鑷姩鍒嗘瀽鍦烘櫙鐨勮妭濂忕粨鏋勩€佽鑹插叧绯诲拰鍦烘櫙鍖归厤搴︺€?/p>
              <div style={{ 
                padding: '20px', 
                textAlign: 'center', 
                color: '#e0d3b8', 
                fontSize: '13px',
                opacity: 0.7
              }}>
                绛夊緟鍦烘櫙鍒嗘瀽...
              </div>
            </section>
          )}

          {/* 瑙嗛缁撴灉 */}
          {isGeneratingVideo || workbenchState.video ? (
            <section className="wb-card">
              <h3>鈶?/ 鈶?瑙嗛棰勮涓庡厜褰甭烽煶涔愯皟鑺?/h3>

              {/* 鐢熸垚涓?*/}
              {isGeneratingVideo && (
                <div className="video-placeholder">
                  <div className="video-frame video-loading">
                    <div className="video-loading-spinner">
                      <div className="spinner-ring" />
                      <div className="spinner-ring" />
                      <div className="spinner-ring" />
                    </div>
                    <div className="video-loading-text">姝ｅ湪鐢熸垚瑙嗛...</div>
                    <div className="video-loading-progress">
                      <div
                        className="video-loading-progress-bar"
                        style={{ width: `${videoGenerationProgress}%` }}
                      />
                      <span className="video-loading-progress-text">
                        {Math.round(videoGenerationProgress)}%
                      </span>
                    </div>
                    <div className="video-loading-steps">
                      <div
                        className={
                          videoGenerationProgress > 20
                            ? 'step-done'
                            : 'step-pending'
                        }
                      >
                        鉁?鍔ㄤ綔搴忓垪瑙ｆ瀽
                      </div>
                      <div
                        className={
                          videoGenerationProgress > 50
                            ? 'step-done'
                            : 'step-pending'
                        }
                      >
                        鉁?瑙掕壊涓庡満鏅悎鎴?                      </div>
                      <div
                        className={
                          videoGenerationProgress > 80
                            ? 'step-done'
                            : 'step-pending'
                        }
                      >
                        {videoGenerationProgress > 80 ? '鉁? : '鈼?} 瑙嗛娓叉煋涓?..
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* 宸茬敓鎴愯棰?*/}
              {!isGeneratingVideo && workbenchState.video && (
                <div className="video-placeholder">
                  <div className="video-frame video-ready">
                    <video
                      src={workbenchState.video.url}
                      controls
                      autoPlay
                      loop
                      className="video-player"
                      style={{
                        width: '100%',
                        height: '100%',
                        objectFit: 'contain',
                        borderRadius: '12px',
                      }}
                    >
                      鎮ㄧ殑娴忚鍣ㄤ笉鏀寔瑙嗛鎾斁
                    </video>
                    <div className="video-title-overlay">
                      {workbenchState.video.title}
                    </div>
                  </div>
                </div>
              )}

              <div className="video-controls">
                <label className="video-control-item">
                  <span>鍏夊奖寮哄害锛?/span>
                  <input
                    type="range"
                    min={0}
                    max={1}
                    step={0.1}
                    value={videoOptions.lighting}
                    onChange={(e) =>
                      updateWorkbench({
                        videoOptions: {
                          ...videoOptions,
                          lighting: Number(e.target.value),
                        },
                      })
                    }
                  />
                  <span>{Math.round(videoOptions.lighting * 100)}%</span>
                </label>
                <label className="video-control-item">
                  <input
                    type="checkbox"
                    checked={videoOptions.useLibraryMusic}
                    onChange={(e) =>
                      updateWorkbench({
                        videoOptions: {
                          ...videoOptions,
                          useLibraryMusic: e.target.checked,
                        },
                      })
                    }
                  />
                  <span>浣跨敤璧勬簮搴撻厤涔?/span>
                </label>
              </div>

              <p className="wb-desc" style={{ marginTop: '12px', fontSize: '12px' }}>
                瀛楀箷鍖归厤涓庤棰戝悎鎴愬凡瀹屾垚锛屽彲鍦ㄦ璋冭妭鍏夊奖鍜岄煶涔愭晥鏋溿€?              </p>
            </section>
          ) : (
            <section className="wb-card">
              <h3>鈶?/ 鈶?瑙嗛棰勮涓庡厜褰甭烽煶涔愯皟鑺?/h3>
              <p className="wb-desc">瀹屾垚鍦烘櫙纭鍚庯紝鐐瑰嚮"纭骞剁敓鎴愯棰?鎸夐挳锛岀郴缁熷皢鑷姩鐢熸垚鐨奖鎴忚棰戙€傜敓鎴愬畬鎴愬悗鍙湪姝ら瑙堝苟璋冭妭鍏夊奖寮哄害鍜岄煶涔愭晥鏋溿€?/p>
              <div className="video-placeholder">
                <div className="video-frame">
                  <div className="video-icon">鎴?/div>
                  <div className="video-title">绛夊緟鐢熸垚瑙嗛</div>
                  <div className="video-note">璇峰厛瀹屾垚鍓嶉潰鐨勬楠ゅ苟纭鍦烘櫙</div>
                </div>
              </div>
              <div className="video-controls" style={{ opacity: 0.5, pointerEvents: 'none' }}>
                <label className="video-control-item">
                  <span>鍏夊奖寮哄害锛?/span>
                  <input
                    type="range"
                    min={0}
                    max={1}
                    step={0.1}
                    value={videoOptions.lighting}
                    disabled
                  />
                  <span>{Math.round(videoOptions.lighting * 100)}%</span>
                </label>
                <label className="video-control-item">
                  <input
                    type="checkbox"
                    checked={videoOptions.useLibraryMusic}
                    disabled
                  />
                  <span>浣跨敤璧勬簮搴撻厤涔?/span>
                </label>
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}

export default WorkbenchPage;
