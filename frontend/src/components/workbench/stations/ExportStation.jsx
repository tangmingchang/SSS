import React from 'react';
import html2canvas from 'html2canvas';
import { useWorkbenchStore } from '../../../stores/workbenchStore';
import { API_BASE } from '../../../utils/api';
import { IconExport, IconError } from '../../shared/Icons';
import { addWork } from '../../../services/userWorksApi';
import { getToken } from '../../../services/authService';
import './StationCommon.css';

/**
 * Export Station（交付站）
 * 导出视频/BVH/脚本包、完成确认
 */
export default function ExportStation() {
  const { orderTicket, stage, updateTask, markStationCompleted, stageCanvasEl, setExportedVideoUrl } = useWorkbenchStore();
  const [exportFormat, setExportFormat] = React.useState('audio');
  const [exportResult, setExportResult] = React.useState(null);
  /** 视频导出时使用的场景图（舞台截图），优先于 orderTicket 的背景/角色 */
  const [sceneFrameFile, setSceneFrameFile] = React.useState(null);
  const sceneFrameInputRef = React.useRef(null);
  /** 视频可调参数：分辨率、码率（用于调视频画质） */
  const [videoResolution, setVideoResolution] = React.useState('auto'); // auto | 1280x720 | 1920x1080
  const [videoBitrate, setVideoBitrate] = React.useState(''); // '' | 2M | 4M
  /** 保存到作品集：标题、提交状态 */
  const [saveToPortfolioTitle, setSaveToPortfolioTitle] = React.useState('');
  const [saveToPortfolioStatus, setSaveToPortfolioStatus] = React.useState(null); // null | 'saving' | 'success' | 'error'
  const [saveToPortfolioMessage, setSaveToPortfolioMessage] = React.useState('');

  /** 音频：剧本台词 TTS + 背景音乐混音（调用后端流水线，约 30 秒请勿关闭页面） */
  const handleExportPerformance = async () => {
    if (!orderTicket.script || !orderTicket.script.scenes?.length) {
      updateTask('videoGeneration', { status: 'error', error: '请先生成剧本（含台词）', retryable: false });
      return;
    }
    updateTask('videoGeneration', { status: 'running', message: '正在生成念白与混音，约需 30 秒，请勿关闭页面...' });
    try {
      const form = new FormData();
      form.append('script', JSON.stringify(orderTicket.script));
      const musicUrl = orderTicket.videoOptions?.backgroundMusicUrl;
      if (musicUrl && musicUrl.startsWith('blob:')) {
        const res = await fetch(musicUrl);
        const blob = await res.blob();
        const name = orderTicket.videoOptions?.backgroundMusicName || 'music.mp3';
        form.append('music', blob, name);
      }
      const fetchOpts = { method: 'POST', body: form };
      if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
        fetchOpts.signal = AbortSignal.timeout(120000); // 120 秒超时
      }
      const r = await fetch(`${API_BASE}/api/export/performance`, fetchOpts);
      const data = await r.json().catch(() => ({}));
      if (!r.ok || !data.success) {
        throw new Error(data.error || '导出失败');
      }
      let audioUrl = data.audio_url || '';
      if (audioUrl && !audioUrl.startsWith('http')) {
        audioUrl = `${API_BASE}${audioUrl.startsWith('/') ? '' : '/'}${audioUrl}`;
      }
      updateTask('videoGeneration', { status: 'success' });
      setExportResult({ type: 'audio', url: audioUrl });
      markStationCompleted('export');
    } catch (err) {
      const msg = (err.name === 'TimeoutError' || err.name === 'AbortError') ? '请求超时，请重试并保持页面打开（约 30 秒）。' : (err.message || '导出失败');
      updateTask('videoGeneration', { status: 'error', error: msg, retryable: true });
    }
  };

  /** 阶段三：念白+音乐合成后与场景图合成 MP4（静态图+音频）；自动截取当前舞台作为场景图 */
  const handleExportVideo = async () => {
    if (!orderTicket.script || !orderTicket.script.scenes?.length) {
      updateTask('videoGeneration', { status: 'error', error: '请先生成剧本（含台词）', retryable: false });
      return;
    }
    updateTask('videoGeneration', { status: 'running', message: '正在截取舞台画面...' });
    try {
      const form = new FormData();
      form.append('script', JSON.stringify(orderTicket.script));
      // 优先使用手动上传的场景图；否则自动截取当前舞台
      if (sceneFrameFile && sceneFrameFile instanceof File) {
        form.append('frame', sceneFrameFile, sceneFrameFile.name || 'scene.png');
      } else if (stageCanvasEl && typeof stageCanvasEl.getBoundingClientRect === 'function') {
        try {
          const canvas = await html2canvas(stageCanvasEl, { useCORS: true, allowTaint: true, scale: 1, logging: false });
          const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
          if (blob) form.append('frame', blob, 'stage.png');
        } catch (e) {
          console.warn('[Export] 舞台自动截图失败', e);
        }
      }
      updateTask('videoGeneration', { status: 'running', message: '正在生成念白、混音与视频，约需 1～2 分钟，请勿关闭页面...' });
      const musicUrl = orderTicket.videoOptions?.backgroundMusicUrl;
      if (musicUrl && musicUrl.startsWith('blob:')) {
        const res = await fetch(musicUrl);
        const blob = await res.blob();
        const name = orderTicket.videoOptions?.backgroundMusicName || 'music.mp3';
        form.append('music', blob, name);
      }
      const bg = orderTicket.background;
      const bgUrl = bg?.url || bg?.thumbnail;
      if (bgUrl && (bgUrl.startsWith('blob:') || bgUrl.startsWith('http'))) {
        try {
          const res = await fetch(bgUrl);
          const blob = await res.blob();
          const ext = /\.(jpe?g|png|gif|webp)$/i.test(bg.name || '') ? (bg.name || '').split('.').pop() : 'png';
          form.append('background', blob, `background.${ext}`);
        } catch (_) { /* 忽略 */ }
      }
      const char = orderTicket.character;
      const charUrl = char?.image_url || char?.thumbnail;
      if (charUrl && (charUrl.startsWith('blob:') || charUrl.startsWith('http'))) {
        try {
          const res = await fetch(charUrl);
          const blob = await res.blob();
          const ext = /\.(jpe?g|png|gif|webp)$/i.test(char.name || '') ? (char.name || '').split('.').pop() : 'png';
          form.append('character', blob, `character.${ext}`);
        } catch (_) { /* 忽略 */ }
      }
      if (Array.isArray(orderTicket.actionSequence) && orderTicket.actionSequence.length > 0) {
        form.append('action_sequence', JSON.stringify(orderTicket.actionSequence));
      }
      if (videoResolution && videoResolution !== 'auto') {
        const [w, h] = videoResolution.split('x').map(Number);
        if (!isNaN(w)) form.append('video_width', String(w));
        if (!isNaN(h)) form.append('video_height', String(h));
      }
      if (videoBitrate && videoBitrate.trim()) {
        form.append('video_bitrate', videoBitrate.trim());
      }
      const fetchOpts = { method: 'POST', body: form };
      if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
        fetchOpts.signal = AbortSignal.timeout(180000);
      }
      const r = await fetch(`${API_BASE}/api/export/video`, fetchOpts);
      const data = await r.json().catch(() => ({}));
      if (!r.ok || !data.success) {
        throw new Error(data.error || '视频导出失败');
      }
      let videoUrl = data.video_url || '';
      if (videoUrl && !videoUrl.startsWith('http')) {
        videoUrl = `${API_BASE}${videoUrl.startsWith('/') ? '' : '/'}${videoUrl}`;
      }
      updateTask('videoGeneration', { status: 'success' });
      setExportResult({ type: 'video', url: videoUrl });
      setExportedVideoUrl(videoUrl);
      markStationCompleted('export');
      // 已登录时自动保存到作品集
      if (getToken()) {
        const title = (orderTicket?.theme || '').trim() || ('皮影作品 ' + new Date().toLocaleString('zh-CN', { dateStyle: 'short', timeStyle: 'short' }));
        let videoUrlForApi = videoUrl;
        if (videoUrlForApi.startsWith(API_BASE)) {
          const path = videoUrlForApi.slice(API_BASE.length);
          videoUrlForApi = path.startsWith('/') ? path : '/' + path;
        }
        setSaveToPortfolioTitle(title);
        addWork({ title, video_url: videoUrlForApi })
          .then(() => {
            setSaveToPortfolioStatus('success');
            setSaveToPortfolioMessage('已自动保存到作品集');
          })
          .catch(() => {
            setSaveToPortfolioStatus('error');
            setSaveToPortfolioMessage('自动保存失败，可点击下方按钮重试');
          });
      }
    } catch (err) {
      const msg = (err.name === 'TimeoutError' || err.name === 'AbortError') ? '请求超时，请重试并保持页面打开。' : (err.message || '视频导出失败');
      updateTask('videoGeneration', { status: 'error', error: msg, retryable: true });
    }
  };

  const handleExportBVH = async () => {
    // BVH导出逻辑
    console.log('导出BVH...');
  };

  const handleExportScript = () => {
    // 脚本包导出：亮度/灯光/字幕以左侧调参（stage）为准
    const videoOptions = {
      ...orderTicket.videoOptions,
      brightness: stage.brightness ?? 0.8,
      lighting: stage.lighting ?? 0.7,
      subtitles: stage.subtitles ?? false,
    };
    const scriptData = {
      theme: orderTicket.theme,
      script: orderTicket.script,
      character: orderTicket.character,
      background: orderTicket.background,
      actionSequence: orderTicket.actionSequence,
      videoOptions,
    };
    const blob = new Blob([JSON.stringify(scriptData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `piying-script-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const task = useWorkbenchStore((state) => state.tasks.videoGeneration);

  React.useEffect(() => {
    if (exportResult?.type === 'video') {
      const theme = orderTicket?.theme?.trim();
      const defaultTitle = theme || '皮影作品 ' + new Date().toLocaleString('zh-CN', { dateStyle: 'short', timeStyle: 'short' });
      setSaveToPortfolioTitle(defaultTitle);
      setSaveToPortfolioStatus(null);
      setSaveToPortfolioMessage('');
    }
  }, [exportResult?.type, exportResult?.url, orderTicket?.theme]);

  const handleSaveToPortfolio = async () => {
    if (!exportResult?.url || exportResult?.type !== 'video') return;
    if (!getToken()) {
      setSaveToPortfolioStatus('error');
      setSaveToPortfolioMessage('请先登录后再保存到作品集');
      return;
    }
    setSaveToPortfolioStatus('saving');
    setSaveToPortfolioMessage('');
    try {
      let videoUrl = exportResult.url;
      if (videoUrl.startsWith(API_BASE)) {
        const path = videoUrl.slice(API_BASE.length);
        videoUrl = path.startsWith('/') ? path : '/' + path;
      }
      await addWork({ title: saveToPortfolioTitle.trim() || undefined, video_url: videoUrl });
      setSaveToPortfolioStatus('success');
      setSaveToPortfolioMessage('已保存到作品集');
    } catch (e) {
      setSaveToPortfolioStatus('error');
      setSaveToPortfolioMessage(e.message || '保存失败');
    }
  };

  return (
    <div className="station-content export-station">
      <h3 className="station-title">
        <IconExport size={18} />
        <span>交付站</span>
      </h3>
      <p className="station-desc">
        导出演出结果：音频、图生视频、BVH 或脚本包
      </p>

      <div className="export-options">
        <h4>导出格式</h4>
        <div className="format-selector">
          <button
            className={exportFormat === 'audio' ? 'active' : ''}
            onClick={() => setExportFormat('audio')}
          >
            音频
          </button>
          <button
            className={exportFormat === 'video' ? 'active' : ''}
            onClick={() => setExportFormat('video')}
          >
            图生视频
          </button>
          <button
            className={exportFormat === 'bvh' ? 'active' : ''}
            onClick={() => setExportFormat('bvh')}
          >
            BVH
          </button>
          <button
            className={exportFormat === 'script' ? 'active' : ''}
            onClick={() => setExportFormat('script')}
          >
            脚本包
          </button>
        </div>
      </div>

        {exportFormat === 'video' && (
        <>
          <div className="export-scene-frame" style={{ marginBottom: 12 }}>
            <label className="stage-hint" style={{ display: 'block', marginBottom: 6 }}>
              上传一张你截好的整幅舞台画面，作为「图生视频」的底图；如果不上传，将尝试使用当前舞台或默认场景图。
            </label>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <input
                ref={sceneFrameInputRef}
                type="file"
                accept="image/png,image/jpeg,image/jpg,image/webp"
                style={{ display: 'none' }}
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  setSceneFrameFile(f || null);
                }}
              />
              <button
                type="button"
                className="btn-secondary"
                onClick={() => sceneFrameInputRef.current?.click()}
              >
                {sceneFrameFile ? `已选：${sceneFrameFile.name}` : '选择场景图（覆盖）'}
              </button>
              {sceneFrameFile && (
                <button type="button" className="btn-secondary" onClick={() => { setSceneFrameFile(null); if (sceneFrameInputRef.current) sceneFrameInputRef.current.value = ''; }}>
                  清除
                </button>
              )}
            </div>
          </div>
          <div className="export-video-params" style={{ marginBottom: 12, display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 12 }}>
            <label className="stage-hint" style={{ color: '#e8dcc5', fontSize: 12 }}>分辨率：</label>
            <select
              className="wb-select"
              value={videoResolution}
              onChange={(e) => setVideoResolution(e.target.value)}
              style={{ minWidth: 120 }}
            >
              <option value="auto">自动（与画面一致）</option>
              <option value="1280x720">1280×720</option>
              <option value="1920x1080">1920×1080</option>
            </select>
            <label className="stage-hint" style={{ color: '#e8dcc5', fontSize: 12 }}>码率：</label>
            <select
              className="wb-select"
              value={videoBitrate}
              onChange={(e) => setVideoBitrate(e.target.value)}
              style={{ minWidth: 90 }}
            >
              <option value="">自动</option>
              <option value="2M">2 Mbps</option>
              <option value="4M">4 Mbps</option>
            </select>
          </div>
        </>
      )}

      <div className="export-actions">
        {exportFormat === 'audio' && (
          <button
            className="btn-primary"
            onClick={handleExportPerformance}
            disabled={task.status === 'running'}
          >
            {task.status === 'running' ? '导出中，请稍候...' : '导出音频'}
          </button>
        )}
        {exportFormat === 'video' && (
          <button
            className="btn-primary"
            onClick={handleExportVideo}
            disabled={task.status === 'running'}
          >
            {task.status === 'running' ? '导出中...' : '导出视频'}
          </button>
        )}
        {exportFormat === 'bvh' && (
          <button className="btn-primary" onClick={handleExportBVH}>
            导出BVH
          </button>
        )}
        {exportFormat === 'script' && (
          <button className="btn-primary" onClick={handleExportScript}>
            导出脚本包
          </button>
        )}
      </div>

      {task.status === 'running' && (
        <p className="stage-hint" style={{ marginTop: 8 }}>{task.message || '处理中...'}</p>
      )}

      {task.status === 'error' && (
        <div className="station-error">
          <span>
            <IconError size={14} />
            {task.error}
          </span>
          <button onClick={() => { if (exportFormat === 'audio') handleExportPerformance(); else if (exportFormat === 'video') handleExportVideo(); }}>重试</button>
        </div>
      )}

      {exportResult && (
        <div className="export-result">
          <h4>导出成功！</h4>
          {exportResult.type === 'audio' && (
            <>
              <audio src={exportResult.url} controls style={{ maxWidth: '100%', marginBottom: 8 }} />
              <p className="stage-hint">念白由剧本台词生成，可单独下载音频。</p>
            </>
          )}
          {exportResult.type === 'video' && (
            <>
              <video
                src={exportResult.url}
                controls
                style={{ maxWidth: '100%', marginBottom: 8 }}
                onDoubleClick={(e) => {
                  const el = e.currentTarget;
                  if (el.requestFullscreen) el.requestFullscreen();
                }}
              />
              <p className="stage-hint">由图生视频服务生成的新视频，双击播放器可全屏观看。</p>
              <div className="save-to-portfolio" style={{ marginTop: 12 }}>
                <label className="stage-hint" style={{ display: 'block', marginBottom: 6 }}>保存到作品集</label>
                <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8 }}>
                  <input
                    type="text"
                    className="wb-input"
                    value={saveToPortfolioTitle}
                    onChange={(e) => setSaveToPortfolioTitle(e.target.value)}
                    placeholder="作品标题"
                    style={{ flex: '1 1 200px', minWidth: 120 }}
                  />
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={handleSaveToPortfolio}
                    disabled={saveToPortfolioStatus === 'saving'}
                  >
                    {saveToPortfolioStatus === 'saving' ? '保存中…' : '保存到作品集'}
                  </button>
                </div>
                {saveToPortfolioStatus === 'success' && <p className="stage-hint" style={{ color: '#8f8', marginTop: 6 }}>{saveToPortfolioMessage}</p>}
                {saveToPortfolioStatus === 'error' && <p className="stage-hint" style={{ color: '#f88', marginTop: 6 }}>{saveToPortfolioMessage}</p>}
              </div>
            </>
          )}
          <a href={exportResult.url} download>下载文件</a>
        </div>
      )}
    </div>
  );
}
