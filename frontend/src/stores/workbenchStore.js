import { create } from 'zustand';

/**
 * 站点ID类型
 * @typedef {'order' | 'script' | 'motion' | 'stage' | 'showtime' | 'export'} StationId
 */

/**
 * 任务状态类型
 * @typedef {'idle' | 'running' | 'success' | 'error'} TaskStatusType
 */

/**
 * 工作台全局状态管理（Zustand）
 */
export const useWorkbenchStore = create((set, get) => ({
  // ========== Order Ticket数据 ==========
  orderTicket: {
    theme: '',
    script: null,
    character: null,
    background: null,
    actionSequence: [],
    videoOptions: {
      lighting: 0.7,
      brightness: 0.8,
      speed: 1.0,
      subtitles: false,
      /** 背景音乐（演出站上传后的 blob URL 或服务器 URL） */
      backgroundMusicUrl: null,
      backgroundMusicName: null,
    },
    sceneAnalysis: null,
  },

  // ========== 站点状态 ==========
  currentStation: 'order',
  completedStations: [],

  // ========== 舞台状态 ==========
  stage: {
    characters: [],
    background: null,
    props: [],
    playback: {
      playing: false,
      currentTime: 0,
      duration: 0,
      speed: 1.0,
    },
    brightness: 0.8,
    lighting: 0.7,
    subtitles: false,
    /** 字幕自定义文案，为空则使用剧本内容 */
    subtitleText: null,
    /** 字幕字号（px） */
    subtitleFontSize: 14,
    /** 字幕位置：水平中心（%），垂直距底（%） */
    subtitleCenterX: 50,
    subtitleBottomPercent: 12,
  },

  // ========== 任务状态 ==========
  tasks: {
    scriptGeneration: { status: 'idle' },
    videoGeneration: { status: 'idle' },
    motionCapture: { status: 'idle' },
    sceneAnalysis: { status: 'idle' },
  },

  livePose: null,
  liveTrackingStatus: 'idle',
  liveTargetCharacterId: '',

  // ========== UI状态 ==========
  ui: {
    orderTicketExpanded: false,
    orderTicketPinned: false,
    bottomRailExpanded: {
      assets: true,   // 资源仓默认展开
      capture: true,  // 动作捕捉默认展开
      export: true,  // 参数(调参)默认展开
    },
  },

  /** 舞台画布 DOM（用于导出视频时自动截图），由 Stage 组件设置 */
  stageCanvasEl: null,
  setStageCanvasEl: (el) => set({ stageCanvasEl: el }),

  /** 导出成功的视频 URL：非空时中央舞台区显示该视频（与舞台同尺寸 + 播放/倍速），替代静态舞台 */
  exportedVideoUrl: null,
  setExportedVideoUrl: (url) => set({ exportedVideoUrl: url }),
  setLivePose: (pose) => set({ livePose: pose || null }),
  setLiveTrackingStatus: (status) => set({ liveTrackingStatus: status || 'idle' }),
  setLiveTargetCharacterId: (id) => set({ liveTargetCharacterId: id || '' }),

  // ========== Actions ==========

  /**
   * 更新Order Ticket数据
   */
  updateOrderTicket: (updates) => set((state) => ({
    orderTicket: { ...state.orderTicket, ...updates }
  })),

  /**
   * 设置当前站点
   */
  setCurrentStation: (station) => {
    set({ currentStation: station });
    // 自动高亮Order Ticket对应字段
  },

  /**
   * 标记站点为已完成
   */
  markStationCompleted: (station) => set((state) => {
    if (!state.completedStations.includes(station)) {
      return {
        completedStations: [...state.completedStations, station]
      };
    }
    return state;
  }),

  /**
   * 更新舞台状态
   */
  updateStage: (updates) => set((state) => ({
    stage: { ...state.stage, ...updates }
  })),

  /**
   * 更新任务状态
   */
  updateTask: (taskId, status) => set((state) => ({
    tasks: { ...state.tasks, [taskId]: status }
  })),

  /**
   * 更新UI状态
   */
  updateUI: (updates) => set((state) => ({
    ui: { ...state.ui, ...updates }
  })),

  /**
   * 切换到下一个站点
   */
  goToNextStation: () => {
    const stations = ['order', 'script', 'motion', 'stage', 'showtime', 'export'];
    const current = get().currentStation;
    const currentIndex = stations.indexOf(current);
    if (currentIndex < stations.length - 1) {
      const nextStation = stations[currentIndex + 1];
      get().setCurrentStation(nextStation);
    }
  },

  /**
   * 切换到上一个站点
   */
  goToPrevStation: () => {
    const stations = ['order', 'script', 'motion', 'stage', 'showtime', 'export'];
    const current = get().currentStation;
    const currentIndex = stations.indexOf(current);
    if (currentIndex > 0) {
      const prevStation = stations[currentIndex - 1];
      get().setCurrentStation(prevStation);
    }
  },
}));
