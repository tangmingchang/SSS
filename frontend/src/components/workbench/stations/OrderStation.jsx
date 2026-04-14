import React from 'react';
import { useWorkbenchStore } from '../../../stores/workbenchStore';
import { API_BASE } from '../../../utils/api';
import { IconEdit, IconError } from '../../shared/Icons';
import './StationCommon.css';

/**
 * Order Station（点单站）
 * 输入想法/主题 → 生成剧本按钮
 */
export default function OrderStation() {
  const { orderTicket, updateOrderTicket, updateTask, setCurrentStation, markStationCompleted, goToNextStation } = useWorkbenchStore();
  const [isGenerating, setIsGenerating] = React.useState(false);

  const handleGenerateScript = async () => {
    if (!orderTicket.theme.trim()) return;

    setIsGenerating(true);
    updateTask('scriptGeneration', { status: 'running', progress: 0, message: '正在生成剧本...' });

    try {
      // 模拟进度更新
      let currentProgress = 0;
      const progressInterval = setInterval(() => {
        currentProgress = Math.min(currentProgress + 10, 90);
        updateTask('scriptGeneration', {
          status: 'running',
          progress: currentProgress,
          message: '正在生成剧本...'
        });
      }, 300);

      const res = await fetch(`${API_BASE}/api/generate_script`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          theme: orderTicket.theme,
          character: '',
          length: 1
        }),
      });

      clearInterval(progressInterval);

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        updateTask('scriptGeneration', {
          status: 'error',
          error: data.error || '生成失败',
          retryable: true
        });
        return;
      }

      updateTask('scriptGeneration', { status: 'success', progress: 100 });
      updateOrderTicket({
        script: data.script || data,
        actionSequence: data.action_sequence || []
      });
      markStationCompleted('order');
      
      // 自动跳转到下一站
      setTimeout(() => {
        setCurrentStation('script');
      }, 500);
    } catch (err) {
      updateTask('scriptGeneration', {
        status: 'error',
        error: err.message || '无法连接后端',
        retryable: true
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const task = useWorkbenchStore((state) => state.tasks.scriptGeneration);

  return (
    <div className="station-content order-station">
      <h3 className="station-title">
        <IconEdit size={18} />
        <span>点单站</span>
      </h3>
      <p className="station-desc">
        输入你的创作想法，AI将为你生成单场景剧本
      </p>

      <div className="station-input-group">
        <textarea
          className="wb-textarea"
          value={orderTicket.theme}
          onChange={(e) => updateOrderTicket({ theme: e.target.value })}
          placeholder="例如：黛玉葬花、杨贵妃霓裳羽衣舞、孙悟空大闹天宫..."
          rows={3}
        />
      </div>

      <div className="station-actions">
        <button
          className="btn-primary"
          onClick={handleGenerateScript}
          disabled={!orderTicket.theme.trim() || task.status === 'running'}
        >
          {task.status === 'running' ? `生成中... ${task.progress || 0}%` : '生成剧本'}
        </button>
      </div>

      {task.status === 'error' && (
        <div className="station-error">
          <span>
            <IconError size={14} />
            {task.error}
          </span>
          <button onClick={handleGenerateScript}>重试</button>
        </div>
      )}
    </div>
  );
}
