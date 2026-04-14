import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { useWorkbenchStore } from '../../stores/workbenchStore';
import StageBackground from './StageBackground';
import StageCharacters from './StageCharacters';
import PlaybackControls from './PlaybackControls';
import StageHUD from './StageHUD';
import './Stage.css';

/** 从剧本推导默认字幕文案 */
function getDefaultSubtitleText(orderTicket) {
  if (!orderTicket?.script) return '暂无字幕';
  if (orderTicket.script.scenes?.length > 0) return orderTicket.script.scenes[0].description || '暂无字幕';
  return typeof orderTicket.script === 'string' ? orderTicket.script : '暂无字幕';
}

const SUBTITLE_FONT_SIZE_MIN = 10;
const SUBTITLE_FONT_SIZE_MAX = 32;
const SUBTITLE_FONT_SIZE_STEP = 2;
const SUBTITLE_POSITION_CLAMP = { centerX: [5, 95], bottomPercent: [5, 90] };

/**
 * 中央主舞台组件
 * 包含：背景层、角色层、道具层、字幕层（可编辑/调字号/删除/拖拽位置）、播放控制、状态HUD
 */
export default function Stage() {
  const { stage, orderTicket, livePose, liveTargetCharacterId, updateStage, updateOrderTicket, setStageCanvasEl } = useWorkbenchStore();
  const [subtitleFocused, setSubtitleFocused] = useState(false);
  const [subtitleDragging, setSubtitleDragging] = useState(false);
  const canvasRef = useRef(null);
  const setCanvasRef = useCallback((el) => {
    canvasRef.current = el;
    setStageCanvasEl(el);
  }, [setStageCanvasEl]);
  const dragStartRef = useRef({ x: 0, y: 0, centerX: 50, bottomPercent: 12 });

  const brightness = stage.brightness ?? 0.8;
  const lighting = stage.lighting ?? 0.7;
  const subtitles = stage.subtitles ?? false;
  const subtitleFontSize = Math.min(SUBTITLE_FONT_SIZE_MAX, Math.max(SUBTITLE_FONT_SIZE_MIN, stage.subtitleFontSize ?? 14));
  const subtitleCenterX = stage.subtitleCenterX ?? 50;
  const subtitleBottomPercent = stage.subtitleBottomPercent ?? 12;

  const brightnessFilter = 0.3 + (brightness * 0.7);
  const lightingIntensity = lighting;

  const displayCharacters = useMemo(() => {
    if (stage.characters?.length > 0) return stage.characters;
    return orderTicket.character ? [orderTicket.character] : [];
  }, [stage.characters, orderTicket.character]);

  const displaySubtitleText = stage.subtitleText !== undefined && stage.subtitleText !== null
    ? stage.subtitleText
    : getDefaultSubtitleText(orderTicket);

  const handleSubtitleChange = useCallback((e) => {
    updateStage({ subtitleText: e.target.value });
  }, [updateStage]);

  const handleSubtitleFontSize = useCallback((delta) => {
    const next = Math.min(SUBTITLE_FONT_SIZE_MAX, Math.max(SUBTITLE_FONT_SIZE_MIN, subtitleFontSize + delta));
    updateStage({ subtitleFontSize: next });
  }, [subtitleFontSize, updateStage]);

  const handleRemoveSubtitle = useCallback(() => {
    updateStage({ subtitles: false });
  }, [updateStage]);

  const handleSubtitleDragStart = useCallback((e) => {
    if (e.button !== 0) return;
    e.preventDefault();
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    dragStartRef.current = {
      x: e.clientX,
      y: e.clientY,
      centerX: subtitleCenterX,
      bottomPercent: subtitleBottomPercent,
    };
    setSubtitleDragging(true);
  }, [subtitleCenterX, subtitleBottomPercent]);

  useEffect(() => {
    if (!subtitleDragging) return;
    const onMove = (e) => {
      const rect = canvasRef.current?.getBoundingClientRect();
      if (!rect) return;
      const dx = (e.clientX - dragStartRef.current.x) / rect.width * 100;
      const dy = (dragStartRef.current.y - e.clientY) / rect.height * 100;
      const centerX = Math.min(SUBTITLE_POSITION_CLAMP.centerX[1], Math.max(SUBTITLE_POSITION_CLAMP.centerX[0], dragStartRef.current.centerX + dx));
      const bottomPercent = Math.min(SUBTITLE_POSITION_CLAMP.bottomPercent[1], Math.max(SUBTITLE_POSITION_CLAMP.bottomPercent[0], dragStartRef.current.bottomPercent + dy));
      updateStage({ subtitleCenterX: centerX, subtitleBottomPercent: bottomPercent });
    };
    const onUp = () => setSubtitleDragging(false);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [subtitleDragging, updateStage]);

  const handleRemoveCharacter = (id) => {
    const list = stage.characters?.length > 0
      ? stage.characters
      : (orderTicket.character ? [orderTicket.character] : []);
    const next = list.filter((c, i) => (c.id ?? `char-${i}`) !== id);
    updateStage({ characters: next });
    if (next.length === 0) {
      updateOrderTicket({ character: null });
    }
  };

  return (
    <div className="stage-container">
      <div 
        ref={setCanvasRef}
        className="stage-canvas"
        style={{
          filter: `brightness(${brightnessFilter})`,
        }}
      >
        {/* 舞台背景层 */}
        <StageBackground background={stage.background || orderTicket.background} />

        {/* 角色层 */}
        <StageCharacters
          characters={displayCharacters}
          livePose={livePose}
          liveTargetCharacterId={liveTargetCharacterId}
          onRemoveCharacter={handleRemoveCharacter}
        />

        {/* 道具层（暂时为空） */}
        <div className="stage-props-layer"></div>

        {/* 灯光效果层 */}
        <div 
          className="stage-lighting-overlay"
          style={{
            opacity: lightingIntensity,
          }}
        />

        {/* 字幕层：可编辑、可调字号、可删除、可拖动调整位置 */}
        {subtitles && (
          <div
            className={`stage-subtitles ${subtitleFocused ? 'stage-subtitles-focused' : ''} ${subtitleDragging ? 'stage-subtitles-dragging' : ''}`}
            style={{
              fontSize: `${subtitleFontSize}px`,
              left: `${subtitleCenterX}%`,
              transform: 'translateX(-50%)',
              bottom: `${subtitleBottomPercent}%`,
            }}
          >
            <div
              className="stage-subtitles-toolbar"
              onMouseDown={handleSubtitleDragStart}
              onClick={(e) => e.stopPropagation()}
              title="拖动此处可调整字幕位置"
              role="button"
              tabIndex={0}
            >
              <span className="stage-subtitles-drag-hint" title="拖动调整位置">⋮⋮</span>
              <span className="stage-subtitles-size" onMouseDown={(e) => e.stopPropagation()}>
                <button type="button" className="stage-subtitles-btn" onClick={() => handleSubtitleFontSize(-SUBTITLE_FONT_SIZE_STEP)} aria-label="缩小字号">−</button>
                <span className="stage-subtitles-size-value">{subtitleFontSize}px</span>
                <button type="button" className="stage-subtitles-btn" onClick={() => handleSubtitleFontSize(SUBTITLE_FONT_SIZE_STEP)} aria-label="放大字号">+</button>
              </span>
              <button type="button" className="stage-subtitles-delete" onMouseDown={(e) => e.stopPropagation()} onClick={handleRemoveSubtitle} aria-label="删除字幕">删除</button>
            </div>
            <textarea
              className="subtitle-content subtitle-content-editable"
              value={displaySubtitleText}
              onChange={handleSubtitleChange}
              onFocus={() => setSubtitleFocused(true)}
              onBlur={() => setSubtitleFocused(false)}
              placeholder="输入或编辑字幕..."
              rows={2}
            />
          </div>
        )}

        {/* 状态HUD（右下角） */}
        <StageHUD />
      </div>

      {/* 播放控制（底部） */}
      <PlaybackControls />
    </div>
  );
}
