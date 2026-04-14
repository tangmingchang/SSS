import React from 'react';
import StationStepper from './StationStepper';
import OrderTicket from './OrderTicket';
import './TopRail.css';

/**
 * 顶部站点轨道组件
 * 包含：Station Stepper + Order Ticket
 */
export default function TopRail() {
  return (
    <div className="top-rail">
      <div className="top-rail-content">
        {/* 站点切换条 */}
        <StationStepper />

        {/* 订单票据 */}
        <OrderTicket />
      </div>
    </div>
  );
}
