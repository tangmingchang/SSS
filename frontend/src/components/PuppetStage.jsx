import { useEffect, useRef, useState } from 'react';
import './PuppetStage.css';

function PuppetStage({ 
  currentCharacter, 
  actionSequence, 
  playing, 
  lightOn, 
  lightIntensity,
  showStepOverlay = true,
  currentActionIndex: externalActionIndex,
  onActionIndexChange,
  backgroundScene = null,
  livePose = null,
}) {
  const stageRef = useRef(null);
  const [currentActionIndex, setCurrentActionIndex] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);
  const [characterPosition, setCharacterPosition] = useState({ leftPercent: 50, topPercent: 55 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef({ x: 0, y: 0, left: 50, top: 55 });
  
  // 如果外部传入了currentActionIndex，使用外部的，否则使用内部的
  const activeActionIndex = externalActionIndex !== undefined ? externalActionIndex : currentActionIndex;
  
  // 更新动作索引的回调
  const updateActionIndex = (index) => {
    setCurrentActionIndex(index);
    if (onActionIndexChange) {
      onActionIndexChange(index);
    }
  };

  // 动作类名映射
  const actionClasses = {
    'attack': 'action-attack',
    'jump': 'action-jump',
    'walk': 'action-walk',
    'run': 'action-run',
    'defend': 'action-defend',
    'dance': 'action-dance',
    'sit': 'action-sit',
    'stand': 'action-stand',
    'wave': 'action-wave',
    'bow': 'action-bow',
    'point': 'action-point',
    'raise': 'action-raise',
    'lower': 'action-lower'
  };

  // 所有动作类名的数组（用于清理）
  const allActionClassNames = Object.values(actionClasses);
  const isLivePoseActive = !!livePose && (Number(livePose?.confidence) || 0) > 0.05;
  const bodyRotateDeg = isLivePoseActive ? Number(livePose?.bodyRotateDeg || 0) : 0;
  const leftArmRotateDeg = isLivePoseActive ? Number(livePose?.leftArmRotateDeg || 0) : 0;
  const rightArmRotateDeg = isLivePoseActive ? Number(livePose?.rightArmRotateDeg || 0) : 0;
  const leftLegRotateDeg = isLivePoseActive ? Number(livePose?.leftLegRotateDeg || 0) : 0;
  const rightLegRotateDeg = isLivePoseActive ? Number(livePose?.rightLegRotateDeg || 0) : 0;

  // 当动作序列更新或播放状态改变时，执行动画
  useEffect(() => {
    const stageEl = stageRef.current;
    if (!stageEl) return;

    if (isLivePoseActive) {
      updateActionIndex(0);
      setIsAnimating(false);
      stageEl.classList.remove(...allActionClassNames);
      return;
    }

    // 如果停止播放，顺便清掉所有动作类
    if (!playing || actionSequence.length === 0) {
      updateActionIndex(0);
      setIsAnimating(false);
      stageEl.classList.remove(...allActionClassNames);
      return;
    }

    setIsAnimating(true);
    let index = 0;

    function playNext() {
      if (index >= actionSequence.length) {
        setIsAnimating(false);
        updateActionIndex(0);
        stageEl.classList.remove(...allActionClassNames);
        return;
      }

      const action = actionSequence[index];
      updateActionIndex(index);

      // 移除之前的动作类（使用 values 而不是 keys）
      stageEl.classList.remove(...allActionClassNames);

      // 添加当前动作类
      if (actionClasses[action]) {
        stageEl.classList.add(actionClasses[action]);
      }

      // 根据动作类型设置持续时间
      const duration = getActionDuration(action);

      setTimeout(() => {
        stageEl.classList.remove(...allActionClassNames);
        index++;
        if (playing) {
          playNext();
        }
      }, duration);
    }

    playNext();
  }, [actionSequence, playing, isLivePoseActive]);

  useEffect(() => {
    if (!isLivePoseActive || isDragging) return;
    const left = Number(livePose?.centerXPercent);
    const top = Number(livePose?.centerYPercent);
    if (!Number.isFinite(left) || !Number.isFinite(top)) return;
    setCharacterPosition({
      leftPercent: Math.min(95, Math.max(5, left)),
      topPercent: Math.min(95, Math.max(5, top)),
    });
  }, [isLivePoseActive, livePose, isDragging]);

  // 获取动作持续时间（毫秒）
  function getActionDuration(action) {
    const durations = {
      'attack': 800,
      'jump': 1000,
      'walk': 600,
      'run': 500,
      'defend': 700,
      'dance': 1200,
      'sit': 800,
      'stand': 500,
      'wave': 600,
      'bow': 1000,
      'point': 500,
      'raise': 600,
      'lower': 600
    };
    return durations[action] || 800;
  }

  // 角色拖动：在舞台内任意位置拖拽
  const handlePuppetMouseDown = (e) => {
    if (!stageRef.current || e.button !== 0) return;
    const rect = stageRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width * 100;
    const y = (e.clientY - rect.top) / rect.height * 100;
    dragStartRef.current = { x, y, left: characterPosition.leftPercent, top: characterPosition.topPercent };
    setIsDragging(true);
  };
  useEffect(() => {
    if (!isDragging) return;
    const onMove = (e) => {
      if (!stageRef.current) return;
      const rect = stageRef.current.getBoundingClientRect();
      const dx = (e.clientX - rect.left) / rect.width * 100 - dragStartRef.current.x;
      const dy = (e.clientY - rect.top) / rect.height * 100 - dragStartRef.current.y;
      const left = Math.min(95, Math.max(5, dragStartRef.current.left + dx));
      const top = Math.min(95, Math.max(5, dragStartRef.current.top + dy));
      setCharacterPosition({ leftPercent: left, topPercent: top });
    };
    const onUp = () => setIsDragging(false);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [isDragging]);

  // 检查是否有图片（支持分层图片或完整图片）
  const hasImages = currentCharacter && currentCharacter.images && 
    (currentCharacter.images.head || currentCharacter.images.body || currentCharacter.images.full);
  
  const { images = {}, name } = currentCharacter || {};

  // 获取角色class（用于占位符配色）
  const roleClass = currentCharacter?.roleClass || '';

  // 背景场景样式
  const stageBackgroundStyle = backgroundScene?.url
    ? {
        backgroundImage: `url(${backgroundScene.url})`,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat',
      }
    : {};

  return (
    <div className={`stage ${isLivePoseActive ? 'live-pose-active' : ''}`} ref={stageRef} style={stageBackgroundStyle}>
      {/* 幕布半透明背景层 */}
      <div className="screen-layer"></div>
      {isLivePoseActive && (
        <div className="live-follow-indicator">实时动作映射中</div>
      )}
      
      {/* 皮影角色部件容器：可拖动定位 */}
      <div
        className={`puppet-container ${!hasImages ? `puppet-placeholder ${roleClass}` : ''} ${isDragging ? 'puppet-dragging' : ''}`}
        style={{
          position: 'absolute',
          left: `${characterPosition.leftPercent}%`,
          top: `${characterPosition.topPercent}%`,
          transform: 'translate(-50%, -50%)',
          cursor: isLivePoseActive ? 'default' : (isDragging ? 'grabbing' : 'grab'),
          userSelect: 'none',
          zIndex: 10,
        }}
        onMouseDown={isLivePoseActive ? undefined : handlePuppetMouseDown}
      >
        {hasImages ? (
          images.full ? (
            <img 
              src={images.full} 
              className="puppet-full-image" 
              alt={name || '皮影角色'}
              style={{ 
                display: 'block',
                maxWidth: '200px',
                maxHeight: '300px',
                objectFit: 'contain',
                filter: 'drop-shadow(0 0 10px rgba(0,0,0,0.8))',
                pointerEvents: 'none',
                transform: isLivePoseActive ? `rotate(${bodyRotateDeg}deg)` : undefined,
              }}
              onError={(e) => {
                e.target.style.display = 'none';
              }}
            />
          ) : (
            <>
              {images.head && (
                <img 
                  src={images.head} 
                  className="puppet-part head" 
                  alt="头部"
                  style={{ 
                    transformOrigin: 'center bottom',
                    zIndex: 10
                  }}
                  onError={(e) => {
                    e.target.style.display = 'none';
                  }}
                />
              )}
              {images.body && (
                <img 
                  src={images.body} 
                  className="puppet-part body" 
                  alt="身体"
                  style={{ 
                    transformOrigin: 'center top',
                    transform: isLivePoseActive ? `translateX(-50%) rotate(${bodyRotateDeg}deg)` : 'translateX(-50%)',
                    zIndex: 5
                  }}
                  onError={(e) => {
                    e.target.style.display = 'none';
                  }}
                />
              )}
              {images.leftArm && (
                <img 
                  src={images.leftArm} 
                  className="puppet-part left-arm" 
                  alt="左臂"
                  style={{ 
                    transformOrigin: 'top right',
                    transform: isLivePoseActive ? `rotate(${leftArmRotateDeg}deg)` : undefined,
                    zIndex: 6
                  }}
                  onError={(e) => {
                    e.target.style.display = 'none';
                  }}
                />
              )}
              {images.rightArm && (
                <img 
                  src={images.rightArm} 
                  className="puppet-part right-arm" 
                  alt="右臂"
                  style={{ 
                    transformOrigin: 'top left',
                    transform: isLivePoseActive ? `rotate(${rightArmRotateDeg}deg)` : undefined,
                    zIndex: 6
                  }}
                  onError={(e) => {
                    e.target.style.display = 'none';
                  }}
                />
              )}
              {images.leftLeg && (
                <img 
                  src={images.leftLeg} 
                  className="puppet-part left-leg" 
                  alt="左腿"
                  style={{ 
                    transformOrigin: 'top center',
                    transform: isLivePoseActive ? `rotate(${leftLegRotateDeg}deg)` : undefined,
                    zIndex: 4
                  }}
                  onError={(e) => {
                    e.target.style.display = 'none';
                  }}
                />
              )}
              {images.rightLeg && (
                <img 
                  src={images.rightLeg} 
                  className="puppet-part right-leg" 
                  alt="右腿"
                  style={{ 
                    transformOrigin: 'top center',
                    transform: isLivePoseActive ? `rotate(${rightLegRotateDeg}deg)` : undefined,
                    zIndex: 4
                  }}
                  onError={(e) => {
                    e.target.style.display = 'none';
                  }}
                />
              )}
            </>
          )
        ) : (
          <>
            <div className="puppet-part puppet-head"></div>
            <div className="puppet-part puppet-body" style={{ transform: isLivePoseActive ? `rotate(${bodyRotateDeg}deg)` : undefined }}></div>
            <div className="puppet-part puppet-arm-left" style={{ transform: isLivePoseActive ? `rotate(${leftArmRotateDeg}deg)` : undefined }}></div>
            <div className="puppet-part puppet-arm-right" style={{ transform: isLivePoseActive ? `rotate(${rightArmRotateDeg}deg)` : undefined }}></div>
            <div className="puppet-part puppet-leg puppet-leg-left" style={{ transform: isLivePoseActive ? `rotate(${leftLegRotateDeg}deg)` : undefined }}></div>
            <div className="puppet-part puppet-leg puppet-leg-right" style={{ transform: isLivePoseActive ? `rotate(${rightLegRotateDeg}deg)` : undefined }}></div>
          </>
        )}
      </div>

      {/* 灯光效果层 */}
      <div 
        className="light-overlay" 
        style={{ 
          opacity: lightOn ? lightIntensity : 0 
        }}
      ></div>

      {/* 动作指示器 */}
      {isAnimating && actionSequence.length > 0 && !isLivePoseActive && (
        <div className="action-indicator">
          <span>动作 {currentActionIndex + 1} / {actionSequence.length}</span>
        </div>
      )}
    </div>
  );
}

export default PuppetStage;
