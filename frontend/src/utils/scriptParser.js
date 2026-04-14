// 用来做关键词高亮的词表（可以之后再慢慢补充）
const KEYWORDS = [
  '起身', '站定', '挥手', '招手', '跳跃', '跳起',
  '行走', '慢走', '跑', '奔跑',
  '防御', '格挡',
  '鞠躬', '下拜',
  '指向', '指着',
  '举手', '抬手', '放下手',
  '打斗', '攻击', '出击'
];

/**
 * 根据关键词把文本切成若干段：
 * [{ text: '……', highlight: false }, { text: '起身', highlight: true }, ...]
 */
export function highlightKeywords(text) {
  if (!text) return [];

  const parts = [];
  let i = 0;

  while (i < text.length) {
    let matchedKeyword = null;

    // 尝试从当前下标匹配任意一个关键词
    for (const kw of KEYWORDS) {
      if (text.startsWith(kw, i)) {
        matchedKeyword = kw;
        break;
      }
    }

    if (matchedKeyword) {
      // 命中关键词，单独作为一段高亮
      parts.push({ text: matchedKeyword, highlight: true });
      i += matchedKeyword.length;
    } else {
      // 普通文本，往后扫，直到遇到下一个关键词
      const start = i;
      while (i < text.length) {
        const hasUpcomingKeyword = KEYWORDS.some(kw => text.startsWith(kw, i));
        if (hasUpcomingKeyword) break;
        i++;
      }
      const normalText = text.slice(start, i);
      if (normalText) {
        parts.push({ text: normalText, highlight: false });
      }
    }
  }

  return parts;
}

// 动作序列配置
const DEFAULT_ACTIONS = [
  { action: 'stand', label: '角色起身站定，完成亮相' },
  { action: 'walk',  label: '向前行走两步，接近对白位置' },
  { action: 'wave',  label: '抬手挥动，配合对白情绪' },
  { action: 'attack',label: '做出打斗/出击动作' },
  { action: 'jump',  label: '跳跃腾空，突出身法变化' },
  { action: 'bow',   label: '收势鞠躬，完成一小段表演' }
];

/**
 * AI 剧本解析接口
 */
export async function fakeParseScriptApi(text) {
  await new Promise(resolve => setTimeout(resolve, 800));

  const result = {
    title: 'AI 剧本解析结果',
    summary: '系统将当前剧本拆分为 6 个关键动作节点，用于驱动皮影角色在舞台上的连续表演。',
    scenes: '山林 / 庙宇 / 戏台',
    roles: '主角 / 反派 / 配角',
    rhythm: '由慢到快，再回落的节奏结构',
    emotions: '紧张、对抗、释然',
    actions: DEFAULT_ACTIONS.map((item, idx) => ({
      id: `action-${idx + 1}`,
      action: item.action,
      label: item.label
    }))
  };

  return result;
}

/**
 * 解析剧本文本，生成动作指令序列（保留原函数用于兼容）
 * @param {string} text - 输入的剧本文本
 * @returns {Array<string>} - 动作指令数组
 */
export function parseScriptToActions(text) {
  const actions = [];
  const lowerText = text.toLowerCase();
  
  // 动作关键词映射
  const actionKeywords = {
    'attack': ['打', '击', '劈', '砍', '刺', '攻', '战', '斗', '杀'],
    'jump': ['跳', '跃', '腾', '飞'],
    'walk': ['走', '行', '步', '移', '前', '后'],
    'run': ['跑', '奔', '追', '逃'],
    'defend': ['挡', '防', '守', '护'],
    'dance': ['舞', '蹈', '转', '旋'],
    'sit': ['坐', '蹲'],
    'stand': ['站', '立'],
    'wave': ['挥', '摆', '摇'],
    'bow': ['拜', '躬', '礼'],
    'point': ['指', '点'],
    'raise': ['举', '抬', '扬'],
    'lower': ['放', '降', '垂']
  };
  
  // 检测动作关键词
  for (const [action, keywords] of Object.entries(actionKeywords)) {
    for (const keyword of keywords) {
      if (lowerText.includes(keyword)) {
        // 检测重复次数（如"三打"）
        const regex = new RegExp(`(\\d+)?${keyword}`, 'g');
        const matches = text.match(regex);
        if (matches) {
          matches.forEach(match => {
            const numMatch = match.match(/\d+/);
            const count = numMatch ? parseInt(numMatch[0]) : 1;
            for (let i = 0; i < count; i++) {
              actions.push(action);
            }
          });
        } else {
          actions.push(action);
        }
        break; // 每个关键词只匹配一次
      }
    }
  }
  
  // 如果没有检测到任何动作，添加默认动作
  if (actions.length === 0) {
    actions.push('stand');
  }
  
  // 去重并保持顺序
  return [...new Set(actions)];
}

