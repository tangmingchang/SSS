import { useState, useEffect } from 'react';
import './AuthModal.css';
import { login as loginAPI, register as registerAPI } from '../../services/authService';

/**
 * 登录注册模态框组件
 */
export default function AuthModal({ isOpen, onClose, onLogin, onRegister, initialMode = 'login', onOpenPrivacyPolicy }) {
  const [isLoginMode, setIsLoginMode] = useState(initialMode === 'login');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  
  useEffect(() => {
    if (isOpen) {
      setIsLoginMode(initialMode === 'login');
      setError('');
    }
  }, [isOpen, initialMode]);
  
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    agreeToPrivacy: false,
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      if (isLoginMode) {
        // 登录逻辑
        const result = await loginAPI(formData.username, formData.password);
        if (result.success) {
          if (onLogin) {
            onLogin(result.data.user, result.data.token);
          }
          // 重置表单
          setFormData({
            username: '',
            email: '',
            password: '',
            confirmPassword: '',
          });
          onClose();
        } else {
          setError(result.error || '登录失败');
        }
      } else {
        // 注册逻辑
        if (!formData.agreeToPrivacy) {
          setError('请先阅读并同意《隐私条款》');
          setIsLoading(false);
          return;
        }
        if (formData.password !== formData.confirmPassword) {
          setError('两次输入的密码不一致');
          setIsLoading(false);
          return;
        }
        if (formData.password.length < 6) {
          setError('密码长度至少6位');
          setIsLoading(false);
          return;
        }
        
        const result = await registerAPI(formData.username, formData.email, formData.password);
        if (result.success) {
          if (onRegister) {
            onRegister(result.data.user, result.data.token);
          }
          // 重置表单
          setFormData({
            username: '',
            email: '',
            password: '',
            confirmPassword: '',
            agreeToPrivacy: false,
          });
          onClose();
        } else {
          setError(result.error || '注册失败');
        }
      }
    } catch (err) {
      setError(err.message || '操作失败，请稍后重试');
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (e) => {
    const name = e.target.name;
    const value = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
    setFormData({
      ...formData,
      [name]: value,
    });
  };

  if (!isOpen) return null;

  return (
    <div className="auth-modal-overlay" onClick={onClose}>
      <div className="auth-modal" onClick={(e) => e.stopPropagation()}>
        <button className="auth-modal-close" onClick={onClose}>×</button>
        
        <div className="auth-modal-header">
          <h2>{isLoginMode ? '登录' : '注册'}</h2>
          <p>{isLoginMode ? '欢迎回来' : '创建新账号'}</p>
        </div>

        {error && (
          <div className="auth-error">
            {error}
          </div>
        )}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="auth-form-group">
            <label>用户名</label>
            <input
              type="text"
              name="username"
              value={formData.username}
              onChange={handleChange}
              placeholder="请输入用户名"
              required
            />
          </div>

          {!isLoginMode && (
            <div className="auth-form-group">
              <label>邮箱</label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                placeholder="请输入邮箱"
                required
              />
            </div>
          )}

          <div className="auth-form-group">
            <label>密码</label>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              placeholder="请输入密码"
              required
            />
          </div>

          {!isLoginMode && (
            <div className="auth-form-group">
              <label>确认密码</label>
              <input
                type="password"
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleChange}
                placeholder="请再次输入密码"
                required
              />
            </div>
          )}

          {!isLoginMode && (
            <div className="auth-form-group auth-form-group-checkbox">
              <label className="auth-privacy-label">
                <input
                  type="checkbox"
                  name="agreeToPrivacy"
                  checked={formData.agreeToPrivacy}
                  onChange={handleChange}
                />
                <span>我已阅读并同意<button type="button" className="auth-privacy-link" onClick={(e) => { e.preventDefault(); onOpenPrivacyPolicy?.(); }}>《隐私条款》</button></span>
              </label>
            </div>
          )}

          <button type="submit" className="auth-submit-btn" disabled={isLoading}>
            {isLoading ? '处理中...' : (isLoginMode ? '登录' : '注册')}
          </button>
        </form>

        <div className="auth-modal-footer">
          <button
            className="auth-mode-toggle"
            onClick={() => setIsLoginMode(!isLoginMode)}
          >
            {isLoginMode ? '还没有账号？立即注册' : '已有账号？立即登录'}
          </button>
        </div>
      </div>
    </div>
  );
}
