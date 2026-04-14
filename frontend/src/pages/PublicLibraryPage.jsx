import { useState } from 'react';
import { resolveImageUrl } from '../utils/api';
import './PublicLibraryPage.css';

function PublicLibraryPage({ publicResources }) {
  const [activeTab, setActiveTab] = useState('characters');

  const tabs = [
    { id: 'characters', label: '人物' },
    { id: 'scenes', label: '场景' },
    { id: 'motions', label: '动作' },
    { id: 'music', label: '音乐' },
    { id: 'cases', label: '案例' },
  ];

  const safeList = (list) => (Array.isArray(list) ? list : []);

  const renderResourceCard = (item, type) => {
    let imageUrl = null;
    const resourceUrl = item?.url || item?.link || item?.previewUrl || item?.videoUrl || item?.audioUrl || null;

    if (type === 'characters') {
      imageUrl = item?.thumbnail || item?.images?.full || null;
    } else if (type === 'scenes') {
      imageUrl = item?.url || null;
    }

    const resolvedImageUrl = imageUrl ? resolveImageUrl(imageUrl) : null;
    const resolvedResourceUrl = resourceUrl ? resolveImageUrl(resourceUrl) : null;
    const itemId = item?.id || `${type}-${item?.name || Math.random()}`;

    return (
      <div key={itemId} className="resource-card">
        {resolvedImageUrl && (
          <div className="resource-image">
            <img
              src={resolvedImageUrl}
              alt={item?.name || '资源'}
              onError={(e) => {
                e.currentTarget.style.display = 'none';
              }}
            />
          </div>
        )}

        <div className="resource-header">
          <h4>{item?.name || '未命名资源'}</h4>
          {Array.isArray(item?.tags) && item.tags.length > 0 && (
            <div className="resource-tags">
              {item.tags.map((tag, idx) => (
                <span key={`${itemId}-tag-${idx}`} className="resource-tag">{tag}</span>
              ))}
            </div>
          )}
        </div>

        {item?.style && <p className="resource-style">风格：{item.style}</p>}
        {item?.duration && <p className="resource-duration">时长：{item.duration}</p>}

        {type === 'music' && resolvedResourceUrl && (
          <div className="resource-media-wrap">
            <audio className="resource-media" controls preload="none" src={resolvedResourceUrl} />
          </div>
        )}

        {type === 'cases' && resolvedResourceUrl && (
          <div className="resource-media-wrap">
            <video className="resource-media" controls preload="metadata" src={resolvedResourceUrl} />
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="public-library-page">
      <h1 className="page-title">公共资源库</h1>
      <p className="page-subtitle">平台提供的免费资源，可直接使用</p>

      <div className="library-tabs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`library-tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            <span className="tab-label">{tab.label}</span>
          </button>
        ))}
      </div>

      <div className="library-content">
        {activeTab === 'characters' && (
          <div className="resource-grid">
            {safeList(publicResources?.characters).map((item) => renderResourceCard(item, 'characters'))}
          </div>
        )}

        {activeTab === 'scenes' && (
          <div className="resource-grid">
            {safeList(publicResources?.scenes).map((item) => renderResourceCard(item, 'scenes'))}
          </div>
        )}

        {activeTab === 'motions' && (
          <div className="resource-grid">
            {safeList(publicResources?.motions).map((item) => renderResourceCard(item, 'motions'))}
          </div>
        )}

        {activeTab === 'music' && (
          <div className="resource-grid">
            {safeList(publicResources?.music).map((item) => renderResourceCard(item, 'music'))}
          </div>
        )}

        {activeTab === 'cases' && (
          <div className="resource-grid">
            {safeList(publicResources?.cases).map((item) => renderResourceCard(item, 'cases'))}
          </div>
        )}
      </div>
    </div>
  );
}

export default PublicLibraryPage;
