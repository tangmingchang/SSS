import React, { useState, useRef, useCallback } from 'react';
import { resolveImageUrl } from '../../utils/api';
import './StageCharacters.css';

/**
 * 舞台角色层组件：支持选中、拖动、删除人物
 * 当前版本为整图驱动，不做任何图层切分
 */
export default function StageCharacters({ characters, livePose = null, liveTargetCharacterId = '', onRemoveCharacter }) {
  const containerRef = useRef(null);
  const liveAnchorRef = useRef({});
  const [positions, setPositions] = useState({});
  const [scales, setScales] = useState({});
  const [selectedId, setSelectedId] = useState(null);
  const [draggingId, setDraggingId] = useState(null);
  const dragStart = useRef({ x: 0, y: 0, left: 0, bottom: 0 });
  const dragPendingId = useRef(null);

  const DRAG_THRESHOLD_PX = 6;
  const SCALE_MIN = 0.4;
  const SCALE_MAX = 2;
  const SCALE_STEP = 0.15;
  const BODY_GAIN = 1.1;
  const MIN_ROTATE_DEADZONE = 2.2;
  const isLivePoseActive = !!livePose && (Number(livePose?.confidence) || 0) > 0.05;

  const clamp = useCallback((v, min, max) => {
    return Math.max(min, Math.min(max, v));
  }, []);

  const withGain = useCallback((v, gain, min, max) => {
    const n = Number(v) || 0;
    const g = n * gain;
    return Math.abs(g) < MIN_ROTATE_DEADZONE ? 0 : clamp(g, min, max);
  }, [clamp]);

  const getPos = useCallback((char, index) => {
    const id = char.id ?? `char-${index}`;
    if (positions[id]) return positions[id];
    return { left: 20 + index * 30, bottom: 20 };
  }, [positions]);

  const getScale = useCallback((id) => scales[id] ?? 1, [scales]);

  React.useEffect(() => {
    if (!isLivePoseActive || !characters || characters.length === 0) return;
    if (draggingId) return;

    const hasManualTarget = !!liveTargetCharacterId && characters.some((c, i) => (c.id ?? `char-${i}`) === liveTargetCharacterId);
    const hasSelected = !!selectedId && characters.some((c, i) => (c.id ?? `char-${i}`) === selectedId);
    const targetId = hasManualTarget
      ? liveTargetCharacterId
      : (hasSelected ? selectedId : (characters[0].id ?? 'char-0'));
    const targetChar = characters.find((c, i) => (c.id ?? `char-${i}`) === targetId) || characters[0];
    const targetIndex = characters.findIndex((c, i) => (c.id ?? `char-${i}`) === targetId);

    const poseX = Number(livePose?.centerXPercent);
    const poseY = Number(livePose?.centerYPercent);
    if (!Number.isFinite(poseX) || !Number.isFinite(poseY)) return;

    const current = getPos(targetChar, targetIndex);
    const anchor = liveAnchorRef.current[targetId] || {
      baseLeft: current.left,
      baseBottom: current.bottom,
      poseX,
      poseY,
    };
    liveAnchorRef.current[targetId] = anchor;

    const dx = poseX - anchor.poseX;
    const dy = poseY - anchor.poseY;
    const left = clamp(anchor.baseLeft + dx, 5, 90);
    const bottom = clamp(anchor.baseBottom - dy, 5, 80);

    setPositions((prev) => {
      const prevPos = prev[targetId];
      // 防止相同值反复写入导致渲染死循环
      if (prevPos && Math.abs(prevPos.left - left) < 0.01 && Math.abs(prevPos.bottom - bottom) < 0.01) {
        return prev;
      }
      return {
        ...prev,
        [targetId]: { left, bottom },
      };
    });
  }, [isLivePoseActive, livePose, characters, selectedId, liveTargetCharacterId, draggingId, getPos, clamp]);

  React.useEffect(() => {
    if (!isLivePoseActive) {
      liveAnchorRef.current = {};
    }
  }, [isLivePoseActive]);

  const handleScale = useCallback((id, delta) => {
    setScales((prev) => {
      const current = prev[id] ?? 1;
      const next = Math.min(SCALE_MAX, Math.max(SCALE_MIN, current + delta));
      return { ...prev, [id]: next };
    });
  }, []);

  const handleMouseDown = useCallback((e, char, index) => {
    if (e.button !== 0) return;
    const id = char.id ?? `char-${index}`;
    const pos = getPos(char, index);
    dragPendingId.current = id;
    dragStart.current = {
      x: e.clientX,
      y: e.clientY,
      left: pos.left,
      bottom: pos.bottom,
    };
  }, [getPos]);

  const handleMouseMove = useCallback((e) => {
    const pendingId = dragPendingId.current;
    if (pendingId && !draggingId && containerRef.current) {
      const dx = e.clientX - dragStart.current.x;
      const dy = e.clientY - dragStart.current.y;
      if (Math.sqrt(dx * dx + dy * dy) > DRAG_THRESHOLD_PX) {
        setSelectedId(pendingId);
        setDraggingId(pendingId);
      }
    }
    if (!draggingId || !containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const dx = (e.clientX - dragStart.current.x) / rect.width * 100;
    const dy = -(e.clientY - dragStart.current.y) / rect.height * 100;
    const left = Math.min(90, Math.max(5, dragStart.current.left + dx));
    const bottom = Math.min(80, Math.max(5, dragStart.current.bottom + dy));
    setPositions((prev) => ({ ...prev, [draggingId]: { left, bottom } }));
  }, [draggingId]);

  const handleMouseUp = useCallback(() => {
    if (draggingId) {
      if (isLivePoseActive) {
        const current = positions[draggingId];
        const poseX = Number(livePose?.centerXPercent);
        const poseY = Number(livePose?.centerYPercent);
        if (current && Number.isFinite(poseX) && Number.isFinite(poseY)) {
          liveAnchorRef.current[draggingId] = {
            baseLeft: current.left,
            baseBottom: current.bottom,
            poseX,
            poseY,
          };
        }
      }
      setDraggingId(null);
    } else if (dragPendingId.current) {
      const id = dragPendingId.current;
      setSelectedId((prev) => (prev === id ? null : id));
    }
    dragPendingId.current = null;
  }, [draggingId, isLivePoseActive, positions, livePose]);

  React.useEffect(() => {
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  if (!characters || characters.length === 0) {
    return (
      <div className="stage-characters empty">
        <div className="empty-hint">拖拽角色到舞台</div>
      </div>
    );
  }

  return (
    <div className="stage-characters" ref={containerRef}>
      {characters.map((char, index) => {
        const id = char.id ?? `char-${index}`;
        const pos = getPos(char, index);
        const scale = getScale(id);
        const isSelected = selectedId === id;
        const isManualLiveTarget = !!liveTargetCharacterId && id === liveTargetCharacterId;
        const isLiveTarget = isLivePoseActive && (
          isManualLiveTarget
          || (!liveTargetCharacterId && (isSelected || (!selectedId && index === 0)))
        );
        const isDragging = draggingId === id;
        const bodyRotateDeg = isLiveTarget ? withGain(livePose?.bodyRotateDeg, BODY_GAIN, -35, 35) : 0;
        const fullImage = char.thumbnail || char.image_url || char.images?.full;

        return (
          <div
            key={id}
            className={`stage-character ${isSelected ? 'selected' : ''} ${isDragging ? 'dragging' : ''}`}
            style={{
              left: `${pos.left}%`,
              bottom: `${pos.bottom}%`,
              transform: `translateX(-50%) scale(${scale})`,
            }}
            onMouseDown={(e) => handleMouseDown(e, char, index)}
            role="button"
            tabIndex={0}
            title="点击选中，再次点击取消选中；拖动可移动位置"
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setSelectedId((prev) => (prev === id ? null : id));
              }
            }}
          >
            {fullImage ? (
              <img
                src={resolveImageUrl(fullImage)}
                alt={char.name || '角色'}
                className="character-image"
                draggable={false}
                style={isLiveTarget ? { transform: `rotate(${bodyRotateDeg}deg)` } : undefined}
              />
            ) : (
              <div className="character-placeholder">{char.name || '角色'}</div>
            )}

            {isSelected && (
              <>
                <div className="stage-character-scale-bar" onMouseDown={(e) => e.stopPropagation()}>
                  <button
                    type="button"
                    className="stage-character-scale-btn"
                    onClick={(e) => { e.stopPropagation(); handleScale(id, -SCALE_STEP); }}
                    title="缩小"
                    aria-label="缩小"
                  >
                    -
                  </button>
                  <span className="stage-character-scale-value">{Math.round(scale * 100)}%</span>
                  <button
                    type="button"
                    className="stage-character-scale-btn"
                    onClick={(e) => { e.stopPropagation(); handleScale(id, SCALE_STEP); }}
                    title="放大"
                    aria-label="放大"
                  >
                    +
                  </button>
                </div>
                {onRemoveCharacter && (
                  <button
                    type="button"
                    className="stage-character-delete"
                    onMouseDown={(e) => e.stopPropagation()}
                    onClick={(e) => {
                      e.stopPropagation();
                      e.preventDefault();
                      onRemoveCharacter(id);
                      setSelectedId(null);
                    }}
                    title="从舞台移除"
                    aria-label="从舞台移除"
                  >
                    x
                  </button>
                )}
              </>
            )}
          </div>
        );
      })}
    </div>
  );
}
