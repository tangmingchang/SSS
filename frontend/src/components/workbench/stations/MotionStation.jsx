import React from 'react';
import { useWorkbenchStore } from '../../../stores/workbenchStore';
import ActionEditor from '../../ActionEditor';
import { IconMotion } from '../../shared/Icons';
import './StationCommon.css';

/**
 * Motion Station（动作站）
 * 情绪/动作标签选择、生成动作序列、动作预览
 */
export default function MotionStation() {
  const { orderTicket, updateOrderTicket, markStationCompleted, goToNextStation } = useWorkbenchStore();

  const handleActionChange = (actions) => {
    // 将编辑后的动作转换为Order Ticket格式
    updateOrderTicket({ actionSequence: actions });
  };

  const handleNext = () => {
    if (orderTicket.actionSequence && orderTicket.actionSequence.length > 0) {
      markStationCompleted('motion');
      goToNextStation();
    }
  };

  return (
    <div className="station-content motion-station">
      <h3 className="station-title">
        <IconMotion size={18} />
        <span>动作站</span>
      </h3>
      <p className="station-desc">
        编辑动作序列，从剧本中提取的动作节点可以自由添加、删除或修改
      </p>

      {!orderTicket.script ? (
        <div className="station-empty">
          请先在点单站生成剧本
        </div>
      ) : (
        <>
          <div className="action-editor-container">
            <ActionEditor
              script={orderTicket.script}
              actionSequence={orderTicket.actionSequence || []}
              onChange={handleActionChange}
            />
          </div>

          <div className="station-actions">
            <button
              className="btn-primary"
              onClick={handleNext}
              disabled={!orderTicket.actionSequence || orderTicket.actionSequence.length === 0}
            >
              下一站：布景 →
            </button>
          </div>
        </>
      )}
    </div>
  );
}
