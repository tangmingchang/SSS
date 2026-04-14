import { useState } from 'react';
import { API_BASE } from '../utils/api';
import './AiGeneratorPage.css';

function AiGeneratorPage({ onGenerateToPersonal }) {
  const [prompt, setPrompt] = useState('');
  const [type, setType] = useState('characters');
  const [generated, setGenerated] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [error, setError] = useState(null);

  const types = [
    { id: 'characters', label: '角色', icon: '角' },
    { id: 'scenes', label: '场景', icon: '景' },
    { id: 'motions', label: '动作', icon: '动' },
    { id: 'tools', label: '工具', icon: '具' },
  ];

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    
    setIsGenerating(true);
    setGenerationProgress(0);
    setGenerated(null);
    setError(null);
    
    // 模拟进度（真实请求较慢）
    const progressInterval = setInterval(() => {
      setGenerationProgress((prev) => Math.min(prev + 5, 90));
    }, 500);

    try {
      // 角色和场景走通义万相文生图 API
      const supportedTypes = ['characters', 'scenes'];
      const apiType = supportedTypes.includes(type) ? type : 'characters';
      
      const res = await fetch(`${API_BASE}/api/generate_image`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: prompt.trim(), type: apiType }),
      });
      const data = await res.json().catch(() => ({}));
      
      clearInterval(progressInterval);
      setGenerationProgress(100);
      
      if (!res.ok) {
        setError(data.error || '生成失败');
        return;
      }
      
      if (data.success) {
        const result = {
          id: data.id,
          name: data.name,
          type: apiType,
          prompt: data.prompt,
          url: data.image_url || data.url,
          thumbnail: data.thumbnail || data.image_url || data.url,
          images: data.image_url ? { full: data.image_url } : undefined,
        };
        setGenerated(result);
      } else {
        setError(data.error || '生成失败');
      }
    } catch (err) {
      clearInterval(progressInterval);
      setError(err.message || '无法连接后端，请确认已启动并已下载模型');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSave = () => {
    if (generated) {
      onGenerateToPersonal(type, generated);
      setGenerated(null);
      setPrompt('');
      alert('已保存到个人资源库！');
    }
  };

  return (
    <div className="ai-generator-page">
      <h1 className="page-title">AI 生成</h1>
      <p className="page-subtitle">输入描述，AI自动生成资源</p>

      <div className="ai-generator">
        <div className="ai-input-section">
          <h3>选择生成类型</h3>
          <div className="type-selector">
            {types.map((t) => (
              <button
                key={t.id}
                className={`type-btn ${type === t.id ? 'active' : ''}`}
                onClick={() => setType(t.id)}
              >
                <span className="type-label">{t.label}</span>
              </button>
            ))}
          </div>

          <h3 style={{ marginTop: '24px' }}>输入描述</h3>
          <textarea
            className="ai-textarea"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder={type === 'characters' ? '例如：皮影风格孙悟空，手持金箍棒' : type === 'scenes' ? '例如：夜晚荒山古庙场景' : `描述你想要生成的${types.find(t => t.id === type)?.label}`}
            rows={6}
          />
          {(type === 'motions' || type === 'tools') && (
            <p style={{ fontSize: 12, color: 'rgba(255,220,160,0.7)', marginTop: 8 }}>
              当前仅支持角色、场景的 AI 生成，动作与工具敬请期待
            </p>
          )}

          {error && <p className="ai-error" style={{ color: '#e74c3c', marginTop: 8 }}>{error}</p>}
          <button
            className="btn-generate"
            onClick={handleGenerate}
            disabled={!prompt.trim() || isGenerating || (type !== 'characters' && type !== 'scenes')}
          >
            {isGenerating ? '生成中...' : '生成资源'}
          </button>
        </div>

        <div className="ai-result-section">
          <h3>生成结果</h3>
          {isGenerating ? (
            <div className="ai-loading">
              <div className="ai-loading-spinner">
                <div className="spinner-ring"></div>
                <div className="spinner-ring"></div>
                <div className="spinner-ring"></div>
              </div>
              <div className="ai-loading-text">正在生成{types.find(t => t.id === type)?.label}...</div>
              <div className="ai-loading-progress">
                <div
                  className="ai-loading-progress-bar"
                  style={{ width: `${generationProgress}%` }}
                ></div>
                <span className="ai-loading-progress-text">
                  {Math.round(generationProgress)}%
                </span>
              </div>
              <div className="ai-loading-steps">
                <div className={generationProgress > 20 ? 'step-done' : 'step-pending'}>
                  ✓ 分析描述内容
                </div>
                <div className={generationProgress > 50 ? 'step-done' : 'step-pending'}>
                  ✓ AI模型生成
                </div>
                <div className={generationProgress > 80 ? 'step-done' : 'step-pending'}>
                  {generationProgress > 80 ? '✓' : '○'} 优化与渲染...
                </div>
              </div>
            </div>
          ) : generated ? (
            <div className="result-card">
              <div className="result-header">
                <h4>{generated.name}</h4>
                <span className="result-type">{types.find(t => t.id === type)?.label}</span>
              </div>
              <p className="result-prompt">描述：{generated.prompt}</p>
              {(generated.url || generated.thumbnail) ? (
                <div className="result-image">
                  <img 
                    src={(generated.url || generated.thumbnail).startsWith('http') ? (generated.url || generated.thumbnail) : `${API_BASE}${generated.url || generated.thumbnail}`} 
                    alt={generated.name}
                    style={{
                      width: '100%',
                      maxHeight: '300px',
                      objectFit: 'contain',
                      borderRadius: '8px',
                      border: '1px solid rgba(255, 220, 160, 0.3)',
                    }}
                  />
                </div>
              ) : (
                <div className="result-placeholder">
                  <div className="placeholder-icon">智</div>
                  <div className="placeholder-text">AI生成内容</div>
                </div>
              )}
              <button className="btn-save" onClick={handleSave}>
                保存到个人资源库
              </button>
            </div>
          ) : (
            <div className="result-empty">
              <div className="empty-icon">智</div>
              <p>输入描述并点击"生成资源"开始</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default AiGeneratorPage;
