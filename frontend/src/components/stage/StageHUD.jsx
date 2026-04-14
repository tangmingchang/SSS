import React from 'react';
import { useWorkbenchStore } from '../../stores/workbenchStore';
import './StageHUD.css';

/**
 * 舞台状态HUD组件（右下角）
 * 显示生成/渲染/捕捉状态
 */
export default function StageHUD() {
  const { tasks } = useWorkbenchStore();

  // 仅显示部分任务在 HUD；生成剧本、生成视频的进度在各自站点内显示，不在此弹框
  const runningTasks = Object.entries(tasks).filter(
    ([taskId, task]) =>
      task.status === 'running' &&
      taskId !== 'scriptGeneration' &&
      taskId !== 'videoGeneration'
  );

  if (runningTasks.length === 0) {
    return null;
  }

  return (
    <div className="stage-hud">
      {runningTasks.map(([taskId, task]) => (
        <div key={taskId} className="hud-task">
          <div className="hud-task-header">
            <span className="hud-task-name">{getTaskName(taskId)}</span>
            <span className="hud-task-progress">{task.progress || 0}%</span>
          </div>
          <div className="hud-progress-bar">
            <div
              className="hud-progress-fill"
              style={{ width: `${task.progress || 0}%` }}
            />
          </div>
          {task.message && (
            <div className="hud-task-message">{task.message}</div>
          )}
        </div>
      ))}
    </div>
  );
}

function getTaskName(taskId) {
  const names = {
    scriptGeneration: '生成剧本',
    videoGeneration: '生成视频',
    motionCapture: '动作捕捉',
    sceneAnalysis: '场景分析',
  };
  return names[taskId] || taskId;
}
