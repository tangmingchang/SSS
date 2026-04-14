import React from 'react';
import { useWorkbenchStore } from '../../../stores/workbenchStore';
import { IconScript } from '../../shared/Icons';
import './StationCommon.css';

/**
 * Script Station（剧本站）
 * 剧本预览/编辑、分镜、关键词高亮
 */
export default function ScriptStation() {
  const { orderTicket, updateOrderTicket, markStationCompleted, goToNextStation } = useWorkbenchStore();
  const task = useWorkbenchStore((state) => state.tasks.scriptGeneration);

  const formatScriptForDisplay = (script) => {
    if (!script || typeof script !== 'object') return '暂未生成剧本';
    const lines = [];
    if (script.title) lines.push(script.title);
    if (script.theme) lines.push(`主题：${script.theme}`);
    if (script.character) lines.push(`角色：${script.character}`);
    if (Array.isArray(script.scenes)) {
      script.scenes.forEach((s) => {
        lines.push(`\n【场景 ${s.scene_number}】${s.description || ''}`);
        if (s.lines && s.lines.length) lines.push(`台词：${s.lines.join(' / ')}`);
        if (s.actions && s.actions.length) lines.push(`动作：${s.actions.join(' → ')}`);
        if (s.emotion) lines.push(`情绪：${s.emotion}`);
      });
    }
    return lines.length ? lines.join('\n') : JSON.stringify(script, null, 2);
  };

  const handleNext = () => {
    if (orderTicket.script) {
      markStationCompleted('script');
      goToNextStation();
    }
  };

  return (
    <div className="station-content script-station">
      <h3 className="station-title">
        <IconScript size={18} />
        <span>剧本站</span>
      </h3>
      <p className="station-desc">
        预览和编辑生成的剧本，确认无误后进入下一站
      </p>

      <div className="script-preview-container">
        {task.status === 'running' ? (
          <div className="script-loading">
            <div className="loading-spinner"></div>
            <div className="loading-text">正在生成剧本... {task.progress || 0}%</div>
          </div>
        ) : (
          <pre className="script-preview">
            {orderTicket.script ? formatScriptForDisplay(orderTicket.script) : '请先在点单站生成剧本'}
          </pre>
        )}
      </div>

      <div className="station-actions">
        <button
          className="btn-primary"
          onClick={handleNext}
          disabled={!orderTicket.script || task.status === 'running'}
        >
          下一站：动作 →
        </button>
      </div>
    </div>
  );
}
