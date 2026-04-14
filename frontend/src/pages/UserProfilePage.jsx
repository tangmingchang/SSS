import { useState, useEffect, useRef } from 'react';
import './UserProfilePage.css';
import { getCurrentUser, updateUserInfo, uploadAvatar } from '../services/authService';
import { API_BASE } from '../utils/api';
import PersonalLibraryPage from './PersonalLibraryPage';
import AiGeneratorPage from './AiGeneratorPage';
import PortfolioPage from './PortfolioPage';

function UserProfilePage({ publicResources = { characters: [], scenes: [], motions: [], music: [] }, personalResources = { characters: [], scenes: [], motions: [], music: [] }, onAddToPersonal, currentUser }) {
  const [isEditing, setIsEditing] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const fileInputRef = useRef(null);
  
  const [userInfo, setUserInfo] = useState({
    id: null,
    username: '',
    email: '',
    accountType: '',
    registerTime: '',
    avatar: null,
  });
  
  const [editForm, setEditForm] = useState({
    username: '',
    email: '',
    avatar: null,
    avatarPreview: null,
  });

  useEffect(() => {
    const loadUserData = async () => {
      setIsLoading(true);
      try {
        const result = await getCurrentUser();
        if (result.success && result.data.user) {
          const user = result.data.user;
          setUserInfo({
            id: user.id,
            username: user.username || '',
            email: user.email || '',
            accountType: user.account_type === 'teacher' ? '教师' : (user.account_type === 'student' ? '学生' : '专业版'),
            registerTime: user.created_at ? new Date(user.created_at).toLocaleDateString('zh-CN') : '',
            avatar: user.avatar_url || null,
          });
          setEditForm({
            username: user.username || '',
            email: user.email || '',
            avatar: null,
            avatarPreview: user.avatar_url || null,
          });
        }
      } catch (error) {
        console.error('加载用户信息失败:', error);
      } finally {
        setIsLoading(false);
      }
    };
    
    loadUserData();
  }, []);

  const handleEdit = () => {
    setIsEditing(true);
    setEditForm({
      username: userInfo.username,
      email: userInfo.email,
      avatar: null,
      avatarPreview: userInfo.avatar,
    });
    setError('');
  };

  const handleCancel = () => {
    setIsEditing(false);
    setEditForm({
      username: userInfo.username,
      email: userInfo.email,
      avatar: null,
      avatarPreview: userInfo.avatar,
    });
    setError('');
  };

  const handleAvatarChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      // 检查文件大小（限制5MB）
      if (file.size > 5 * 1024 * 1024) {
        setError('头像文件大小不能超过5MB');
        return;
      }
      
      // 检查文件类型
      const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp'];
      if (!allowedTypes.includes(file.type)) {
        setError('不支持的文件类型，仅支持: PNG, JPG, JPEG, GIF, WEBP');
        return;
      }
      
      // 创建预览
      const reader = new FileReader();
      reader.onloadend = () => {
        setEditForm({
          ...editForm,
          avatar: file,
          avatarPreview: reader.result,
        });
      };
      reader.readAsDataURL(file);
      setError('');
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setError('');
    
    try {
      // 先上传头像（如果有）
      if (editForm.avatar) {
        const avatarResult = await uploadAvatar(editForm.avatar);
        if (!avatarResult.success) {
          setError(avatarResult.error || '头像上传失败');
          setIsSaving(false);
          return;
        }
      }
      
      // 更新用户信息
      const result = await updateUserInfo(editForm.username, editForm.email);
      if (result.success) {
        // 重新加载用户数据
        const userResult = await getCurrentUser();
        if (userResult.success && userResult.data.user) {
          const user = userResult.data.user;
          setUserInfo({
            id: user.id,
            username: user.username || '',
            email: user.email || '',
            accountType: user.account_type === 'teacher' ? '教师' : (user.account_type === 'student' ? '学生' : '专业版'),
            registerTime: user.created_at ? new Date(user.created_at).toLocaleDateString('zh-CN') : '',
            avatar: user.avatar_url || null,
          });
        }
        setIsEditing(false);
        setError('');
      } else {
        setError(result.error || '更新失败');
      }
    } catch (err) {
      setError(err.message || '操作失败，请稍后重试');
    } finally {
      setIsSaving(false);
    }
  };

  const getAvatarUrl = (avatarPath) => {
    if (!avatarPath) return null;
    if (avatarPath.startsWith('http') || avatarPath.startsWith('data:')) return avatarPath;
    if (avatarPath.startsWith('/api/')) return `${API_BASE}${avatarPath}`;
    return `${API_BASE}${avatarPath}`;
  };

  if (isLoading) {
    return (
      <div className="user-profile-page">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>加载中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="user-profile-page">
      {/* 个人资料卡 + 个人资源库 */}
      <div className="profile-with-library">
        <div className="profile-main-card">
        <div className="profile-card-header">
          <div className="profile-card-title">
            <h2 className="card-title-text">个人中心</h2>
            {!isEditing && (
              <button className="btn-edit-profile" onClick={handleEdit}>
                编辑资料
              </button>
            )}
            {isEditing && (
              <div className="edit-actions">
                <button className="btn-cancel" onClick={handleCancel}>
                  取消
                </button>
                <button className="btn-save" onClick={handleSave} disabled={isSaving}>
                  {isSaving ? '保存中...' : '保存'}
                </button>
              </div>
            )}
          </div>
        </div>

        {error && (
          <div className="error-message">{error}</div>
        )}

        <div className="profile-card-content">
          {/* 左侧：头像区域 */}
          <div className="profile-avatar-wrapper">
            <div 
              className={`profile-avatar ${isEditing ? 'editable' : ''}`} 
              onClick={() => isEditing && fileInputRef.current?.click()}
            >
              {(isEditing ? editForm.avatarPreview : userInfo.avatar) ? (
                <img 
                  src={getAvatarUrl(isEditing ? editForm.avatarPreview : userInfo.avatar)} 
                  alt="头像" 
                />
              ) : (
                <span className="avatar-placeholder">{userInfo.username.charAt(0) || '用'}</span>
              )}
              {isEditing && (
                <div className="avatar-overlay">
                  <span>点击更换</span>
                </div>
              )}
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpeg,image/jpg,image/gif,image/webp"
              onChange={handleAvatarChange}
              style={{ display: 'none' }}
            />
            <div className="profile-badge-group">
              <span className="badge-item">{userInfo.accountType || '学生'}</span>
              {userInfo.registerTime && (
                <span className="badge-item">注册于 {userInfo.registerTime}</span>
              )}
            </div>
          </div>

          {/* 右侧：用户信息区域 */}
          <div className="profile-info-wrapper">
            {isEditing ? (
              <div className="edit-form">
                <div className="form-group">
                  <label>用户名</label>
                  <input
                    type="text"
                    value={editForm.username}
                    onChange={(e) => setEditForm({ ...editForm, username: e.target.value })}
                    placeholder="请输入用户名"
                    maxLength={20}
                  />
                </div>
                <div className="form-group">
                  <label>邮箱</label>
                  <input
                    type="email"
                    value={editForm.email}
                    onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                    placeholder="请输入邮箱"
                  />
                </div>
                <div className="form-group">
                  <label>账号类型</label>
                  <div className="form-readonly">{userInfo.accountType || '学生'}</div>
                </div>
                {userInfo.registerTime && (
                  <div className="form-group">
                    <label>注册时间</label>
                    <div className="form-readonly">{userInfo.registerTime}</div>
                  </div>
                )}
              </div>
            ) : (
              <div className="info-display">
                <div className="info-header">
                  <h1 className="profile-name">{userInfo.username || '用户'}</h1>
                  <p className="profile-email">{userInfo.email || ''}</p>
                </div>
                <div className="info-list">
                  <div className="info-item">
                    <span className="info-label">用户名</span>
                    <span className="info-value">{userInfo.username || '-'}</span>
                  </div>
                  <div className="info-item">
                    <span className="info-label">邮箱</span>
                    <span className="info-value">{userInfo.email || '-'}</span>
                  </div>
                  <div className="info-item">
                    <span className="info-label">账号类型</span>
                    <span className="info-value">{userInfo.accountType || '学生'}</span>
                  </div>
                  {userInfo.registerTime && (
                    <div className="info-item">
                      <span className="info-label">注册时间</span>
                      <span className="info-value">{userInfo.registerTime}</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
        </div>
        <div className="profile-library-inline">
          <PersonalLibraryPage personalResources={personalResources} onUpload={onAddToPersonal} />
        </div>
      </div>

      {/* 作品集 */}
      <div className="profile-section profile-section-portfolio">
        <PortfolioPage currentUserId={currentUser?.id} />
      </div>

      {/* AI 生成 */}
      <div className="profile-section profile-section-ai">
        <AiGeneratorPage onGenerateToPersonal={onAddToPersonal} />
      </div>
    </div>
  );
}

export default UserProfilePage;
