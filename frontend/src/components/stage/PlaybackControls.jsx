import React from 'react';
import { useWorkbenchStore } from '../../stores/workbenchStore';
import { IconPlay, IconPause } from '../shared/Icons';
import './PlaybackControls.css';

/**
 * 播放控制组件
 */
export default function PlaybackControls() {
  const { stage, updateStage } = useWorkbenchStore();
  const { playback } = stage;

  const handlePlay = () => {
    updateStage({
      playback: { ...playback, playing: true }
    });
  };

  const handlePause = () => {
    updateStage({
      playback: { ...playback, playing: false }
    });
  };

  const handleSeek = (e) => {
    const newTime = parseFloat(e.target.value);
    updateStage({
      playback: { ...playback, currentTime: newTime }
    });
  };

  const handleSpeedChange = (e) => {
    const newSpeed = parseFloat(e.target.value);
    updateStage({
      playback: { ...playback, speed: newSpeed }
    });
  };

  return (
    <div className="playback-controls">
      <div className="controls-main">
        <button
          className="play-pause-btn"
          onClick={playback.playing ? handlePause : handlePlay}
        >
          {playback.playing ? <IconPause size={20} /> : <IconPlay size={20} />}
        </button>

        <div className="time-display">
          <span>{formatTime(playback.currentTime)}</span>
          <span>/</span>
          <span>{formatTime(playback.duration || 0)}</span>
        </div>

        <input
          type="range"
          className="progress-slider"
          min="0"
          max={playback.duration || 100}
          value={playback.currentTime}
          onChange={handleSeek}
        />

        <div className="speed-control">
          <span>速度:</span>
          <input
            type="range"
            min="0.5"
            max="2"
            step="0.1"
            value={playback.speed}
            onChange={handleSpeedChange}
          />
          <span>{playback.speed}x</span>
        </div>
      </div>
    </div>
  );
}

function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}
