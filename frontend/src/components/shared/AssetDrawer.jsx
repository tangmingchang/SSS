import React, { useState } from 'react';
import { useWorkbenchStore } from '../../stores/workbenchStore';
import { resolveImageUrl } from '../../utils/api';
import { IconBox, IconArrowDown, IconArrowUp } from './Icons';
import './AssetDrawer.css';

/**
 * 资源仓组件（可折叠）
 * 角色/道具/背景/音效缩略图抽屉
 */
export default function AssetDrawer({ allCharacters = [], allScenes = [] }) {
  const { ui, updateUI } = useWorkbenchStore();
  const [activeTab, setActiveTab] = useState('characters');
  const expanded = ui.bottomRailExpanded.assets;

  const toggleExpand = () => {
    updateUI({
      bottomRailExpanded: {
        ...ui.bottomRailExpanded,
        assets: !expanded
      }
    });
  };

  return (
    <div className={`asset-drawer ${expanded ? 'expanded' : ''}`}>
      <button className="drawer-toggle" onClick={toggleExpand}>
        <span className="drawer-icon">
          <IconBox size={16} />
        </span>
        <span className="drawer-label">资源仓</span>
        <span className="drawer-arrow">
          {expanded ? <IconArrowUp size={12} /> : <IconArrowDown size={12} />}
        </span>
      </button>

      {expanded && (
        <div className="drawer-content">
          <div className="asset-tabs">
            <button
              className={activeTab === 'characters' ? 'active' : ''}
              onClick={() => setActiveTab('characters')}
            >
              角色
            </button>
            <button
              className={activeTab === 'scenes' ? 'active' : ''}
              onClick={() => setActiveTab('scenes')}
            >
              背景
            </button>
          </div>

          <div className="asset-grid">
            {activeTab === 'characters' && allCharacters.map((char) => {
              const imgUrl = char.thumbnail || char.image_url;
              return (
                <div key={char.id} className="asset-item" draggable>
                  {imgUrl ? (
                    <img src={resolveImageUrl(imgUrl)} alt={char.name} />
                  ) : (
                    <div className="asset-item-placeholder" aria-hidden>无图</div>
                  )}
                  <span>{char.name}</span>
                </div>
              );
            })}
            {activeTab === 'scenes' && allScenes.map((scene) => {
              const imgUrl = scene.thumbnail || scene.url;
              return (
                <div key={scene.id} className="asset-item" draggable>
                  {imgUrl ? (
                    <img src={resolveImageUrl(imgUrl)} alt={scene.name} />
                  ) : (
                    <div className="asset-item-placeholder" aria-hidden>无图</div>
                  )}
                  <span>{scene.name}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
