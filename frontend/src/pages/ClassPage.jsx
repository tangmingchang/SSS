import React, { useState, useEffect } from 'react';
import { apiClassGet, apiAssignmentsList, apiAssignmentCreate } from '../services/teachApi';
import GroupBoard from '../components/teach/GroupBoard';
import './ClassPage.css';

/**
 * 班级页：邀请码、分组看板、作业列表、课堂演示入口
 */
export default function ClassPage({ classId, onOpenStage, onOpenLesson, onBack }) {
  const [cls, setCls] = useState(null);
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [newAssignmentTitle, setNewAssignmentTitle] = useState('');

  useEffect(() => {
    if (!classId) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [classData, list] = await Promise.all([
          apiClassGet(classId),
          apiAssignmentsList(classId),
        ]);
        if (!cancelled) {
          setCls(classData);
          setAssignments(Array.isArray(list) ? list : []);
        }
      } catch (e) {
        if (!cancelled) setError(e.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [classId]);

  const handleCreateAssignment = async (e) => {
    e.preventDefault();
    if (!newAssignmentTitle.trim()) return;
    try {
      await apiAssignmentCreate({
        classId,
        title: newAssignmentTitle.trim(),
        spec: { description: '', submitType: 'performance' },
      });
      setNewAssignmentTitle('');
      const list = await apiAssignmentsList(classId);
      setAssignments(Array.isArray(list) ? list : []);
    } catch (e) {
      setError(e.message);
    }
  };

  if (!classId) return <div className="class-page">请选择班级</div>;
  if (loading) return <div className="class-page">加载中…</div>;
  if (error) return <div className="class-page class-error">错误：{error}</div>;
  if (!cls) return null;

  return (
    <div className="class-page">
      <div className="class-header">
        {onBack && (
          <button type="button" className="class-back" onClick={onBack} aria-label="返回上一页">
            ← 返回
          </button>
        )}
        <h1>{cls.name}</h1>
        <p className="class-course">{cls.course?.title}</p>
        <div className="class-join-code">
          邀请码：<strong>{cls.joinCode}</strong>
        </div>
      </div>

      <GroupBoard groups={cls.groups || []} />

      <section className="class-section">
        <h2>作业</h2>
        <form onSubmit={handleCreateAssignment} className="class-form">
          <input
            type="text"
            value={newAssignmentTitle}
            onChange={(e) => setNewAssignmentTitle(e.target.value)}
            placeholder="新作业标题"
          />
          <button type="submit">发布作业</button>
        </form>
        <ul className="class-assignments">
          {assignments.map((a) => (
            <li key={a.id}>
              <span>{a.title}</span>
              <span className="class-meta">提交 {a._count?.submissions ?? 0} 份</span>
            </li>
          ))}
          {assignments.length === 0 && <li className="class-empty">暂无作业</li>}
        </ul>
      </section>

      <div className="class-actions">
        <button
          type="button"
          className="class-btn-demo"
          onClick={() => onOpenStage && onOpenStage({ classId, mode: 'demo' })}
        >
          课堂演示模式
        </button>
        {(cls.course?.lessons?.length ?? 0) > 0 && (
          <button
            type="button"
            onClick={() => onOpenLesson && onOpenLesson({
              lessonId: cls.course.lessons[0].id,
              courseId: cls.course.id,
            })}
          >
            进入课时
          </button>
        )}
      </div>
    </div>
  );
}
