"""
剧本生成与指令转化模块
支持通义千问（DashScope）或 OpenAI 生成剧本，将文本指令转化为动作序列

基于科学研究论文：
1. "Kinematic dataset of actors expressing emotions" (s41597-020-00635-7)
2. Motion-X Dataset: A Large-scale 3D Expressive Whole-body Human Motion Dataset
3. "eHeritage of Shadow Puppetry" (eHeritage_of_Shadow_Puppetry_Creation_and_Manipulation.pdf)
4. "Chinese Shadow Puppetry with Kinect" (978-3-642-33863-2_35.pdf)
"""

import json
import os
import re
import yaml
from typing import Dict, List, Optional
from pathlib import Path

# 通义千问（阿里云 DashScope）
try:
    from dashscope import Generation
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False
    Generation = None

# OpenAI（可选）
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None


class ScriptGenerator:
    """剧本生成器（优先通义千问，其次 OpenAI，无密钥时模拟模式）"""

    def __init__(self,
                 api_key: Optional[str] = None,
                 model: str = "gpt-4",
                 tongyi_api_key: Optional[str] = None,
                 tongyi_model: str = "qwen-plus"):
        """
        Args:
            api_key: OpenAI API 密钥（可选）
            model: OpenAI 模型名
            tongyi_api_key: 通义千问 API Key（阿里云 DashScope，优先使用）
            tongyi_model: 通义模型，如 qwen-plus / qwen-turbo / qwen-max
        """
        self.model = model
        self.tongyi_model = tongyi_model
        self.client = None
        self.provider = None  # "tongyi" | "openai" | None(模拟)

        if tongyi_api_key and tongyi_api_key.strip() and DASHSCOPE_AVAILABLE:
            self.tongyi_api_key = tongyi_api_key.strip()
            self.provider = "tongyi"
        elif api_key and api_key.strip() and OPENAI_AVAILABLE:
            self.client = OpenAI(api_key=api_key.strip())
            self.provider = "openai"
        else:
            if not (tongyi_api_key and tongyi_api_key.strip()):
                print("提示: 未设置通义千问 API Key（环境变量 DASHSCOPE_API_KEY），将使用模拟模式")
            elif not DASHSCOPE_AVAILABLE:
                print("提示: 请安装 dashscope: pip install dashscope")
            self.provider = None

        self.emotion_config = self._load_emotion_config()
        self.action_rules = self._load_action_rules()
    
    def _load_emotion_config(self) -> Dict:
        """从YAML配置文件加载情绪-动作映射（基于科学研究）"""
        config_path = Path(__file__).parent.parent.parent / "configs" / "emotion_action_mapping.yaml"
        try:
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    print(f"✓ 已加载情绪配置文件: {config_path}")
                    return config
            else:
                print(f"⚠ 配置文件不存在: {config_path}，将使用默认规则")
        except Exception as e:
            print(f"⚠ 无法加载情绪配置文件 {config_path}: {e}，将使用默认规则")
        return {}
    
    def _load_action_rules(self) -> Dict[str, List[str]]:
        """加载动作规则库（情绪词映射到动作序列）
        
        优先从配置文件加载，如果配置文件不存在或加载失败，则使用默认规则
        默认规则基于科学研究论文，但建议使用配置文件以获得更完整的映射
        """
        # 尝试从配置文件加载
        if self.emotion_config and 'emotion_to_actions' in self.emotion_config:
            rules = {}
            for emotion, config in self.emotion_config['emotion_to_actions'].items():
                if isinstance(config, dict) and 'actions' in config:
                    rules[emotion] = config['actions']
            if rules:
                print(f"✓ 从配置文件加载了 {len(rules)} 个情绪-动作映射")
                return rules
        
        # 如果配置文件加载失败，使用基于研究的默认规则
        print("使用基于研究的默认动作规则")
        return {
            # ========== 基本情绪（基于Ekman理论）==========
            "快乐": [
                "挑线-快速上挑-中幅",
                "转签-快速旋转-中幅",
                "挑线-快速上挑-中幅",
                "转签-快速旋转-中幅",
                "挑线-快速上挑-中幅"
            ],
            "悲伤": [
                "压签-缓慢下压-小幅",
                "转签-缓慢旋转-小幅",
                "挑线-缓慢上挑-小幅",
                "压签-保持下压-静止",
                "转签-缓慢旋转-小幅"
            ],
            "愤怒": [
                "挑线-快速上挑-大幅",
                "压签-快速下压-大幅",
                "转签-快速旋转-大幅",
                "挑线-快速上挑-大幅",
                "压签-快速下压-大幅"
            ],
            "恐惧": [
                "压签-快速下压-中幅",
                "转签-快速旋转-中幅",
                "挑线-快速上挑-中幅",
                "压签-快速下压-中幅"
            ],
            "厌恶": [
                "压签-缓慢下压-中幅",
                "转签-缓慢旋转-中幅",
                "挑线-缓慢上挑-中幅",
                "压签-缓慢下压-中幅"
            ],
            "惊讶": [
                "挑线-快速上挑-大幅",
                "保持-保持姿势-静止",
                "转签-快速旋转-中幅",
                "挑线-快速上挑-中幅"
            ],
            "中性": [
                "保持-保持姿势-静止",
                "转签-缓慢旋转-小幅",
                "保持-保持姿势-静止"
            ],
            # ========== 扩展情绪 ==========
            "悲怆": [
                "压签-缓慢下压-小幅",
                "转签-缓慢旋转-小幅",
                "挑线-缓慢上挑-小幅",
                "压签-保持下压-静止",
                "转签-缓慢旋转-小幅"
            ],
            "忧伤": [
                "压签-缓慢下压-小幅",
                "转签-缓慢旋转-小幅",
                "挑线-缓慢上挑-小幅",
                "压签-保持下压-静止"
            ],
            "欢快": [
                "挑线-快速上挑-中幅",
                "转签-快速旋转-中幅",
                "挑线-快速上挑-中幅",
                "转签-快速旋转-中幅",
                "挑线-快速上挑-中幅"
            ],
            "喜悦": [
                "挑线-快速上挑-中幅",
                "转签-快速旋转-中幅",
                "挑线-快速上挑-中幅",
                "转签-快速旋转-中幅"
            ],
            "愤怒": [
                "挑线-快速上挑-大幅",
                "压签-快速下压-大幅",
                "转签-快速旋转-大幅",
                "挑线-快速上挑-大幅",
                "压签-快速下压-大幅"
            ],
            "紧张": [
                "挑线-快速上挑-中幅",
                "压签-快速下压-中幅",
                "转签-快速旋转-中幅",
                "挑线-快速上挑-中幅"
            ],
            "平静": [
                "压签-缓慢下压-小幅",
                "保持-保持姿势-静止",
                "转签-缓慢旋转-小幅",
                "压签-缓慢下压-小幅"
            ],
            "激动": [
                "挑线-快速上挑-中幅",
                "转签-快速旋转-中幅",
                "挑线-快速上挑-中幅",
                "转签-快速旋转-中幅"
            ],
            "恐惧": [
                "压签-快速下压-中幅",
                "转签-快速旋转-中幅",
                "挑线-快速上挑-中幅",
                "压签-快速下压-中幅"
            ],
            "兴奋": [
                "挑线-快速上挑-大幅",
                "转签-快速旋转-大幅",
                "挑线-快速上挑-大幅",
                "转签-快速旋转-大幅",
                "挑线-快速上挑-大幅"
            ],
            "满足": [
                "压签-缓慢下压-小幅",
                "保持-保持姿势-静止",
                "转签-缓慢旋转-小幅"
            ],
            "失望": [
                "压签-缓慢下压-小幅",
                "保持-保持姿势-静止",
                "压签-缓慢下压-小幅"
            ],
            # 兼容旧的动作词（向后兼容）
            "打斗": [
                "挑线-快速上挑-大幅",
                "压签-快速下压-大幅",
                "转签-快速旋转-大幅",
                "挑线-快速上挑-大幅",
                "压签-快速下压-大幅",
                "转签-快速旋转-大幅"
            ],
            "行走": [
                "挑线-左腿上抬-中幅",
                "压签-左腿下压-中幅",
                "挑线-右腿上抬-中幅",
                "压签-右腿下压-中幅",
                "挑线-左腿上抬-中幅",
                "压签-左腿下压-中幅"
            ],
            "挥手": [
                "挑线-手臂上抬-中幅",
                "转签-手臂旋转-中幅",
                "压签-手臂下压-中幅",
                "挑线-手臂上抬-中幅",
                "转签-手臂旋转-中幅"
            ],
            "鞠躬": [
                "压签-身体前倾-大幅",
                "保持-保持姿势-静止",
                "保持-保持姿势-静止",
                "挑线-身体恢复-中幅"
            ],
            "跳跃": [
                "挑线-快速上挑-大幅",
                "保持-空中停留-静止",
                "压签-快速下压-大幅",
                "保持-落地缓冲-静止"
            ],
            "旋转": [
                "转签-快速旋转-大幅",
                "转签-快速旋转-大幅",
                "转签-快速旋转-大幅",
                "转签-快速旋转-大幅"
            ],
            "攻击": [
                "挑线-快速上挑-大幅",
                "压签-快速下压-大幅",
                "转签-快速旋转-大幅",
                "挑线-快速上挑-大幅"
            ],
            "防御": [
                "压签-缓慢下压-中幅",
                "保持-保持姿势-静止",
                "转签-缓慢旋转-小幅",
                "压签-缓慢下压-中幅"
            ],
            "逃跑": [
                "挑线-快速上挑-中幅",
                "压签-快速下压-中幅",
                "挑线-快速上挑-中幅",
                "压签-快速下压-中幅",
                "转签-快速旋转-中幅"
            ],
            "庆祝": [
                "挑线-快速上挑-大幅",
                "转签-快速旋转-大幅",
                "挑线-快速上挑-大幅",
                "转签-快速旋转-大幅",
                "挑线-快速上挑-大幅"
            ]
        }
    
    def _infer_character_from_theme(self, theme: str) -> str:
        """根据主题关键词推断默认角色，避免所有剧本都变成孙悟空"""
        if not theme or not isinstance(theme, str):
            return "主角"
        t = theme.strip()
        if "黛玉" in t or "葬花" in t:
            return "林黛玉"
        if "贵妃" in t or "霓裳" in t or "杨贵妃" in t:
            return "杨贵妃"
        if "白骨精" in t or "三打" in t or "悟空" in t or "孙悟空" in t:
            return "孙悟空"
        if "观音" in t or "菩萨" in t:
            return "观音菩萨"
        if "霸王" in t or "别姬" in t or "虞姬" in t:
            return "虞姬"
        return "主角"

    def generate_script(self,
                       theme: str,
                       character: str = "孙悟空",
                       length: int = 5) -> Dict:
        """
        生成剧本
        
        Args:
            theme: 主题（如"三打白骨精"、"黛玉葬花"）
            character: 角色名称（若为空则根据 theme 推断）
            length: 剧本长度（场景数）
            
        Returns:
            剧本字典，包含场景、动作序列等
        """
        if not character or not str(character).strip():
            character = self._infer_character_from_theme(theme)
        if self.provider is None:
            return self._generate_mock_script(theme, character, length)

        prompt = f"""请为皮影戏生成一个专业的剧本，主题是"{theme}"，主角是{character}。

要求：
1. 包含{length}个场景，每个场景要有明确的戏剧冲突和情感变化
2. 每个场景必须包含：
   - scene_number: 场景编号
   - description: 详细的场景描述（50-100字）
   - lines: 该场景的台词列表（数组，每句为角色念白，如 ["花谢花飞花满天", "红消香断有谁怜"]，至少1句，不超过5句）
   - actions: 动作指令列表（使用皮影技法：挑线、压签、转签，每个动作格式为"技法-速度-幅度"，如"挑线-快速上挑-大幅"）
   - emotion: 情感标签（优先使用基本情绪：快乐、悲伤、愤怒、恐惧、厌恶、惊讶、中性；也可使用扩展情绪：欢快、喜悦、兴奋、满足、悲怆、忧伤、失望、平静、紧张、激动）
   - duration: 场景持续时间（秒）
   - intensity: 动作强度（1-10）
   - transition: 到下一场景的过渡方式（如"淡出"、"快速切换"等，如果是最后一个场景则设为"结束"）

3. 动作规则：
   - 挑线：上挑动作，用于上升、跳跃、攻击等
   - 压签：下压动作，用于下降、防御、悲伤等
   - 转签：旋转动作，用于旋转、转身、庆祝等
   - 速度：快速、中速、缓慢
   - 幅度：大幅、中幅、小幅

4. 情感与动作的对应关系（基于科学研究）：
   - 快乐/欢快/喜悦/兴奋：上升动作、开放姿态、快速移动（挑线-快速上挑-中幅/大幅）
   - 悲伤/悲怆/忧伤/失望：下降动作、收缩姿态、缓慢移动（压签-缓慢下压-小幅）
   - 愤怒：快速大幅动作、紧张姿态、攻击性（挑线-快速上挑-大幅 + 压签-快速下压-大幅）
   - 恐惧：快速收缩、防御姿态、不稳定（压签-快速下压-中幅 + 转签-快速旋转-中幅）
   - 厌恶：回避动作、收缩姿态、后退（压签-缓慢下压-中幅 + 转签-缓慢旋转-中幅）
   - 惊讶：突然动作、开放姿态、快速反应（挑线-快速上挑-大幅 + 保持-保持姿势-静止）
   - 中性/平静：平静、稳定、低激活（保持-保持姿势-静止 + 转签-缓慢旋转-小幅）

5. 剧本要有起承转合，情感要有起伏变化

请以JSON格式输出，确保格式正确：
{{
    "title": "剧本标题",
    "character": "{character}",
    "theme": "{theme}",
    "scenes": [
        {{
            "scene_number": 1,
            "description": "详细的场景描述",
            "lines": ["第一句台词", "第二句台词"],
            "actions": ["挑线-快速上挑-大幅", "压签-快速下压-大幅"],
            "emotion": "愤怒",
            "duration": 8,
            "intensity": 8,
            "transition": "快速切换"
        }}
    ]
}}
"""
        try:
            if self.provider == "tongyi":
                content = self._call_tongyi(prompt)
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "你是一个专业的皮影戏编剧。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7
                )
                content = (response.choices[0].message.content or "").strip()
            if not content:
                raise ValueError("模型未返回内容")
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                script = json.loads(json_match.group())
            else:
                script = self._generate_mock_script(theme, character, length)
        except Exception as e:
            print(f"生成剧本失败: {e}，使用模拟模式")
            script = self._generate_mock_script(theme, character, length)
        # 兼容：确保每个场景都有 lines（台词）
        for scene in script.get("scenes", []):
            if "lines" not in scene or not isinstance(scene.get("lines"), list):
                scene["lines"] = [scene.get("description", "")] if scene.get("description") else []
        return script

    def _call_tongyi(self, user_prompt: str) -> str:
        """调用通义千问（DashScope）生成内容"""
        response = Generation.call(
            api_key=self.tongyi_api_key,
            model=self.tongyi_model,
            messages=[
                {"role": "system", "content": "你是一个专业的皮影戏编剧。请严格按用户要求的 JSON 格式输出剧本。"},
                {"role": "user", "content": user_prompt}
            ],
            result_format="message",
            temperature=0.7
        )
        if response.status_code == 200 and response.output and response.output.choices:
            return (response.output.choices[0].message.content or "").strip()
        msg = getattr(response, "message", None) or getattr(response, "code", "") or "未知错误"
        raise RuntimeError(f"通义千问 API 错误: {msg}")
    
    def _generate_mock_script(self, theme: str, character: str, length: int) -> Dict:
        """生成模拟剧本（用于测试）；根据主题选用贴合的情绪与描述"""
        scenes = []
        theme_lower = (theme or "").lower()
        # 黛玉葬花、葬花等：以悲伤、抒情为主（使用基本情绪）
        if "黛玉" in theme or "葬花" in theme:
            emotions = ["悲伤", "悲伤", "平静", "失望", "悲伤"]
            descriptions = [
                "林黛玉荷锄携囊，于园中见落花满地，触景伤情",
                "黛玉吟唱《葬花吟》，以袖拭泪，缓步葬花",
                "手执花帚，轻扫落瓣，动作哀婉",
                "将花瓣收入锦囊，掩土而葬，神情凄楚",
                "独倚花树，望春归去，收势退场"
            ]
            lines_list = [
                ["花谢花飞花满天，红消香断有谁怜？"],
                ["尔今死去侬收葬，未卜侬身何日丧。"],
                ["侬今葬花人笑痴，他年葬侬知是谁？"],
                ["一朝春尽红颜老，花落人亡两不知。"],
                ["愿奴胁下生双翼，随花飞到天尽头。"],
            ]
        elif "贵妃" in theme or "霓裳" in theme:
            emotions = ["平静", "快乐", "兴奋", "满足", "平静"]
            descriptions = [
                "杨贵妃着霓裳，缓步登场",
                "展袖起舞，姿态雍容",
                "旋转回身，裙摆飞扬",
                "醉舞一段，渐收",
                "行礼退场"
            ]
            lines_list = [
                ["云想衣裳花想容，春风拂槛露华浓。"],
                ["若非群玉山头见，会向瑶台月下逢。"],
                ["名花倾国两相欢，长得君王带笑看。"],
                ["解释春风无限恨，沉香亭北倚阑干。"],
                ["一曲霓裳羽衣舞，千秋万代传佳话。"],
            ]
        else:
            emotions = ["紧张", "悲伤", "快乐", "平静", "满足"]
            descriptions = [f"{character}在{theme}中的第{i+1}个场景" for i in range(length)]
            lines_list = [[f"（{character}念白第{i+1}句）"] for i in range(length)]
        
        for i in range(length):
            emotion = emotions[i % len(emotions)]
            desc = descriptions[i % len(descriptions)] if descriptions else f"{character}在{theme}中的第{i+1}个场景"
            scene_lines = lines_list[i % len(lines_list)] if lines_list else [f"（场景{i+1}台词）"]
            scenes.append({
                "scene_number": i + 1,
                "description": desc,
                "lines": scene_lines,
                "actions": self.action_rules.get(emotion, ["挑线", "压签", "转签"]),
                "emotion": emotion,
                "duration": 5
            })
        
        return {
            "title": f"{character}的{theme}" if character != "主角" else theme,
            "character": character,
            "theme": theme,
            "scenes": scenes
        }
    
    def convert_script_to_actions(self, script: Dict) -> List[Dict]:
        """
        将剧本转换为动作序列
        
        Args:
            script: 剧本字典
            
        Returns:
            动作序列列表
        """
        action_sequence = []
        
        for scene in script.get("scenes", []):
            scene_num = scene["scene_number"]
            actions = scene["actions"]
            emotion = scene["emotion"]
            duration = scene.get("duration", 5)
            
            # 将文本动作转换为动作序列
            for action_text in actions:
                action_data = self._parse_action(action_text, emotion)
                action_sequence.append({
                    "scene": scene_num,
                    "action": action_text,
                    "action_data": action_data,
                    "emotion": emotion,
                    "duration": duration / len(actions)
                })
        
        return action_sequence
    
    def _parse_action(self, action_text: str, emotion: str) -> Dict:
        """
        解析动作文本为动作数据（增强版）
        
        Args:
            action_text: 动作文本（如"挑线-快速上挑-大幅"）
            emotion: 情感标签
            
        Returns:
            动作数据字典
        """
        # 解析动作类型、速度和幅度
        parts = action_text.split("-")
        action_type = parts[0] if parts else action_text
        speed_text = parts[1] if len(parts) > 1 else ""
        amplitude_text = parts[2] if len(parts) > 2 else ""
        
        # 速度映射
        speed_map = {
            "快速": "very_fast",
            "中速": "fast",
            "缓慢": "slow",
            "保持": "still"
        }
        
        # 幅度映射
        amplitude_map = {
            "大幅": 0.9,
            "中幅": 0.6,
            "小幅": 0.3,
            "静止": 0.0
        }
        
        # 根据动作类型生成参数
        action_params = {
            "挑线": {
                "direction": "up",
                "speed": speed_map.get(speed_text, "fast"),
                "amplitude": amplitude_map.get(amplitude_text, 0.5)
            },
            "压签": {
                "direction": "down",
                "speed": speed_map.get(speed_text, "fast"),
                "amplitude": amplitude_map.get(amplitude_text, 0.5)
            },
            "转签": {
                "direction": "rotate",
                "speed": speed_map.get(speed_text, "fast"),
                "angle": 45 if amplitude_text == "大幅" else 30,
                "amplitude": amplitude_map.get(amplitude_text, 0.5)
            },
            "保持": {
                "direction": "none",
                "speed": "still",
                "amplitude": 0.0
            }
        }
        
        base_params = action_params.get(action_type, {
            "direction": "none",
            "speed": "medium",
            "amplitude": 0.3
        })
        
        # 添加情感影响（如果未明确指定）
        if not speed_text or not amplitude_text:
            emotion_modifiers = {
                "悲怆": {"speed": "slow", "amplitude": 0.3},
                "欢快": {"speed": "fast", "amplitude": 0.7},
                "打斗": {"speed": "very_fast", "amplitude": 0.9},
                "行走": {"speed": "fast", "amplitude": 0.5},
                "挥手": {"speed": "fast", "amplitude": 0.6},
                "鞠躬": {"speed": "slow", "amplitude": 0.4},
                "跳跃": {"speed": "very_fast", "amplitude": 0.9},
                "旋转": {"speed": "very_fast", "amplitude": 0.8},
                "攻击": {"speed": "very_fast", "amplitude": 0.9},
                "防御": {"speed": "slow", "amplitude": 0.4},
                "逃跑": {"speed": "very_fast", "amplitude": 0.7},
                "庆祝": {"speed": "very_fast", "amplitude": 0.8}
            }
            
            if emotion in emotion_modifiers:
                base_params.update(emotion_modifiers[emotion])
        
        return {
            "type": action_type,
            "parameters": base_params,
            "emotion": emotion,
            "original_text": action_text
        }
    
    def combine_actions(self, action_sequence: List[Dict], combination_rules: Dict = None) -> List[Dict]:
        """
        组合动作序列，优化过渡
        
        Args:
            action_sequence: 动作序列
            combination_rules: 组合规则（可选）
            
        Returns:
            优化后的动作序列
        """
        if not combination_rules:
            combination_rules = {
                "smooth_transition": True,
                "min_gap": 2,  # 最小间隔帧数
                "blend_ratio": 0.3  # 混合比例
            }
        
        optimized_sequence = []
        
        for i, action in enumerate(action_sequence):
            optimized_action = action.copy()
            
            # 如果是第一个动作，直接添加
            if i == 0:
                optimized_sequence.append(optimized_action)
                continue
            
            # 检查与前一个动作的过渡
            prev_action = optimized_sequence[-1]
            
            # 如果动作类型相同，可以合并
            if (prev_action['action_data']['type'] == action['action_data']['type'] and
                combination_rules.get('smooth_transition', True)):
                # 添加过渡帧
                transition = {
                    "type": "transition",
                    "from_action": prev_action['action'],
                    "to_action": action['action'],
                    "duration": combination_rules.get('min_gap', 2),
                    "blend_ratio": combination_rules.get('blend_ratio', 0.3)
                }
                optimized_sequence.append(transition)
            
            optimized_sequence.append(optimized_action)
        
        return optimized_sequence

