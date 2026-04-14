import React, { useState } from 'react';
import { useWorkbenchStore } from '../../stores/workbenchStore';
import { IconSettings, IconArrowDown, IconArrowUp } from './Icons';
import './ExportAndTuningPanel.css';

/**
 * 导出与调参面板组件（可折叠）
 */
export default function ExportAndTuningPanel() {
  const { ui, updateUI, stage, updateStage } = useWorkbenchStore();
  const expanded = ui.bottomRailExpanded.export;

  const toggleExpand = () => {
    updateUI({
      bottomRailExpanded: {
        ...ui.bottomRailExpanded,
        export: !expanded
      }
    });
  };

  return (
    <div className={`export-tuning-panel ${expanded ? 'expanded' : ''}`}>
      <button className="panel-toggle" onClick={toggleExpand}>
        <span className="panel-icon">
          <IconSettings size={16} />
        </span>
        <span className="panel-label">调参</span>
        <span className="panel-arrow">
          {expanded ? <IconArrowDown size={12} /> : <IconArrowUp size={12} />}
        </span>
      </button>

      {expanded && (
        <div className="panel-content">
          <div className="tuning-controls">
            <div className="control-item">
              <label>
                亮度
                <span className="control-value">{Math.round((stage.brightness ?? 0.8) * 100)}%</span>
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={stage.brightness ?? 0.8}
                onChange={(e) => updateStage({ brightness: parseFloat(e.target.value) })}
              />
            </div>
            <div className="control-item">
              <label>
                灯光
                <span className="control-value">{Math.round((stage.lighting ?? 0.7) * 100)}%</span>
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={stage.lighting ?? 0.7}
                onChange={(e) => updateStage({ lighting: parseFloat(e.target.value) })}
              />
            </div>
            <div className="control-item">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={stage.subtitles ?? false}
                  onChange={(e) => updateStage({ subtitles: e.target.checked })}
                />
                <span>字幕</span>
              </label>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
