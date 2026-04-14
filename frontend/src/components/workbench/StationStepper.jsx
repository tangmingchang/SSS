import React from 'react';
import { useWorkbenchStore } from '../../stores/workbenchStore';
import { IconEdit, IconScript, IconMotion, IconStage, IconShowtime, IconExport, IconCheck } from '../shared/Icons';
import './StationStepper.css';

const STATIONS = [
  { id: 'order', label: '点单', Icon: IconEdit },
  { id: 'script', label: '剧本', Icon: IconScript },
  { id: 'motion', label: '动作', Icon: IconMotion },
  { id: 'stage', label: '布景', Icon: IconStage },
  { id: 'showtime', label: '演出', Icon: IconShowtime },
  { id: 'export', label: '交付', Icon: IconExport },
];

/**
 * 站点切换条组件
 * 显示6个站点，当前站点高亮，已完成站点打勾
 */
export default function StationStepper() {
  const { currentStation, completedStations, setCurrentStation } = useWorkbenchStore();

  return (
    <div className="station-stepper">
      {STATIONS.map((station, index) => {
        const isActive = currentStation === station.id;
        const isCompleted = completedStations.includes(station.id);
        /* 调试友好：所有站点均可点击，不依赖上一站完成 */
        const isAccessible = true;

        return (
          <button
            key={station.id}
            className={`station-step ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''} ${!isAccessible ? 'disabled' : ''}`}
            onClick={() => isAccessible && setCurrentStation(station.id)}
            disabled={!isAccessible}
          >
            <span className="station-icon">
              <station.Icon size={16} />
            </span>
            <span className="station-label">{station.label}</span>
            {isCompleted && (
              <span className="station-check">
                <IconCheck size={12} />
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
