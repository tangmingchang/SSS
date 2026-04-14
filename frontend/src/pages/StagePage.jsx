import React, { useState, useEffect } from 'react';
import { apiPerformanceGet, apiPerformanceSave, apiPerformanceRender } from '../services/teachApi';
import { useWorkbenchStore } from '../stores/workbenchStore';
import Stage from '../components/stage/Stage';
import './StagePage.css';

/**
 * 大舞台页：按 performanceId 加载/保存舞台工程，支持课堂演示模式 / 学生练习模式
 * mode: 'demo' | 'practice'
 * 保存时从 workbenchStore 读取当前 stage + orderTicket 作为 payload
 */
export default function StagePage({ performanceId, mode = 'practice', classId, onBack }) {
  const [performance, setPerformance] = useState(null);
  const [loading, setLoading] = useState(!!performanceId);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!performanceId) {
      setPerformance(null);
      setLoading(false);
      return;
    }
    let cancelled = false;
    apiPerformanceGet(performanceId)
      .then((p) => { if (!cancelled) setPerformance(p); })
      .catch((e) => { if (!cancelled) setError(e.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [performanceId]);

  const handleSave = async () => {
    const state = useWorkbenchStore.getState();
    const payload = {
      stage: state.stage,
      orderTicket: state.orderTicket,
    };
    setSaving(true);
    try {
      const p = await apiPerformanceSave({
        title: performance?.title,
        payload,
        classId: classId || performance?.classId,
      });
      setPerformance((prev) => ({ ...prev, id: p.id, payload: p.payload }));
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleRender = async () => {
    if (!performance?.id) return;
    try {
      const r = await apiPerformanceRender(performance.id);
      alert(r.message || '渲染已提交，请稍后查看导出');
    } catch (e) {
      setError(e.message);
    }
  };

  if (loading) return <div className="stage-page-wrap">加载中…</div>;
  if (error) return <div className="stage-page-wrap stage-error">错误：{error}</div>;

  const isDemo = mode === 'demo';

  return (
    <div className={`stage-page-wrap stage-mode-${mode}`}>
      {(onBack || true) && (
        <div className="stage-page-bar">
          {onBack && <button type="button" onClick={onBack}>返回</button>}
          {isDemo && <span className="stage-mode-label">课堂演示模式</span>}
          {!isDemo && <span className="stage-mode-label">学生练习模式</span>}
          <button type="button" onClick={handleSave} disabled={saving}>
            {saving ? '保存中…' : '保存'}
          </button>
          {performance?.id && (
            <button type="button" onClick={handleRender}>导出 mp4/gif</button>
          )}
        </div>
      )}
      <div className="stage-page-main">
        <Stage />
      </div>
    </div>
  );
}
