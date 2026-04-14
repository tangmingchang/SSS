import React, { useState } from 'react';
import { useWorkbenchStore } from '../../../stores/workbenchStore';
import { API_BASE, resolveImageUrl } from '../../../utils/api';
import { IconStage } from '../../shared/Icons';
import './StationCommon.css';

/**
 * Stage Station（布景站）
 * 选择角色/道具/背景，舞台布局（拖拽到舞台）
 */
export default function StageStation({ allCharacters = [], allScenes = [], onAddToPersonal }) {
  const { orderTicket, stage, updateOrderTicket, updateStage, markStationCompleted, goToNextStation } = useWorkbenchStore();
  const [stageTab, setStageTab] = useState('character');
  const [characterSource, setCharacterSource] = useState('library');
  const [backgroundSource, setBackgroundSource] = useState('library');
  const [aiCharPrompt, setAiCharPrompt] = useState('');
  const [aiBgPrompt, setAiBgPrompt] = useState('');
  const [aiCharGenerating, setAiCharGenerating] = useState(false);
  const [aiBgGenerating, setAiBgGenerating] = useState(false);
  const [aiCharGenerated, setAiCharGenerated] = useState(null);
  const [aiBgGenerated, setAiBgGenerated] = useState(null);

  // 角色生成
  const handleGenerateCharacter = async () => {
    if (!aiCharPrompt.trim()) return;
    setAiCharGenerating(true);
    try {
      const res = await fetch(`${API_BASE}/api/generate_character`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: aiCharPrompt.trim() }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.success) {
        setAiCharGenerated(data);
        updateOrderTicket({ character: data });
        // 生成的角色追加到舞台，可自主增删
        const currentList = stage.characters || [];
        updateStage({ characters: [...currentList, data] });
      }
    } catch (err) {
      console.error('生成角色失败:', err);
    } finally {
      setAiCharGenerating(false);
    }
  };

  // 背景生成
  const handleGenerateBackground = async () => {
    if (!aiBgPrompt.trim()) return;
    setAiBgGenerating(true);
    try {
      const res = await fetch(`${API_BASE}/api/generate_background`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: aiBgPrompt.trim() }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.success) {
        setAiBgGenerated(data);
        updateOrderTicket({ background: data });
        updateStage({ background: data });
      }
    } catch (err) {
      console.error('生成背景失败:', err);
    } finally {
      setAiBgGenerating(false);
    }
  };

  // 资源库角色列表 = 公共/个人资源 + 本场 AI 生成的角色（舞台上已有的 AI 角色也可在资源库中点击再次添加）
  const charactersForLibrary = React.useMemo(() => {
    const list = [...allCharacters];
    const seen = new Set(list.map((c) => c.id));
    const stageChars = stage.characters || [];
    const aiFromStage = stageChars.filter((c) => c.id && String(c.id).startsWith('ai-'));
    aiFromStage.forEach((c) => {
      if (!seen.has(c.id)) {
        seen.add(c.id);
        list.unshift(c);
      }
    });
    if (aiCharGenerated && !seen.has(aiCharGenerated.id)) {
      list.unshift(aiCharGenerated);
    }
    return list;
  }, [allCharacters, stage.characters, aiCharGenerated]);

  const hasCharacters = (stage.characters?.length > 0) || !!orderTicket.character;
  const handleNext = () => {
    if (hasCharacters && orderTicket.background) {
      markStationCompleted('stage');
      goToNextStation();
    }
  };

  return (
    <div className="station-content stage-station">
      <h3 className="station-title">
        <IconStage size={18} />
        <span>布景站</span>
      </h3>
      <p className="station-desc">
        选择角色和背景，可以拖拽到舞台进行布局
      </p>

      <div className="stage-tabs">
        <button
          className={stageTab === 'character' ? 'active' : ''}
          onClick={() => setStageTab('character')}
        >
          角色
        </button>
        <button
          className={stageTab === 'background' ? 'active' : ''}
          onClick={() => setStageTab('background')}
        >
          背景
        </button>
      </div>

      {stageTab === 'character' && (
        <div className="stage-selector">
          <div className="source-tabs">
            <button
              className={characterSource === 'library' ? 'active' : ''}
              onClick={() => setCharacterSource('library')}
            >
              资源库
            </button>
            <button
              className={characterSource === 'ai' ? 'active' : ''}
              onClick={() => setCharacterSource('ai')}
            >
              AI 生成
            </button>
          </div>

          {characterSource === 'library' ? (
            <>
              <select
                className="wb-select"
                value={orderTicket.character?.id || ''}
                onChange={(e) => {
                  const selected = charactersForLibrary.find((c) => (c.id || '') === e.target.value);
                  if (selected) {
                    updateOrderTicket({ character: selected });
                    // 追加到舞台，支持多人物（不替换已有角色）
                    const currentList = stage.characters || [];
                    if (!currentList.some((c) => (c.id ?? '') === (selected.id ?? ''))) {
                      updateStage({ characters: [...currentList, selected] });
                    }
                  }
                }}
              >
                <option value="">请选择角色（可多选添加）</option>
                {charactersForLibrary.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
        
            </>
          ) : (
            <>
              <textarea
                className="wb-textarea"
                value={aiCharPrompt}
                onChange={(e) => setAiCharPrompt(e.target.value)}
                placeholder="例：旦角，凤冠，明黄+翠绿，扇，团花（身份/头饰/主色/道具/纹样）"
                rows={2}
              />
              <div className="generated-actions" style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
                <button
                  className="btn-primary"
                  onClick={handleGenerateCharacter}
                  disabled={!aiCharPrompt.trim() || aiCharGenerating}
                >
                  {aiCharGenerating ? '生成中...' : '生成角色'}
                </button>
                {aiCharGenerated && onAddToPersonal && (
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => {
                      onAddToPersonal('characters', aiCharGenerated);
                      alert('已保存到个人资源库');
                    }}
                  >
                    下载到个人资源库
                  </button>
                )}
              </div>
              {aiCharGenerated && (
                <div className="generated-preview">
                  <img src={resolveImageUrl(aiCharGenerated.thumbnail || aiCharGenerated.image_url)} alt={aiCharGenerated.name} />
                  <p>{aiCharGenerated.name}</p>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {stageTab === 'background' && (
        <div className="stage-selector">
          <div className="source-tabs">
            <button
              className={backgroundSource === 'library' ? 'active' : ''}
              onClick={() => setBackgroundSource('library')}
            >
              资源库
            </button>
            <button
              className={backgroundSource === 'ai' ? 'active' : ''}
              onClick={() => setBackgroundSource('ai')}
            >
              AI 生成
            </button>
          </div>

          {backgroundSource === 'library' ? (
            <select
              className="wb-select"
              value={orderTicket.background?.id || ''}
              onChange={(e) => {
                const selected = allScenes.find((s) => s.id === e.target.value);
                if (selected) {
                  updateOrderTicket({ background: selected });
                  updateStage({ background: selected });
                }
              }}
            >
              <option value="">请选择背景</option>
              {allScenes.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          ) : (
            <>
              <textarea
                className="wb-textarea"
                value={aiBgPrompt}
                onChange={(e) => setAiBgPrompt(e.target.value)}
                placeholder="描述想要的背景..."
                rows={2}
              />
              <div className="generated-actions" style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
                <button
                  className="btn-primary"
                  onClick={handleGenerateBackground}
                  disabled={!aiBgPrompt.trim() || aiBgGenerating}
                >
                  {aiBgGenerating ? '生成中...' : '生成背景'}
                </button>
                {aiBgGenerated && onAddToPersonal && (
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => {
                      onAddToPersonal('scenes', aiBgGenerated);
                      alert('已保存到个人资源库');
                    }}
                  >
                    下载到个人资源库
                  </button>
                )}
              </div>
              {aiBgGenerated && (
                <div className="generated-preview">
                  <img src={resolveImageUrl(aiBgGenerated.thumbnail || aiBgGenerated.url)} alt={aiBgGenerated.name} />
                  <p>{aiBgGenerated.name}</p>
                </div>
              )}
            </>
          )}
        </div>
      )}

      <div className="station-actions">
        <button
          className="btn-primary"
          onClick={handleNext}
          disabled={!hasCharacters || !orderTicket.background}
        >
          下一站：演出 →
        </button>
      </div>
    </div>
  );
}
