import { useState } from 'react';
import './CharacterSelector.css';

// 角色数据配置
const CHARACTERS = [
  {
    id: 'monkey',
    name: '孙悟空',
    roleClass: 'role-monkey',
    thumbnail: null,
    images: null,
    description: '图层化结构：头 / 身 / 手 / 腿'
  },
  {
    id: 'demon',
    name: '白骨精',
    roleClass: 'role-demon',
    thumbnail: null,
    images: null,
    description: '图层化结构：头 / 身 / 手 / 腿'
  },
  {
    id: 'character-1',
    name: '人物-1',
    roleClass: 'role-monkey',
    thumbnail: '/api/characters/人物-1/头.png',
    images: {
      head: '/api/characters/人物-1/头.png',
      body: '/api/characters/人物-1/上身.png',
      leftArm: '/api/characters/人物-1/左手.png',
      rightArm: '/api/characters/人物-1/右手.png',
      leftLeg: '/api/characters/人物-1/左腿.png',
      rightLeg: '/api/characters/人物-1/右腿.png'
    },
    description: '图层化结构：头 / 上身 / 左手 / 右手 / 左腿 / 右腿'
  }
];

function CharacterSelector({ characters = CHARACTERS, onSelect, selectedCharacterId }) {
  const [hoveredCharacter, setHoveredCharacter] = useState(null);

  const handleCharacterClick = (character) => {
    onSelect(character);
  };

  return (
    <div className="character-selector">
      <div className="character-selector-header">
        <h4>
          <span className="icon">角</span>
          选择角色
        </h4>
      </div>
      
      <div className="character-list">
        {characters.map(char => (
          <div
            key={char.id}
            className={`char-item ${selectedCharacterId === char.id ? 'selected' : ''}`}
            onClick={() => handleCharacterClick(char)}
            onMouseEnter={() => setHoveredCharacter(char.id)}
            onMouseLeave={() => setHoveredCharacter(null)}
          >
            <div className="char-thumbnail">
              {char.thumbnail ? (
                <img 
                  src={char.thumbnail} 
                  alt={char.name}
                  onError={(e) => {
                    e.target.style.display = 'none';
                  }}
                />
              ) : (
                <div className="char-placeholder">
                  <div className={`char-dot ${char.roleClass || ''}`}></div>
                </div>
              )}
              {selectedCharacterId === char.id && (
                <div className="selected-badge">中</div>
              )}
            </div>
            <span className="char-name">{char.name}</span>
            {char.description && (
              <span className="char-desc">{char.description}</span>
            )}
            
            {/* 悬停时显示角色信息 */}
            {hoveredCharacter === char.id && char.description && (
              <div className="character-preview">
                <div className="preview-title">角色说明</div>
                <div className="preview-text">{char.description}</div>
              </div>
            )}
          </div>
        ))}
      </div>
      
      <div className="character-tips">
        <p>点击角色可切换，悬停查看部件详情</p>
      </div>
    </div>
  );
}

export default CharacterSelector;

