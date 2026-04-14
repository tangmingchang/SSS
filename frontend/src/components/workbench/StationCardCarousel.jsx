import React from 'react';
import { useWorkbenchStore } from '../../stores/workbenchStore';
import StationCard from './StationCard';
import OrderStation from './stations/OrderStation';
import ScriptStation from './stations/ScriptStation';
import MotionStation from './stations/MotionStation';
import StageStation from './stations/StageStation';
import ShowtimeStation from './stations/ShowtimeStation';
import ExportStation from './stations/ExportStation';
import './StationCardCarousel.css';

/**
 * 站点卡片轮播容器
 * 根据当前站点显示对应的Station Card
 */
export default function StationCardCarousel({ allCharacters = [], allScenes = [], onAddToPersonal }) {
  const { currentStation } = useWorkbenchStore();

  const renderStationContent = () => {
    switch (currentStation) {
      case 'order':
        return <OrderStation />;
      case 'script':
        return <ScriptStation />;
      case 'motion':
        return <MotionStation />;
      case 'stage':
        return <StageStation allCharacters={allCharacters} allScenes={allScenes} onAddToPersonal={onAddToPersonal} />;
      case 'showtime':
        return <ShowtimeStation />;
      case 'export':
        return <ExportStation />;
      default:
        return <OrderStation />;
    }
  };

  return (
    <div className="station-card-carousel">
      <StationCard station={currentStation} isActive={true}>
        {renderStationContent()}
      </StationCard>
    </div>
  );
}
