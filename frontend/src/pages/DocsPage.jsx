import React, { useEffect, useMemo, useRef, useState } from "react";
import "./DocsPage.css";

const DOCS = [
  {
    id: "flow",
    title: "一、创作工作台使用流程",
    steps: [
      {
        title: "输入创作想法",
        body: "用自然语言描述你想要的皮影戏片段，例如：\"观音菩萨与龙袍王帽生对话，突出文戏和庄重氛围\"。",
      },
      { title: "生成单场景剧本", body: "平台会根据你的想法自动生成包含人物、场景、动作的剧本文本。" },
      { title: "选择角色素材", body: "从公共资源库或个人资源库中选择皮影角色，也可以使用AI生成新角色。" },
      { title: "选择动作素材", body: "选择角色的动作序列，可以在预览区查看动作效果。" },
      { title: "选择背景场景", body: "从资源库中选择或上传背景图片，营造场景氛围。" },
      { title: "场景分析", body: "平台会自动分析场景的节奏、角色关系、场景匹配度等，提供优化建议。" },
      { title: "确认场景内容", body: "再次确认剧本、角色、动作、背景等信息，确认后生成视频。" },
      { title: "生成视频", body: "平台会生成皮影戏视频，可以调节光影强度和音乐。" },
      { title: "完成", body: "视频生成完成，自动匹配字幕，可以下载或分享。" },
    ],
  },
  {
    id: "assets",
    title: "二、资源库使用",
    blocks: [
      { h: "公共资源库", p: "平台提供的免费资源，包括角色、场景、动作、音乐等，可以直接使用。" },
      { h: "个人资源库", p: "你可以上传自己的素材，或从公共资源库、AI生成页面保存资源到个人库。" },
    ],
  },
  {
    id: "aigen",
    title: "三、AI生成功能",
    blocks: [{ p: "输入描述，AI可以生成角色、场景、动作、音乐等资源，生成后可以保存到个人资源库。" }],
  },
];

export default function DocsPage() {
  const [query, setQuery] = useState("");
  const [activeId, setActiveId] = useState("flow");
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const sectionRefs = useRef(new Map());

  const filteredDocs = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return DOCS;

    return DOCS.map((sec) => {
      if (sec.steps) {
        const steps = sec.steps.filter((s) => (s.title + " " + s.body).toLowerCase().includes(q));
        return { ...sec, steps };
      }
      if (sec.blocks) {
        const blocks = sec.blocks.filter((b) => ((b.h || "") + " " + (b.p || "")).toLowerCase().includes(q));
        return { ...sec, blocks };
      }
      return sec;
    });
  }, [query]);

  const scrollTo = (id) => {
    const el = sectionRefs.current.get(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      setMobileNavOpen(false);
    }
  };

  useEffect(() => {
    // IntersectionObserver: 自动高亮当前章节
    const els = Array.from(sectionRefs.current.values());
    if (!els.length) return;

    const io = new IntersectionObserver(
      (entries) => {
        // 找到最靠上且可见的 section
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => (a.boundingClientRect.top ?? 0) - (b.boundingClientRect.top ?? 0))[0];
        if (visible?.target?.dataset?.id) setActiveId(visible.target.dataset.id);
      },
      {
        root: null,
        threshold: 0.25,
        rootMargin: "-20% 0px -60% 0px",
      }
    );

    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  return (
    <div className="docs-shell">
      <div className="docs-top">
        <div className="docs-topTitle">
          <h1 className="docs-title">使用文档</h1>
          <p className="docs-subtitle">更快跳转、更好阅读的交互式说明</p>
        </div>

        <div className="docs-tools">
          <div className="docs-search">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="搜索：步骤、功能点、关键词"
              aria-label="搜索文档"
            />
            {query ? (
              <button className="docs-clear" onClick={() => setQuery("")} aria-label="清除搜索">
                清除
              </button>
            ) : null}
          </div>

          {/* 移动端目录折叠菜单：不用原生 select，做成可控按钮 + 面板 */}
          <div className="docs-mobileNav">
            <button
              className="docs-mobileTrigger"
              onClick={() => setMobileNavOpen((v) => !v)}
              aria-expanded={mobileNavOpen}
              aria-controls="docs-mobile-panel"
              type="button"
            >
              <span className="docs-mobileLabel">目录</span>
              <span className={`docs-caret ${mobileNavOpen ? "is-open" : ""}`} aria-hidden="true" />
            </button>

            <div
              id="docs-mobile-panel"
              className={`docs-mobilePanel ${mobileNavOpen ? "is-open" : ""}`}
              role="region"
              aria-label="文档目录"
            >
              {DOCS.map((sec) => (
                <button
                  key={sec.id}
                  className={`docs-mobileItem ${activeId === sec.id ? "is-active" : ""}`}
                  onClick={() => scrollTo(sec.id)}
                  type="button"
                >
                  {sec.title}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="docs-layout">
        {/* 桌面端：左侧目录 */}
        <aside className="docs-aside" aria-label="文档目录">
          <div className="docs-asideCard">
            <div className="docs-asideHead">目录</div>
            <nav className="docs-toc">
              {DOCS.map((sec) => (
                <button
                  key={sec.id}
                  className={`docs-tocItem ${activeId === sec.id ? "is-active" : ""}`}
                  onClick={() => scrollTo(sec.id)}
                  type="button"
                >
                  <span className="docs-dot" aria-hidden="true" />
                  <span className="docs-tocText">{sec.title}</span>
                </button>
              ))}
            </nav>
            <div className="docs-asideHint">提示：滚动阅读会自动高亮当前章节</div>
          </div>
        </aside>

        {/* 右侧内容 */}
        <main className="docs-main">
          {filteredDocs.map((sec) => (
            <section
              key={sec.id}
              data-id={sec.id}
              ref={(node) => {
                if (!node) return;
                sectionRefs.current.set(sec.id, node);
              }}
              className="docs-card"
            >
              <div className="docs-cardHead">
                <h2 className="docs-h2">{sec.title}</h2>
                {sec.desc ? <p className="docs-desc">{sec.desc}</p> : null}
              </div>

              {/* 流程：用 disclosure/accordion 做成交互步骤 */}
              {sec.steps ? (
                <div className="docs-steps" role="list">
                  {sec.steps.length ? (
                    sec.steps.map((s, idx) => (
                      <details className="docs-step" key={s.title} role="listitem">
                        <summary className="docs-stepSum">
                          <span className="docs-stepIndex">{String(idx + 1).padStart(2, "0")}</span>
                          <span className="docs-stepTitle">{s.title}</span>
                          <span className="docs-stepHint">点击展开</span>
                        </summary>
                        <div className="docs-stepBody">{s.body}</div>
                      </details>
                    ))
                  ) : (
                    <div className="docs-empty">没有匹配的步骤，请换个关键词。</div>
                  )}
                </div>
              ) : null}

              {/* 普通块内容 */}
              {sec.blocks ? (
                <div className="docs-blocks">
                  {sec.blocks.map((b, i) => (
                    <div className="docs-block" key={i}>
                      {b.h ? <h3 className="docs-h3">{b.h}</h3> : null}
                      {b.p ? <p className="docs-p">{b.p}</p> : null}
                    </div>
                  ))}
                </div>
              ) : null}
            </section>
          ))}
        </main>
      </div>
    </div>
  );
}
