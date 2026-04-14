import React, { useState } from 'react';
import { useWorkbenchStore } from '../../stores/workbenchStore';
import { IconTicket, IconPin, IconLocation, IconArrowDown, IconArrowUp } from '../shared/Icons';
import './OrderTicket.css';

/**
 * 订单票据组件
 * 显示当前"订单"状态（主题/剧本/动作/情绪/场景）
 * 可折叠/展开，支持钉住，错误字段标红
 */
export default function OrderTicket() {
  const { orderTicket, currentStation, ui, updateUI } = useWorkbenchStore();
  const [isExpanded, setIsExpanded] = useState(ui.orderTicketExpanded);

  const toggleExpand = () => {
    const newExpanded = !isExpanded;
    setIsExpanded(newExpanded);
    updateUI({ orderTicketExpanded: newExpanded });
  };

  const togglePin = () => {
    updateUI({ orderTicketPinned: !ui.orderTicketPinned });
  };

  // 获取当前站点负责的字段
  const getCurrentStationFields = () => {
    const fieldMap = {
      order: ['theme'],
      script: ['script'],
      motion: ['actionSequence'],
      stage: ['character', 'background'],
      showtime: ['videoOptions', 'sceneAnalysis'],
      export: [],
    };
    return fieldMap[currentStation] || [];
  };

  // 检查字段是否有错误
  const hasFieldError = (field) => {
    // 简单检查：必填字段为空
    if (field === 'theme' && !orderTicket.theme) return true;
    if (field === 'script' && !orderTicket.script) return true;
    if (field === 'character' && !orderTicket.character) return true;
    if (field === 'background' && !orderTicket.background) return true;
    if (field === 'actionSequence' && (!orderTicket.actionSequence || orderTicket.actionSequence.length === 0)) return true;
    return false;
  };

  const currentFields = getCurrentStationFields();

  return (
    <div className={`order-ticket ${isExpanded ? 'expanded' : ''} ${ui.orderTicketPinned ? 'pinned' : ''}`}>
      <div className="ticket-header" onClick={toggleExpand}>
        <div className="ticket-title">
          <span className="ticket-icon">
            <IconTicket size={18} />
          </span>
          <span className="ticket-label">订单票据</span>
          {orderTicket.theme && (
            <span className="ticket-theme">{orderTicket.theme.slice(0, 20)}</span>
          )}
        </div>
        <div className="ticket-actions">
          <button
            className="ticket-pin-btn"
            onClick={(e) => {
              e.stopPropagation();
              togglePin();
            }}
            title={ui.orderTicketPinned ? '取消钉住' : '钉住'}
          >
            {ui.orderTicketPinned ? <IconPin size={14} /> : <IconLocation size={14} />}
          </button>
          <button className="ticket-expand-btn">
            {isExpanded ? <IconArrowDown size={14} /> : <IconArrowUp size={14} />}
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="ticket-content">
          <div className="ticket-field">
            <span className="field-label">主题：</span>
            <span className={`field-value ${hasFieldError('theme') ? 'error' : ''} ${currentFields.includes('theme') ? 'highlight' : ''}`}>
              {orderTicket.theme || '未填写'}
            </span>
          </div>

          <div className="ticket-field">
            <span className="field-label">剧本：</span>
            <span className={`field-value ${hasFieldError('script') ? 'error' : ''} ${currentFields.includes('script') ? 'highlight' : ''}`}>
              {orderTicket.script ? '已生成' : '未生成'}
            </span>
          </div>

          <div className="ticket-field">
            <span className="field-label">角色：</span>
            <span className={`field-value ${hasFieldError('character') ? 'error' : ''} ${currentFields.includes('character') ? 'highlight' : ''}`}>
              {orderTicket.character?.name || '未选择'}
            </span>
          </div>

          <div className="ticket-field">
            <span className="field-label">背景：</span>
            <span className={`field-value ${hasFieldError('background') ? 'error' : ''} ${currentFields.includes('background') ? 'highlight' : ''}`}>
              {orderTicket.background?.name || '未选择'}
            </span>
          </div>

          <div className="ticket-field">
            <span className="field-label">动作序列：</span>
            <span className={`field-value ${hasFieldError('actionSequence') ? 'error' : ''} ${currentFields.includes('actionSequence') ? 'highlight' : ''}`}>
              {orderTicket.actionSequence?.length || 0} 个动作
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
