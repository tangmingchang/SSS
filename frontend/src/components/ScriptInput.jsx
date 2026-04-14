import { useState } from 'react';
import { fakeParseScriptApi, highlightKeywords } from '../utils/scriptParser';
import './ScriptInput.css';

function ScriptInput({ onSubmit, onAiResult }) {
  const [text, setText] = useState('');
  const [highlightedParts, setHighlightedParts] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [aiResult, setAiResult] = useState(null);

  const handleTextChange = (e) => {
    const newText = e.target.value;
    setText(newText);
    // 实时高亮关键词
    if (newText.trim()) {
      setHighlightedParts(highlightKeywords(newText));
    } else {
      setHighlightedParts([]);
    }
  };

  const handleSubmit = async () => {
    if (text.trim() === '') return;
    
    setIsLoading(true);
    
    try {
      // 调用虚假后端API（固定返回结果）
      const result = await fakeParseScriptApi(text);
      setAiResult(result);
      
      // 提取动作序列传递给父组件
      const actions = result.actions.map(a => a.action);
      onSubmit(text, actions);
      
      // 传递完整AI结果给父组件
      if (onAiResult) {
        onAiResult(result);
      }
    } catch (error) {
      console.error('AI解析失败:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      handleSubmit();
    }
  };

  return (
    <div className="script-input">
      <div className="script-input-header">
        <h3>
          <span className="icon">文</span>
          剧本输入
        </h3>
      </div>
      
      <div className="script-textarea-container">
        <textarea
          value={text}
          onChange={handleTextChange}
          onKeyPress={handleKeyPress}
          placeholder="请输入剧本内容，例如：孙悟空三打白骨精..."
          className="script-textarea"
          rows="6"
        />
        
        {/* 关键词高亮预览 */}
        {highlightedParts.length > 0 && (
          <div className="keyword-preview">
            <span className="preview-label">检测到的动作：</span>
            {highlightedParts
              .filter(part => part.highlight)
              .map((part, idx) => (
                <span key={idx} className="keyword-tag">{part.text}</span>
              ))}
          </div>
        )}
      </div>
      
      <button 
        onClick={handleSubmit} 
        className="generate-btn"
        disabled={!text.trim() || isLoading}
      >
        <span className="btn-icon">{isLoading ? '...' : '生'}</span>
        {isLoading ? '正在调用 AI 模型…' : '生成动作'}
      </button>
      
      <div className="script-tips">
        <p>提示：按 Ctrl+Enter 快速生成动作</p>
      </div>

      {/* AI解析结果展示 */}
      {aiResult && (
        <div className="ai-result-panel">
          <div className="ai-result-title">{aiResult.title}</div>
          <div className="ai-result-summary">{aiResult.summary}</div>
          <div className="ai-tag-row">
            <span className="ai-tag">场景：{aiResult.scenes}</span>
            <span className="ai-tag">角色：{aiResult.roles}</span>
            <span className="ai-tag">节奏：{aiResult.rhythm}</span>
            {aiResult.emotions && <span className="ai-tag">情绪：{aiResult.emotions}</span>}
          </div>
          <div className="action-list">
            <div className="action-list-title">动作序列：</div>
            {aiResult.actions.map((act, idx) => (
              <div key={act.id} className="action-item">
                <div className="action-dot"></div>
                <div>步骤 {idx + 1}：{act.label}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default ScriptInput;

