import React from 'react';
import AssetDrawer from '../shared/AssetDrawer';
import CapturePanel from '../shared/CapturePanel';
import './BottomRail.css';

/**
 * 右侧工具区域组件
 * 包含：资源仓（40%）+ 摄像头（60%）
 */
export default function BottomRail({ allCharacters = [], allScenes = [] }) {
  return (
    <div className="bottom-rail">
      <div className="bottom-rail-content">
        {/* 资源仓 */}
        <AssetDrawer allCharacters={allCharacters} allScenes={allScenes} />

        {/* 摄像头模块 */}
        <CapturePanel />
      </div>
    </div>
  );
}
