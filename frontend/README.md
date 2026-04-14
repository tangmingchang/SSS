# MyPiying 皮影戏智能互动网页

基于AI与物理引擎的皮影戏互动网页展示平台，用于比赛演示。

## 功能特性

- 📜 **剧本输入与AI解析**：输入剧本文本，自动生成动作指令序列
- 🎭 **皮影角色动画**：实时预览皮影角色的动画表演
- 💡 **光影效果模拟**：模拟传统皮影戏的油灯灯光和幕布效果
- 🎨 **角色素材库**：支持切换不同皮影角色
- 🎮 **交互控制**：播放/暂停、重播、灯光调节等控制功能

## 技术栈

- **前端框架**：React 18
- **构建工具**：Vite
- **样式**：CSS3（包含动画和光影效果）
- **动画**：CSS Keyframes + JavaScript

## 安装和运行

### 1. 安装依赖

```bash
cd web_interactive
npm install
```

### 2. 配置角色资源路径

编辑 `src/components/CharacterSelector.jsx` 和 `src/App.jsx` 中的角色图片路径，确保指向正确的资源位置。

如果使用本地文件，需要：
- 将角色图片放在 `public/characters/` 目录下
- 或者配置后端API提供图片资源

### 3. 启动开发服务器

```bash
npm run dev
```

应用将在 `http://localhost:3000` 启动。

### 4. 构建生产版本

```bash
npm run build
```

构建产物将输出到 `dist/` 目录。

## 项目结构

```
web_interactive/
├── public/              # 静态资源
├── src/
│   ├── components/      # React组件
│   │   ├── ScriptInput.jsx      # 剧本输入组件
│   │   ├── PuppetStage.jsx      # 皮影舞台组件
│   │   ├── CharacterSelector.jsx # 角色选择组件
│   │   └── Controls.jsx         # 控制面板组件
│   ├── utils/          # 工具函数
│   │   └── scriptParser.js     # 剧本解析工具
│   ├── App.jsx         # 主应用组件
│   ├── main.jsx        # 应用入口
│   └── index.css       # 全局样式
├── index.html          # HTML模板
├── package.json        # 项目配置
└── vite.config.js      # Vite配置
```

## 使用说明

1. **输入剧本**：在左侧面板的文本框中输入剧本内容（例如："孙悟空三打白骨精"）
2. **生成动作**：点击"生成动作"按钮，系统会自动解析剧本并生成动作序列
3. **选择角色**：在右侧面板选择要表演的皮影角色
4. **播放动画**：点击"播放"按钮开始动画表演
5. **调节灯光**：使用灯光控制按钮和亮度滑块调节舞台灯光效果

## 角色资源配置

角色图片需要按照以下结构组织：

```
public/characters/
├── 人物-1/
│   ├── 头.png
│   ├── 上身.png
│   ├── 左手.png
│   ├── 右手.png
│   ├── 左腿.png
│   └── 右腿.png
└── ...
```

或者通过后端API提供：

```
/api/characters/{角色名}/{部件名}.png
```

## 动作关键词

系统支持以下动作关键词（可在 `src/utils/scriptParser.js` 中扩展）：

- **打斗类**：打、击、劈、砍、刺、攻、战、斗、杀
- **移动类**：走、行、步、移、跑、奔、追、逃
- **跳跃类**：跳、跃、腾、飞
- **防御类**：挡、防、守、护
- **表演类**：舞、蹈、转、旋
- **姿态类**：坐、蹲、站、立
- **手势类**：挥、摆、摇、指、点、举、抬、扬、放、降、垂
- **礼仪类**：拜、躬、礼

## 自定义和扩展

### 添加新动作

1. 在 `src/utils/scriptParser.js` 中添加新的关键词映射
2. 在 `src/components/PuppetStage.css` 中添加对应的CSS动画
3. 在 `src/components/PuppetStage.jsx` 中添加动作持续时间配置

### 修改样式

所有样式文件都在对应的 `.css` 文件中，可以根据设计需求调整：
- `src/App.css` - 主应用样式
- `src/components/*.css` - 各组件样式

### 添加新角色

在 `src/App.jsx` 的 `DEFAULT_CHARACTERS` 数组中添加新角色配置。

## 注意事项

1. **图片路径**：确保角色图片路径正确，否则会显示占位符
2. **浏览器兼容性**：建议使用现代浏览器（Chrome、Firefox、Edge等）
3. **性能优化**：大量角色或复杂动画可能影响性能，建议优化图片大小

## 许可证

本项目为"基于AI与物理引擎的皮影戏智能生成与交互传承系统"的一部分。

