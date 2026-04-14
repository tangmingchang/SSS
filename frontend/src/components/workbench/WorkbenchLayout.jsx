import React from 'react';
import TopRail from './TopRail';
import BottomRail from './BottomRail';
import Stage from '../stage/Stage';
import StageVideoPreview from '../stage/StageVideoPreview';
import StationCardCarousel from './StationCardCarousel';
import ExportAndTuningPanel from '../shared/ExportAndTuningPanel';
import { useWorkbenchStore } from '../../stores/workbenchStore';
import './WorkbenchLayout.css';

/**
 * 工作台主布局组件
 * 布局结构：
 * - Top Rail（顶部）：站点切换条 + Order Ticket
 * - Main Area（中间）：左中右三列布局
 *   - 左侧：站点选项（80%）+ 调参（20%）
 *   - 中间：舞台（50%）
 *   - 右侧：资源仓（40%）+ 摄像头（60%）
 */
export default function WorkbenchLayout({ children, allCharacters = [], allScenes = [], onAddToPersonal }) {
  const exportedVideoUrl = useWorkbenchStore((s) => s.exportedVideoUrl);
  return (
    <div className="workbench-layout">
      {/* 顶部站点轨道 */}
      <TopRail />

      {/* 中间区域：左中右三列布局 */}
      <div className="workbench-main-area">
        {/* 左侧：站点选项（80%）+ 调参（20%） */}
        <div className="workbench-options-area">
          <div className="options-station-area">
            <StationCardCarousel allCharacters={allCharacters} allScenes={allScenes} onAddToPersonal={onAddToPersonal} />
          </div>
          <div className="options-tuning-area">
            <ExportAndTuningPanel />
          </div>
        </div>

        {/* 中间：中央主舞台（50%）；导出视频成功后显示视频预览（同尺寸 + 播放/倍速） */}
        <div className="workbench-stage-area">
          {exportedVideoUrl ? (
            <StageVideoPreview videoUrl={exportedVideoUrl} />
          ) : (
            <Stage />
          )}
        </div>

        {/* 右侧：工具区域（资源仓40% + 摄像头60%） */}
        <div className="workbench-tools-area">
          <BottomRail allCharacters={allCharacters} allScenes={allScenes} />
        </div>
      </div>

      {children}
    </div>
  );
}
