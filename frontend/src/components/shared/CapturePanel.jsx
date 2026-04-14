import React, { useState } from 'react';
import { useWorkbenchStore } from '../../stores/workbenchStore';
import CameraCapture from '../CameraCapture';
import { IconCamera, IconArrowDown, IconArrowUp } from './Icons';
import { API_BASE } from '../../utils/api';
import './CapturePanel.css';

/**
 * 摄像头面板组件（可折叠）
 */
export default function CapturePanel() {
  const {
    ui,
    stage,
    orderTicket,
    liveTargetCharacterId,
    updateUI,
    updateTask,
    setLivePose,
    setLiveTrackingStatus,
    setLiveTargetCharacterId,
  } = useWorkbenchStore();
  const expanded = ui.bottomRailExpanded.capture;
  const [driveMode, setDriveMode] = useState('camera'); // camera | kinect(unity bridge)
  const candidates = (stage.characters && stage.characters.length > 0)
    ? stage.characters
    : (orderTicket.character ? [orderTicket.character] : []);

  const toggleExpand = () => {
    updateUI({
      bottomRailExpanded: {
        ...ui.bottomRailExpanded,
        capture: !expanded
      }
    });
  };

  React.useEffect(() => {
    if (driveMode !== 'kinect') return undefined;
    let disposed = false;
    let inFlight = false;
    const poll = async () => {
      if (disposed || inFlight) return;
      inFlight = true;
      try {
        const res = await fetch(`${API_BASE}/api/unity_pose_frame_latest`);
        const data = await res.json().catch(() => ({}));
        if (!res.ok || !data.success) {
          setLiveTrackingStatus('error');
          return;
        }
        if (data.detected && data.puppet_pose) {
          setLivePose(data.puppet_pose);
          setLiveTrackingStatus('tracking');
        } else {
          setLivePose(null);
          setLiveTrackingStatus('no-person');
        }
      } catch (_) {
        setLiveTrackingStatus('error');
      } finally {
        inFlight = false;
      }
    };
    poll();
    const timer = window.setInterval(poll, 80);
    return () => {
      disposed = true;
      window.clearInterval(timer);
    };
  }, [driveMode, setLivePose, setLiveTrackingStatus]);

  return (
    <div className={`capture-panel ${expanded ? 'expanded' : ''}`}>
      <button className="panel-toggle" onClick={toggleExpand}>
        <span className="panel-icon">
          <IconCamera size={16} />
        </span>
        <span className="panel-label">动作捕捉</span>
        <span className="panel-arrow">
          {expanded ? <IconArrowDown size={12} /> : <IconArrowUp size={12} />}
        </span>
      </button>

      {expanded && (
        <div className="panel-content">
          <div style={{ marginBottom: '10px', padding: '8px', borderRadius: '8px', background: 'rgba(255,255,255,0.04)' }}>
            <p style={{ margin: '0 0 6px 0', fontSize: '12px', color: '#d8c8a8' }}>驱动模式</p>
            <label style={{ marginRight: '12px', fontSize: '12px', color: '#cdbb96' }}>
              <input
                type="radio"
                name="captureDriveMode"
                value="camera"
                checked={driveMode === 'camera'}
                onChange={() => {
                  setDriveMode('camera');
                  setLiveTrackingStatus('idle');
                  setLivePose(null);
                }}
                style={{ marginRight: '6px' }}
              />
              普通摄像头实时驱动
            </label>
            <label style={{ fontSize: '12px', color: '#cdbb96' }}>
              <input
                type="radio"
                name="captureDriveMode"
                value="kinect"
                checked={driveMode === 'kinect'}
                onChange={() => {
                  setDriveMode('kinect');
                  setLiveTrackingStatus('idle');
                  setLivePose(null);
                }}
                style={{ marginRight: '6px' }}
              />
              Unity 骨骼桥接驱动
            </label>
          </div>
          <div style={{ marginBottom: '10px', padding: '8px', borderRadius: '8px', background: 'rgba(255,255,255,0.04)' }}>
            <p style={{ margin: '0 0 6px 0', fontSize: '12px', color: '#d8c8a8' }}>实时驱动角色</p>
            <select
              value={liveTargetCharacterId}
              onChange={(e) => setLiveTargetCharacterId(e.target.value)}
              disabled={driveMode !== 'camera' || candidates.length === 0}
              style={{
                width: '100%',
                padding: '6px 8px',
                borderRadius: '6px',
                border: '1px solid rgba(255,255,255,0.2)',
                background: 'rgba(0,0,0,0.2)',
                color: '#e6d8bd',
                fontSize: '12px',
              }}
            >
              <option value="">{candidates.length ? '自动（优先第一个）' : '暂无舞台角色'}</option>
              {candidates.map((c, i) => {
                const cid = c?.id ?? `char-${i}`;
                return (
                  <option key={cid} value={cid}>
                    {c?.name || cid}
                  </option>
                );
              })}
            </select>
          </div>

          <CameraCapture
            enableLiveTracking={driveMode === 'camera'}
            onCaptureSuccess={(data) => {
              updateTask('motionCapture', { status: 'success', result: data });
            }}
            onCaptureError={(msg) => {
              updateTask('motionCapture', { status: 'error', error: msg });
            }}
            onCaptureClear={() => {
              updateTask('motionCapture', { status: 'idle' });
            }}
            onLivePose={(data) => {
              setLivePose(data?.puppet_pose || null);
            }}
            onLivePoseStateChange={(active, status) => {
              if (driveMode === 'camera') {
                setLiveTrackingStatus(status || (active ? 'tracking' : 'idle'));
                if (!active) setLivePose(null);
              }
            }}
            onLivePoseError={() => {
              if (driveMode === 'camera') setLiveTrackingStatus('error');
            }}
          />
          <p style={{ marginTop: '8px', fontSize: '12px', color: '#b8a88a' }}>
            {driveMode === 'camera'
              ? '当前模式：普通摄像头实时跟随，可直接驱动皮影。'
              : '当前模式：Unity 骨骼桥接驱动。请在 Unity 挂载 UnityWebPoseSender 并运行场景。'}
          </p>
        </div>
      )}
    </div>
  );
}
