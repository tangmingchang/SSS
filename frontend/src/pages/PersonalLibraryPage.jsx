import { useState } from 'react';
import { resolveImageUrl } from '../utils/api';
import './PersonalLibraryPage.css';

function PersonalLibraryPage({ personalResources, onUpload }) {
  const [activeTab, setActiveTab] = useState('characters');
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [uploadType, setUploadType] = useState('characters');
  const [uploadName, setUploadName] = useState('');

  const tabs = [
    { id: 'characters', label: '人物', icon: '角' },
    { id: 'scenes', label: '场景', icon: '景' },
    { id: 'motions', label: '动作', icon: '动' },
    { id: 'music', label: '音乐', icon: '乐' },
  ];

  const handleUpload = () => {
    if (!uploadName.trim()) return;
    
    const newItem = {
      id: `personal-${uploadType}-${Date.now()}`,
      name: uploadName,
      type: uploadType,
    };
    
    onUpload(uploadType, newItem);
    setUploadName('');
    setShowUploadDialog(false);
  };

  /** 从资源项中取缩略图/图片地址（人物/场景等保存时带 image_url、thumbnail 或 url） */
  const getItemImageUrl = (item) => {
    if (!item) return null;
    const url = item.thumbnail || item.image_url || item.url;
    return url ? resolveImageUrl(url) : null;
  };

  const renderResourceCard = (item) => {
    const imgUrl = getItemImageUrl(item);
    return (
      <div key={item.id} className="resource-card">
        {imgUrl ? (
          <div className="resource-card-poster">
            <img src={imgUrl} alt={item.name || '资源'} />
          </div>
        ) : (
          <div className="resource-card-poster resource-card-poster-placeholder">
            <span>{item.type === 'scenes' ? '景' : '角'}</span>
          </div>
        )}
        <div className="resource-header">
          <h4>{item.name}</h4>
        </div>
        <p className="resource-note">个人资源</p>
      </div>
    );
  };

  return (
    <div className="personal-library-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">个人资源库</h1>
          <p className="page-subtitle">你收藏和上传的素材</p>
        </div>
        <button
          className="btn-upload"
          onClick={() => {
            setUploadType(activeTab);
            setShowUploadDialog(true);
          }}
        >
          + 添加资源
        </button>
      </div>

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
        {personalResources[activeTab]?.length > 0 ? (
          <div className="resource-grid">
            {personalResources[activeTab].map(renderResourceCard)}
          </div>
        ) : (
          <div className="empty-state">
            <div className="empty-icon">库</div>
            <p className="empty-text">暂无资源，点击上方"添加资源"按钮添加</p>
          </div>
        )}
      </div>

      {showUploadDialog && (
        <div className="upload-dialog-overlay" onClick={() => setShowUploadDialog(false)}>
          <div className="upload-dialog" onClick={(e) => e.stopPropagation()}>
            <h3>添加资源</h3>
            <input
              type="text"
              placeholder="输入资源名称"
              value={uploadName}
              onChange={(e) => setUploadName(e.target.value)}
              className="upload-input"
            />
            <div className="upload-actions">
              <button className="btn-cancel" onClick={() => setShowUploadDialog(false)}>
                取消
              </button>
              <button className="btn-confirm" onClick={handleUpload}>
                确认
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default PersonalLibraryPage;

