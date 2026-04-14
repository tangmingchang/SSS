import { useState, useEffect, useRef, useCallback } from 'react';
import './ActionEditor.css';

/**
 * 动作编辑器组件
 * 从剧本中提取动作节点，允许用户添加、删除、编辑
 */
function ActionEditor({ script, actionSequence, onChange }) {
  const [actions, setActions] = useState([]);
  const isUserActionRef = useRef(false); // 标记是否是用户操作
  const onChangeRef = useRef(onChange); // 使用ref保存onChange，避免依赖变化

  // 更新onChange引用
  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  // 从剧本中提取所有动作节点（仅在script内容变化时执行）
  const scriptRef = useRef(null);
  useEffect(() => {
    // 比较script内容，避免引用变化导致重新初始化
    const scriptKey = script ? JSON.stringify({
      scenes: script.scenes?.map(s => ({
        scene_number: s.scene_number,
        actions: s.actions,
        emotion: s.emotion
      }))
    }) : null;
    
    if (scriptKey === scriptRef.current) {
      return; // script内容未变化，不重新初始化
    }
    
    scriptRef.current = scriptKey;

    if (!script || !script.scenes) {
      setActions([]);
      return;
    }

    console.log('从剧本提取动作节点');
    isUserActionRef.current = false; // 标记为初始化，不是用户操作
    const extractedActions = [];
    script.scenes.forEach((scene) => {
      if (scene.actions && Array.isArray(scene.actions)) {
        scene.actions.forEach((actionText, idx) => {
          extractedActions.push({
            id: `scene-${scene.scene_number}-action-${idx}`,
            sceneNumber: scene.scene_number,
            sceneDescription: scene.description,
            actionText: actionText,
            emotion: scene.emotion || '',
            original: true, // 标记为从剧本中提取的原始动作
          });
        });
      }
    });

    console.log(`提取了 ${extractedActions.length} 个动作节点`);
    setActions(extractedActions);
    // 初始化完成后，标记为可以触发onChange
    setTimeout(() => {
      isUserActionRef.current = true;
      if (onChangeRef.current && extractedActions.length > 0) {
        onChangeRef.current(extractedActions);
      }
    }, 100);
  }, [script]); // 只在script变化时执行

  // 当actions变化时，通知父组件（仅用户操作时）
  useEffect(() => {
    if (onChangeRef.current && isUserActionRef.current && actions.length > 0) {
      onChangeRef.current(actions);
    }
  }, [actions]); // 只在actions变化时执行

  // 添加新动作
  const handleAddAction = (e) => {
    if (e) {
      e.stopPropagation();
      e.preventDefault();
    }
    console.log('添加动作');
    isUserActionRef.current = true; // 标记为用户操作
    setActions(prevActions => {
      const newAction = {
        id: `action-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        sceneNumber: prevActions.length > 0 ? prevActions[prevActions.length - 1].sceneNumber : 1,
        sceneDescription: '',
        actionText: '挑线-中速上挑-中幅',
        emotion: '',
        original: false,
      };
      console.log('新动作添加，当前动作数:', prevActions.length + 1);
      return [...prevActions, newAction];
    });
  };


  // 更新动作文本
  const handleUpdateAction = (id, field, value) => {
    isUserActionRef.current = true; // 标记为用户操作
    setActions(prevActions =>
      prevActions.map((a) => {
        if (a.id === id) {
          return { ...a, [field]: value };
        }
        return a;
      })
    );
  };

  // 移动动作位置
  const handleMoveAction = (id, direction, e) => {
    if (e) {
      e.stopPropagation();
      e.preventDefault();
    }
    console.log(`移动动作: ${id}, 方向: ${direction}`);
    isUserActionRef.current = true; // 标记为用户操作
    setActions(prevActions => {
      const index = prevActions.findIndex((a) => a.id === id);
      if (index === -1) {
        console.warn('未找到动作:', id);
        return prevActions;
      }

      const newActions = [...prevActions];
      if (direction === 'up' && index > 0) {
        [newActions[index - 1], newActions[index]] = [
          newActions[index],
          newActions[index - 1],
        ];
        console.log(`动作上移: ${index} -> ${index - 1}`);
      } else if (direction === 'down' && index < newActions.length - 1) {
        [newActions[index], newActions[index + 1]] = [
          newActions[index + 1],
          newActions[index],
        ];
        console.log(`动作下移: ${index} -> ${index + 1}`);
      } else {
        console.log('无法移动: 已在边界');
        return prevActions;
      }
      return newActions;
    });
  };

  // 删除动作
  const handleDeleteAction = (id, e) => {
    if (e) {
      e.stopPropagation();
      e.preventDefault();
    }
    console.log('删除动作:', id);
    isUserActionRef.current = true; // 标记为用户操作
    setActions(prevActions => {
      const filtered = prevActions.filter((a) => a.id !== id);
      console.log(`删除后动作数: ${filtered.length} (原: ${prevActions.length})`);
      return filtered;
    });
  };

  if (!script || !script.scenes) {
    return (
      <div className="action-editor-empty">
        <p>请先生成剧本，然后在此编辑动作序列</p>
      </div>
    );
  }

  return (
    <div className="action-editor">
      <div className="action-editor-header">
        <h4>动作序列编辑</h4>
        <button
          type="button"
          className="btn-secondary btn-small"
          onClick={(e) => handleAddAction(e)}
        >
          + 添加动作
        </button>
      </div>

      <div className="action-editor-list">
        {actions.length === 0 ? (
          <div className="action-editor-empty">
            <p>暂无动作，请先添加动作</p>
          </div>
        ) : (
          actions.map((action, index) => (
            <div
              key={action.id}
              className={`action-item ${action.original ? 'action-item-original' : 'action-item-custom'}`}
            >
              <div className="action-item-header">
                <span className="action-item-number">#{index + 1}</span>
                {action.original && (
                  <span className="action-item-badge">来自剧本</span>
                )}
                {action.sceneNumber && (
                  <span className="action-item-scene">
                    场景 {action.sceneNumber}
                  </span>
                )}
                <div className="action-item-controls">
                  <button
                    type="button"
                    className="btn-icon"
                    onClick={(e) => handleMoveAction(action.id, 'up', e)}
                    disabled={index === 0}
                    title="上移"
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    className="btn-icon"
                    onClick={(e) => handleMoveAction(action.id, 'down', e)}
                    disabled={index === actions.length - 1}
                    title="下移"
                  >
                    ↓
                  </button>
                  <button
                    type="button"
                    className="btn-icon btn-icon-danger"
                    onClick={(e) => handleDeleteAction(action.id, e)}
                    title="删除"
                  >
                    ×
                  </button>
                </div>
              </div>

              <div className="action-item-body">
                <div className="action-item-field">
                  <label>动作指令：</label>
                  <input
                    type="text"
                    value={action.actionText}
                    onChange={(e) =>
                      handleUpdateAction(action.id, 'actionText', e.target.value)
                    }
                    placeholder="例如：挑线-快速上挑-大幅"
                    className="action-input"
                  />
                </div>

                {action.sceneDescription && (
                  <div className="action-item-description">
                    <small>{action.sceneDescription}</small>
                  </div>
                )}

                {action.emotion && (
                  <div className="action-item-emotion">
                    <span className="emotion-tag">情绪：{action.emotion}</span>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      <div className="action-editor-footer">
        <p className="action-editor-hint">
          提示：动作格式为"技法-速度-幅度"，例如：挑线-快速上挑-大幅、压签-缓慢下压-小幅、转签-中速旋转-中幅
        </p>
      </div>
    </div>
  );
}

export default ActionEditor;
