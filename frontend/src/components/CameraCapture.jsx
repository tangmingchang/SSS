import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { API_BASE } from '../utils/api';
import './CameraCapture.css';

function CameraCapture({
  onVideoCapture,
  onCaptureStart,
  onCaptureComplete,
  onCaptureSuccess,
  onCaptureError,
  onCaptureClear,
  onLivePose,
  onLivePoseError,
  onLivePoseStateChange,
  enableLiveTracking = true,
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordedUrl, setRecordedUrl] = useState(null);
  const [uploadStatus, setUploadStatus] = useState('idle'); // idle | uploading | success | error
  const [uploadError, setUploadError] = useState(null);

  const [isLiveTracking, setIsLiveTracking] = useState(false);
  const [liveStatus, setLiveStatus] = useState('idle'); // idle | tracking | no-person | error
  const [liveError, setLiveError] = useState(null);

  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const captureCanvasRef = useRef(null);
  const liveTimerRef = useRef(null);
  const liveInFlightRef = useRef(false);

  const stopLiveTracking = useCallback((nextStatus = 'idle') => {
    if (liveTimerRef.current) {
      clearInterval(liveTimerRef.current);
      liveTimerRef.current = null;
    }
    liveInFlightRef.current = false;
    setIsLiveTracking(false);
    setLiveStatus(nextStatus);
    if (nextStatus !== 'error') setLiveError(null);
    if (onLivePoseStateChange) onLivePoseStateChange(false, nextStatus);
  }, [onLivePoseStateChange]);

  const sendLiveFrame = useCallback(async () => {
    if (!videoRef.current || !captureCanvasRef.current) return;
    if (liveInFlightRef.current) return;

    const video = videoRef.current;
    if (video.readyState < 2) return;
    const vw = video.videoWidth || 0;
    const vh = video.videoHeight || 0;
    if (!vw || !vh) return;

    const targetW = Math.min(640, vw);
    const scale = targetW / vw;
    const cw = Math.max(160, Math.round(vw * scale));
    const ch = Math.max(120, Math.round(vh * scale));

    const canvas = captureCanvasRef.current;
    canvas.width = cw;
    canvas.height = ch;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Mirror to match user-facing preview.
    ctx.save();
    ctx.translate(cw, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0, cw, ch);
    ctx.restore();

    const dataUrl = canvas.toDataURL('image/jpeg', 0.68);
    liveInFlightRef.current = true;
    try {
      const res = await fetch(`${API_BASE}/api/camera_pose_frame`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: dataUrl }),
      });
      const data = await res.json().catch(() => ({}));

      if (!res.ok || !data.success) {
        let msg = data.error || `实时姿态请求失败 ${res.status}`;
        if (res.status === 503 || /unavailable/i.test(String(msg))) {
          msg = `实时姿态服务不可用（${msg}）。请检查后端是否安装 opencv-python、mediapipe 并重启后端。`;
        }
        setLiveStatus('error');
        setLiveError(msg);
        if (onLivePoseError) onLivePoseError(msg);
        if (res.status === 503) {
          stopLiveTracking('error');
        }
        return;
      }

      if (data.detected) {
        setLiveStatus('tracking');
        setLiveError(null);
        if (onLivePose) onLivePose(data);
      } else {
        setLiveStatus('no-person');
      }
    } catch (err) {
      const msg = err?.message || '实时姿态网络异常';
      setLiveStatus('error');
      setLiveError(msg);
      if (onLivePoseError) onLivePoseError(msg);
    } finally {
      liveInFlightRef.current = false;
    }
  }, [onLivePose, onLivePoseError, stopLiveTracking]);

  const startLiveTracking = useCallback(() => {
    if (!enableLiveTracking) return;
    if (!isOpen || !streamRef.current || isRecording || isLiveTracking) return;
    setIsLiveTracking(true);
    setLiveStatus('tracking');
    setLiveError(null);
    if (onLivePoseStateChange) onLivePoseStateChange(true, 'tracking');
    sendLiveFrame();
    liveTimerRef.current = setInterval(sendLiveFrame, 120);
  }, [enableLiveTracking, isOpen, isRecording, isLiveTracking, onLivePoseStateChange, sendLiveFrame]);

  const openCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user',
        },
        audio: false,
      });
      streamRef.current = stream;
      setIsOpen(true);
    } catch (error) {
      console.error('无法访问摄像头', error);
      alert('无法访问摄像头，请检查浏览器权限设置。');
    }
  };

  useLayoutEffect(() => {
    if (!isOpen || !streamRef.current) return;
    const stream = streamRef.current;
    const bind = () => {
      if (!videoRef.current) return;
      const video = videoRef.current;
      if (video.srcObject === stream) return;
      video.srcObject = stream;
      video.play().catch(() => {});
    };
    bind();
    const t = setTimeout(bind, 50);
    return () => clearTimeout(t);
  }, [isOpen]);

  const closeCamera = useCallback(() => {
    stopLiveTracking('idle');
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
      videoRef.current.pause();
    }
    setIsOpen(false);
    setIsRecording(false);
    setUploadStatus('idle');
    setUploadError(null);
    setRecordedUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return null;
    });
    if (onCaptureClear) onCaptureClear();
  }, [stopLiveTracking, onCaptureClear]);

  const clearRecordedVideo = useCallback(() => {
    setRecordedUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return null;
    });
    setUploadStatus('idle');
    setUploadError(null);
    if (onCaptureClear) onCaptureClear();
  }, [onCaptureClear]);

  const uploadBlob = async (blob) => {
    setUploadStatus('uploading');
    setUploadError(null);
    if (onCaptureStart) onCaptureStart();

    const formData = new FormData();
    formData.append('video', blob, 'capture.webm');

    try {
      const res = await fetch(`${API_BASE}/api/capture_motion`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        const msg = data.error || `请求失败 ${res.status}`;
        setUploadError(msg);
        setUploadStatus('error');
        if (onCaptureError) onCaptureError(msg);
        return;
      }

      if (data.success && data.session_id != null) {
        const payload = { session_id: data.session_id, frames: data.frames, bvh_url: data.bvh_url };
        setUploadStatus('success');
        if (onCaptureSuccess) onCaptureSuccess(payload);
        if (onCaptureComplete) onCaptureComplete(payload);
      } else {
        const msg = data.error || '未返回 session_id';
        setUploadError(msg);
        setUploadStatus('error');
        if (onCaptureError) onCaptureError(msg);
      }
    } catch (err) {
      const msg = err?.message || '网络错误，请确认后端已启动。';
      setUploadError(msg);
      setUploadStatus('error');
      if (onCaptureError) onCaptureError(msg);
    }
  };

  const startRecording = () => {
    if (!streamRef.current) return;
    stopLiveTracking('idle');
    chunksRef.current = [];

    const options = MediaRecorder.isTypeSupported('video/webm;codecs=vp8')
      ? { mimeType: 'video/webm;codecs=vp8' }
      : {};
    const mediaRecorder = new MediaRecorder(streamRef.current, options);

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunksRef.current.push(event.data);
    };
    mediaRecorder.onstop = () => {
      const mime = (mediaRecorder.mimeType || 'video/webm').split(';')[0];
      const blob = new Blob(chunksRef.current, { type: mime });
      setRecordedUrl(URL.createObjectURL(blob));
      if (onVideoCapture) onVideoCapture(blob);
      uploadBlob(blob);
    };

    mediaRecorderRef.current = mediaRecorder;
    mediaRecorder.start();
    setIsRecording(true);
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  useEffect(() => () => {
    if (liveTimerRef.current) {
      clearInterval(liveTimerRef.current);
      liveTimerRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
      videoRef.current.pause();
    }
  }, []);

  return (
    <div className="camera-capture">
      <div className="camera-header">
        <h3>摄像头动作捕捉</h3>
      </div>

      {!isOpen ? (
        <div className="camera-controls">
          <button onClick={openCamera} className="camera-btn open-btn">
            打开摄像头
          </button>
          <p className="camera-tips">支持实时跟随和录制上传（BVH）两种模式。</p>
        </div>
      ) : (
        <div className="camera-preview">
          <div className="video-container">
            <p className="camera-preview-label">实时画面（镜像）</p>
            <video
              ref={videoRef}
              autoPlay
              muted
              playsInline
              className="camera-video mirrored"
              style={{ transform: 'scaleX(-1)', WebkitTransform: 'scaleX(-1)' }}
            />
            {isRecording && (
              <div className="recording-indicator">
                <span className="recording-dot" />
                录制中...
              </div>
            )}
            {isLiveTracking && <div className="live-indicator">实时跟随中</div>}
          </div>

          <div className="camera-actions camera-actions-live">
            {enableLiveTracking && (
              !isLiveTracking ? (
                <button onClick={startLiveTracking} className="camera-btn live-btn" disabled={isRecording}>
                  开始实时跟随
                </button>
              ) : (
                <button onClick={() => stopLiveTracking('idle')} className="camera-btn live-stop-btn">
                  停止实时跟随
                </button>
              )
            )}

            {!isRecording ? (
              <button onClick={startRecording} className="camera-btn record-btn">
                开始录制
              </button>
            ) : (
              <button onClick={stopRecording} className="camera-btn stop-btn">
                停止录制
              </button>
            )}

            <button onClick={closeCamera} className="camera-btn close-btn">
              关闭摄像头
            </button>
          </div>

          {enableLiveTracking && (
            <p className="camera-live-status">
              实时状态：
              {liveStatus === 'tracking' && ' 已跟踪人体'}
              {liveStatus === 'no-person' && ' 未检测到人体'}
              {liveStatus === 'error' && ` 错误：${liveError || '未知错误'}`}
              {liveStatus === 'idle' && ' 空闲'}
            </p>
          )}

          {recordedUrl && (
            <div className="recorded-video">
              <div className="recorded-header">
                <p className="recorded-label">已录制视频：</p>
                <button type="button" className="camera-btn delete-recorded-btn" onClick={clearRecordedVideo} title="删除该视频">
                  删除
                </button>
              </div>
              <video src={recordedUrl} controls className="recorded-preview" style={{ transform: 'scaleX(-1)' }} />

              {uploadStatus === 'uploading' && <p className="recorded-tips">上传/处理中...</p>}
              {uploadStatus === 'success' && (
                <p className="recorded-tips" style={{ color: '#8bc34a' }}>
                  已生成 BVH，可在工作台下载。
                </p>
              )}
              {uploadStatus === 'error' && (
                <>
                  <p className="recorded-tips" style={{ color: '#ff6b6b' }}>{uploadError}</p>
                  <button
                    type="button"
                    className="camera-btn convert-bvh-btn"
                    onClick={() => fetch(recordedUrl).then((r) => r.blob()).then((blob) => uploadBlob(blob))}
                  >
                    重新转换为 BVH
                  </button>
                </>
              )}
              {uploadStatus === 'idle' && (
                <>
                  <p className="recorded-tips">视频已录制，点击下方按钮转换为 BVH。</p>
                  <button
                    type="button"
                    className="camera-btn convert-bvh-btn"
                    onClick={() => fetch(recordedUrl).then((r) => r.blob()).then((blob) => uploadBlob(blob))}
                  >
                    转换为 BVH
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      )}

      <canvas ref={captureCanvasRef} style={{ display: 'none' }} />
    </div>
  );
}

export default CameraCapture;
