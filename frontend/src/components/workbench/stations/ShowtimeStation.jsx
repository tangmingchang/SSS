import React, { useRef } from 'react';
import { useWorkbenchStore } from '../../../stores/workbenchStore';
import { IconShowtime } from '../../shared/Icons';
import './StationCommon.css';

/**
 * 从剧本中收集所有台词（按场景），仅台词部分，不含场景描述/动作/情绪等
 */
function getScriptLines(script) {
  if (!script || !Array.isArray(script.scenes)) return [];
  return script.scenes.map((s) => ({
    sceneNumber: s.scene_number,
    lines: Array.isArray(s.lines) ? s.lines : [],
  }));
}

/**
 * Showtime Station（演出站）
 * 添加音乐、剧本台词、播放速度
 */
export default function ShowtimeStation() {
  const { orderTicket, updateOrderTicket, markStationCompleted, goToNextStation, updateStage } = useWorkbenchStore();
  const audioRef = useRef(null);

  const handleMusicFile = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    updateOrderTicket({
      videoOptions: {
        ...orderTicket.videoOptions,
        backgroundMusicUrl: url,
        backgroundMusicName: file.name,
      }
    });
    e.target.value = '';
  };

  const clearMusic = () => {
    const url = orderTicket.videoOptions?.backgroundMusicUrl;
    if (url && url.startsWith('blob:')) URL.revokeObjectURL(url);
    updateOrderTicket({
      videoOptions: {
        ...orderTicket.videoOptions,
        backgroundMusicUrl: null,
        backgroundMusicName: null,
      }
    });
  };

  const handleConfirmScene = () => {
    markStationCompleted('showtime');
    goToNextStation();
  };

  const scriptLines = getScriptLines(orderTicket.script);
  const hasLines = scriptLines.some((s) => s.lines.length > 0);
  const allLinesText = hasLines
    ? scriptLines.flatMap((s) => s.lines).filter((line) => typeof line === 'string' && line.trim()).join('\n')
    : '';

  const handleApplySubtitles = () => {
    if (!allLinesText) return;
    updateStage({
      subtitles: true,
      subtitleText: allLinesText,
    });
  };
  const musicUrl = orderTicket.videoOptions?.backgroundMusicUrl;
  const musicName = orderTicket.videoOptions?.backgroundMusicName;

  return (
    <div className="station-content showtime-station">
      <h3 className="station-title">
        <IconShowtime size={18} />
        <span>演出站</span>
      </h3>
      <p className="station-desc">
        添加背景音乐、查看剧本台词与播放速度；亮度/灯光/字幕在左侧调参中设置
      </p>

      {/* 添加音乐 */}
      <div className="showtime-section">
        <h4>添加音乐</h4>
        <p className="stage-hint" style={{ marginBottom: 8 }}>
          上传背景音乐（MP3/WAV 等），与下方剧本台词搭配，营造唱戏氛围。
        </p>
        <div className="showtime-music-row">
          <label className="btn-secondary" style={{ marginRight: 8 }}>
            选择音乐文件
            <input
              type="file"
              accept="audio/mpeg,audio/wav,audio/ogg,audio/*"
              onChange={handleMusicFile}
              style={{ display: 'none' }}
            />
          </label>
          {musicUrl && (
            <>
              <span className="showtime-music-name" title={musicName}>{musicName || '已选音乐'}</span>
              <button type="button" className="btn-secondary" onClick={clearMusic}>移除</button>
              <audio ref={audioRef} src={musicUrl} controls style={{ maxWidth: '100%', marginTop: 8 }} />
            </>
          )}
        </div>
      </div>

      {/* 剧本台词（来自前面生成的剧本） */}
      <div className="showtime-section">
        <h4>剧本台词</h4>
        <p className="stage-hint" style={{ marginBottom: 8 }}>
          以下为剧本中生成的念词，配合背景音乐即形成「有背景音乐有念词」的唱戏效果。
        </p>
        {orderTicket.script && hasLines ? (
          <>
            <div className="showtime-lines">
              {scriptLines.map((block) => (
                <div key={block.sceneNumber} className="showtime-lines-block">
                  <ul className="showtime-lines-list">
                    {block.lines.map((line, i) => (
                      <li key={i}>{line}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
            <div style={{ marginTop: 8 }}>
              <button
                type="button"
                className="btn-secondary"
                onClick={handleApplySubtitles}
                disabled={!allLinesText}
              >
                确认台词并显示在舞台底部
              </button>
            </div>
          </>
        ) : (
          <p className="stage-hint">暂无台词。请先在点单站生成剧本（剧本中会包含台词）。</p>
        )}
      </div>

      <p className="stage-hint" style={{ marginTop: 8, marginBottom: 12 }}>
        亮度、灯光、字幕请在左侧「调参」中设置，舞台会实时预览，导出时将使用相同参数。
      </p>

      <div className="render-options-section">
        <h4>播放与导出</h4>
        <div className="option-group">
          <label>
            播放速度：
            <input
              type="range"
              min="0.5"
              max="2"
              step="0.1"
              value={orderTicket.videoOptions.speed}
              onChange={(e) => updateOrderTicket({
                videoOptions: { ...orderTicket.videoOptions, speed: parseFloat(e.target.value) }
              })}
            />
            {orderTicket.videoOptions.speed}x
          </label>
        </div>
      </div>

      <div className="station-actions">
        <button
          className="btn-primary"
          onClick={handleConfirmScene}
        >
          确认并进入导出
        </button>
        <button
          className="btn-secondary"
          onClick={goToNextStation}
        >
          下一站：导出 →
        </button>
      </div>
    </div>
  );
}
