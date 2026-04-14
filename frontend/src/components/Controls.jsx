import './Controls.css';

function Controls({ 
  playing, 
  onTogglePlay, 
  onRestart, 
  onNextAction,
  lightOn, 
  onToggleLight,
  lightIntensity,
  onLightIntensityChange,
  hasActions,
  showStepOverlay = true,
  onStepOverlayToggle
}) {
  return (
    <div className="controls">
      <div className="controls-header">
        <h4>
          <span className="icon">控</span>
          控制面板
        </h4>
      </div>
      
      <div className="controls-content">
        {/* 播放控制 */}
        <div className="control-group">
          <div className="control-label">播放控制</div>
          <div className="play-controls">
            <button 
              onClick={onTogglePlay}
              className="control-btn play-btn"
              disabled={!hasActions}
            >
              <span className="btn-icon">
                {playing ? '停' : '播'}
              </span>
              {playing ? '暂停' : '播放'}
            </button>
            <button 
              onClick={onRestart}
              className="control-btn restart-btn"
              disabled={!hasActions}
            >
              <span className="btn-icon">复</span>
              重播
            </button>
            <button 
              onClick={onNextAction}
              className="control-btn next-btn"
              disabled={!hasActions || playing}
            >
              <span className="btn-icon">下</span>
              下一动作
            </button>
          </div>
        </div>

        {/* 灯光控制 */}
        <div className="control-group">
          <div className="control-label">灯光效果</div>
          <div className="light-controls">
            <button 
              onClick={onToggleLight}
              className={`control-btn light-btn ${lightOn ? 'active' : ''}`}
            >
              <span className="btn-icon">灯</span>
              {lightOn ? '关灯' : '开灯'}
            </button>
            
            {lightOn && (
              <div className="light-slider-container">
                <label className="slider-label">亮度</label>
                <input
                  type="range"
                  min="0.1"
                  max="1"
                  step="0.1"
                  value={lightIntensity}
                  onChange={(e) => onLightIntensityChange(parseFloat(e.target.value))}
                  className="light-slider"
                />
                <span className="slider-value">{Math.round(lightIntensity * 100)}%</span>
              </div>
            )}
          </div>
        </div>

        {/* 教学字幕控制 */}
        {onStepOverlayToggle && (
          <div className="control-group">
            <div className="control-label">教学辅助</div>
            <button
              className={`control-btn ${showStepOverlay ? 'active' : ''}`}
              onClick={() => onStepOverlayToggle(!showStepOverlay)}
            >
              <span className="btn-icon">字</span>
              {showStepOverlay ? '隐藏字幕' : '显示字幕'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default Controls;

