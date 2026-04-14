import React, { useRef, useState, useCallback } from 'react';
import { useWorkbenchStore } from '../../stores/workbenchStore';
import './StageVideoPreview.css';

/**
 * 导出视频成功后，在中央舞台区以与舞台同尺寸播放该视频，下方为播放/倍速控制
 */
export default function StageVideoPreview({ videoUrl }) {
  const videoRef = useRef(null);
  const setExportedVideoUrl = useWorkbenchStore((s) => s.setExportedVideoUrl);
  const [playing, setPlaying] = useState(false);
  const [playbackRate, setPlaybackRate] = useState(1);

  const togglePlay = useCallback(() => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) {
      v.play();
      setPlaying(true);
    } else {
      v.pause();
      setPlaying(false);
    }
  }, []);

  const onPlay = useCallback(() => setPlaying(true), []);
  const onPause = useCallback(() => setPlaying(false), []);

  const handleSpeed = useCallback((rate) => {
    setPlaybackRate(rate);
    if (videoRef.current) videoRef.current.playbackRate = rate;
  }, []);

  const handleBackToStage = useCallback(() => {
    setExportedVideoUrl(null);
  }, [setExportedVideoUrl]);

  if (!videoUrl) return null;

  return (
    <div className="stage-container stage-video-preview">
      <div className="stage-canvas stage-video-canvas">
        <video
          ref={videoRef}
          src={videoUrl}
          className="stage-video-element"
          controls={false}
          playsInline
          onPlay={onPlay}
          onPause={onPause}
          onEnded={() => setPlaying(false)}
        />
        <button
          type="button"
          className="stage-video-back-btn"
          onClick={handleBackToStage}
          title="返回舞台"
        >
          返回舞台
        </button>
      </div>
      <div className="stage-video-controls">
        <button
          type="button"
          className="stage-video-ctrl-btn"
          onClick={togglePlay}
          aria-label={playing ? '暂停' : '播放'}
        >
          {playing ? '暂停' : '播放'}
        </button>
        <span className="stage-video-speed-label">倍速</span>
        <div className="stage-video-speed-btns">
          {[0.5, 0.75, 1, 1.25, 1.5].map((r) => (
            <button
              key={r}
              type="button"
              className={'stage-video-speed-btn' + (playbackRate === r ? ' active' : '')}
              onClick={() => handleSpeed(r)}
            >
              {r === 1 ? '1x' : r}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
