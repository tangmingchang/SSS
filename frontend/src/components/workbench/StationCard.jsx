import React from 'react';
import './StationCard.css';

/**
 * 站点卡片容器组件
 * 统一的站点卡片样式和动画
 */
export default function StationCard({ station, isActive, children }) {
  return (
    <div className={`station-card ${isActive ? 'active' : ''}`}>
      {children}
    </div>
  );
}
