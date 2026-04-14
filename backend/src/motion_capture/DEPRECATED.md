# 废弃代码说明

以下代码已被新的 VIBE + smpl2bvh 集成方案替代，保留作为后备方案。

## 废弃的文件

### `full_body_detector.py` 和 `bvh_24_joints.py`

**状态**: 保留作为后备方案（当 VIBE 不可用时）

**原因**: 
- 使用 MediaPipe 只能提取 2D 关键点，准确度较低
- 所有帧数据几乎相同，动作提取效果差
- 已被 VIBE + smpl2bvh 方案替代

**新方案**: 使用 `vibe_integration.py` 中的 `VIBEPipeline`

**迁移指南**:
- 旧代码: `FullBodyDetector` + `BVH24JointsConverter`
- 新代码: `VIBEPipeline` (自动使用 VIBE + smpl2bvh)

## 保留的文件

以下文件仍然有用，**不要删除**:

- `video_to_piying_pipeline.py`: 主管道，已更新使用新方案
- `vibe_integration.py`: 新的 VIBE 集成模块
- `mediapipe_detector.py`: 可能在其他地方使用
- `keypoint_mapper.py`: 可能在其他地方使用
- `bvh_converter.py`: 可能在其他地方使用

## 使用建议

1. **优先使用 VIBE**: 配置 VIBE 环境，使用 `use_vibe=True`
2. **后备方案**: 如果 VIBE 不可用，会自动回退到 MediaPipe（但效果较差）
3. **测试脚本**: 旧的测试脚本可能需要更新，但可以保留作为参考
