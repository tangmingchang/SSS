import React from 'react';
import './GroupBoard.css';

/**
 * 分组看板：灯光组/道具组/表演组/音乐组/宣传组
 * groups: { id, name, description, members?: [{ user: { name } }] }[]
 */
export default function GroupBoard({ groups = [], className = '' }) {
  const defaultGroups = [
    { name: '灯光组', description: '灯要几个、灯放哪更清楚、举灯太累怎么解决' },
    { name: '道具组', description: '背景要不要做成移动、用什么颜料不刮花、关节如何灵活' },
    { name: '表演组', description: '站着还是坐着、两手操控三根杆、如何快速切换场景' },
    { name: '音乐组', description: '配乐与节奏、锣鼓点与丝竹' },
    { name: '宣传组', description: '海报与展示、记录与复盘' },
  ];

  const list = groups.length > 0
    ? groups
    : defaultGroups.map((g, i) => ({ id: `default-${i}`, name: g.name, description: g.description, members: [] }));

  return (
    <div className={`group-board ${className}`}>
      <div className="group-board-title">分组</div>
      <div className="group-board-cards">
        {list.map((g) => (
          <div key={g.id || g.name} className="group-card">
            <div className="group-title">{g.name}</div>
            <div className="group-desc">{g.description || '任务：见课时探究卡'}</div>
            <div className="group-members">
              {(g.members || []).map((m) => (
                <span key={m.user?.id || m.userId || m.id} className="chip">
                  {m.user?.name || m.user?.username || '组员'}
                </span>
              ))}
              {(g.members?.length ?? 0) === 0 && (
                <span className="chip chip-empty">暂无成员</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
