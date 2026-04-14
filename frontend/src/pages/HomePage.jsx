import { useEffect, useRef } from 'react';
import './HomePage.css';

function HomePage({ onStart }) {
  const pageRef = useRef(null);

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!pageRef.current) return;
      
      const rect = pageRef.current.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 100;
      const y = ((e.clientY - rect.top) / rect.height) * 100;
      
      pageRef.current.style.setProperty('--mouse-x', `${x}%`);
      pageRef.current.style.setProperty('--mouse-y', `${y}%`);
    };

    const pageElement = pageRef.current;
    if (pageElement) {
      pageElement.addEventListener('mousemove', handleMouseMove);
      
      return () => {
        pageElement.removeEventListener('mousemove', handleMouseMove);
      };
    }
  }, []);

  return (
    <div className="home-page" ref={pageRef} role="main">
      <div className="mouse-glow" aria-hidden="true"></div>
      <div className="home-hero">
        <div className="home-left">
          <h1 className="home-title">
            <span className="title-icon" aria-hidden="true">影</span>
            动未来
          </h1>

          <h2 className="home-subtitle">皮影戏智能生成与教学平台</h2>

          <p className="home-desc">
            基于AI与物理引擎的皮影戏智能生成与交互传承系统
            <br />
            让传统非遗在数字时代焕发新活力
          </p>

          <div className="home-cta">
            <button type="button" className="btn-start" onClick={onStart} aria-label="开始创作，进入工作台">
              开始创作
            </button>
            <div className="home-hint">建议使用电脑端体验更完整的舞台效果</div>
          </div>
        </div>

        <div className="home-right">
          <div className="home-visual" aria-label="创作流程预览">
            <div className="visual-title">创作流程</div>

            <ol className="home-timeline" aria-label="从想法到视频的流程">
              <li className="timeline-item">
                <div className="timeline-dot" aria-hidden="true"></div>
                <span>输入想法</span>
              </li>
              <li className="timeline-arrow" aria-hidden="true">→</li>
              <li className="timeline-item">
                <div className="timeline-dot" aria-hidden="true"></div>
                <span>AI生成剧本</span>
              </li>
              <li className="timeline-arrow" aria-hidden="true">→</li>
              <li className="timeline-item">
                <div className="timeline-dot" aria-hidden="true"></div>
                <span>选择角色</span>
              </li>
              <li className="timeline-arrow" aria-hidden="true">→</li>
              <li className="timeline-item">
                <div className="timeline-dot" aria-hidden="true"></div>
                <span>生成视频</span>
              </li>
            </ol>

            <div className="visual-note">
              中央舞台将实时预览角色、灯光与字幕效果
            </div>
          </div>
        </div>
      </div>

      <div className="home-features" aria-label="核心能力">
        <div className="feature-card" tabIndex={0}>
          <div className="feature-icon" aria-hidden="true">文</div>
          <h3>智能剧本生成</h3>
          <p>输入想法，AI自动生成单场景剧本</p>
        </div>

        <div className="feature-card" tabIndex={0}>
          <div className="feature-icon" aria-hidden="true">角</div>
          <h3>丰富角色库</h3>
          <p>公共资源库 + 个人资源库，支持自定义</p>
        </div>

        <div className="feature-card" tabIndex={0}>
          <div className="feature-icon" aria-hidden="true">戏</div>
          <h3>一键生成视频</h3>
          <p>自动匹配字幕，输出完整皮影戏视频</p>
        </div>
      </div>
    </div>
  );
}

export default HomePage;
