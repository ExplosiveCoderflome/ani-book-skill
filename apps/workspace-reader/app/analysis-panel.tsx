import { useState } from 'react';
import { Link } from 'react-router';
import { CheckCircle2, Circle, ArrowUpRight, Copy, Layers3 } from 'lucide-react';
import type { AnalysisDetails, ReferenceUsage } from './lib/analysis.server';
import { documentUrl, type Workspace } from './lib/model';

export function AnalysisPanel({ workspace, analysis, targets }: {
  workspace: Omit<Workspace, 'root'>; analysis: AnalysisDetails; targets: { id: string; title: string; root: string }[];
}) {
  const [selected, setSelected] = useState<string[]>([]);
  const [targetId, setTargetId] = useState('');
  const [chapter, setChapter] = useState(1);
  const [request, setRequest] = useState('');
  const [copied, setCopied] = useState(false);
  const notes = workspace.documents.filter(doc => /^(notes|segments)\//.test(doc.path));
  const usable = analysis.cards.filter(card => card.usable);
  const picked = usable.filter(card => selected.includes(card.id));
  const target = targets.find(target => target.id === targetId);
  const file = (path: string) => workspace.documents.find(doc => doc.path === path);
  const stages: [string, string | undefined, boolean][] = [
    ['来源与覆盖', file('coverage-map.md')?.path ?? file('source-manifest.md')?.path, !!file('source-manifest.md') && !!file('coverage-map.md')],
    ['分段笔记', notes[0]?.path, notes.length > 0], ['综合结论', file('sections/overview.md')?.path ?? file('overview.md')?.path, !!file('sections/overview.md') || !!file('overview.md')],
    ['复用机制', file('pattern-cards.md')?.path, usable.length > 0],
  ];
  const sections = [['overview', '总览'], ['plot-structure', '剧情结构'], ['timeline', '时间线'], ['character-system', '人物系统'], ['worldbuilding', '世界规则'], ['themes', '主题表达'], ['style-technique', '叙事技法'], ['market-highlights', '读者回报']];
  async function copyRequest(prepare: boolean) {
    const prompt = prepare
      ? `使用 $produce-long-form-novel 继续整理拆书工作区 ${JSON.stringify(analysis.root)}。先核对 analysis-state.yaml、coverage-map.md 和已完成笔记，仅对已读范围生成有证据、前提、失败方式及不可照搬元素的可复用机制。按 references/analysis-to-novel.md 整理 pattern-cards.md 和 pattern-cards.yaml，运行 analysis_reference.py inspect 校验。保留已有编辑，缺少材料时明确缺口。${target ? `\n随后结合目标小说 ${JSON.stringify(target.root)} 的简报和当前计划，提出适合使用的机制与原创改造方案。` : ''}`
      : `使用 $produce-long-form-novel 将拆书 ${JSON.stringify(analysis.root)} 的 ${picked.map(card => card.id).join('、')} 用于小说 ${JSON.stringify(target!.root)} 的第 ${chapter} 章。\n先读取 references/analysis-to-novel.md、本书简报、章节计划和必要连续性资料，判断这些机制是否适合本章；不合适时说明原因，不强行采用。针对每个适用机制提出用途、原创改造、不采用的元素及可检验效果，写入 context-packages/chapter-${String(chapter).padStart(3, '0')}.references.yaml。当前机制清单指纹为 ${analysis.registryFingerprint}，仍须重新核对来源与证据。\n运行 analysis_reference.py validate 后，用 novelctl context 装配上下文，并按本书既有审批和保护规则推进。参考方法不得变成本书事实，审校中记录采用效果与过度相似风险。`;
    setRequest(prompt); setCopied(false);
    try { await navigator.clipboard.writeText(prompt); setCopied(true); } catch { /* Read-only text remains selectable when clipboard access is unavailable. */ }
  }
  return <section className="analysis-dashboard" aria-label="拆书工作台">
    <div className="analysis-heading"><span className="eyebrow">FROM READING TO WRITING</span><h2>让拆书结论，成为创作方法</h2><p>先看依据覆盖了哪里，再选择适合本书的机制。</p></div>
    <div className="analysis-coverage"><div><small>覆盖声明</small><strong>{analysis.coverage === 'full' ? '全量覆盖（来源声明）' : analysis.coverage === 'sampled' ? '部分覆盖' : '尚未登记'}</strong></div><div><small>计划分析范围</small><strong>{analysis.scope || '尚未登记'}</strong></div><div><small>实际已读范围</small><strong>{analysis.readScope || '查看覆盖地图'}</strong></div><div><small>已保存分段笔记</small><strong>{notes.length} 份</strong></div></div>
    <p className="analysis-scope-note">计划范围不代表已经读完。{analysis.remainingScope && <>窗口外范围：{analysis.remainingScope}。</>}{file('coverage-map.md') && <Link to={documentUrl(workspace.id, 'coverage-map.md')}>查看覆盖与缺口 <ArrowUpRight size={13} /></Link>}</p>
    <div className="analysis-stages">{stages.map(([title, path, available]) => <div key={title}>{available ? <CheckCircle2 size={18} /> : <Circle size={18} />}<span>{path ? <Link to={documentUrl(workspace.id, path)}>{title}</Link> : title}</span><small>{available ? '已有资料' : '待整理'}</small></div>)}</div>
    <section className="analysis-section"><h3>专项分析</h3><div className="analysis-sections">{sections.map(([name, title]) => {
      const doc = file(`sections/${name}.md`) ?? file(`${name}.md`);
      return doc ? <Link key={name} to={documentUrl(workspace.id, doc.path)}><span>{title}</span><small>{doc.status === 'stale' || doc.status === 'changed' ? '需核对' : '查看资料'}</small><ArrowUpRight size={14} /></Link> : <div key={name}><span>{title}</span><small>尚未生成</small></div>;
    })}</div></section>
    {analysis.warnings.length > 0 && <aside className="notice">{analysis.warnings.map(warning => <p key={warning}>{warning}</p>)}</aside>}
    <section className="analysis-section"><h3><Layers3 size={19} /> 可复用机制 <small>{usable.length} 张可选</small></h3>
      {analysis.cards.length === 0 ? <div className="mechanism-empty"><p>已有笔记可以支撑进一步整理，尚未形成经过校验的机制卡。</p><p>把“发生了什么”整理为“为什么有效、什么条件下适用、怎样在新故事里重新设计”。</p><button className="analysis-action" onClick={() => void copyRequest(true)}><Copy size={15} />复制整理请求</button>{file('pattern-cards.md') && <Link to={documentUrl(workspace.id, 'pattern-cards.md')}>查看已有文字机制卡</Link>}</div>
        : <div className="mechanism-list">{analysis.cards.map((card, index) => <article className={`mechanism-card ${!card.usable ? 'unavailable' : ''}`} key={`${card.id}-${index}`}><label><input type="checkbox" disabled={!card.usable} checked={picked.some(item => item.id === card.id)} onChange={event => setSelected(event.target.checked ? [...selected, card.id] : selected.filter(id => id !== card.id))} /><span><small>{card.id} · {card.scope}</small><strong>{card.title || '待完善机制'}</strong></span></label><p>{card.problem}</p><dl><dt>运作方式</dt><dd>{card.mechanism}</dd><dt>读者回报</dt><dd>{card.payoff}</dd></dl><details><summary>适用条件、失败方式与证据</summary><p>前提：{card.prerequisites.join('；')}</p><p>失败方式：{card.failure_modes.join('；')}</p><p>不可照搬：{card.forbidden_elements.join('；')}</p>{card.evidence.map((item, index) => <Link key={index} to={documentUrl(workspace.id, item.path) + (item.anchor ? `#${encodeURIComponent(item.anchor)}` : '')}>{item.path} ↗</Link>)}</details>{card.issues.length > 0 && <p className="mechanism-issues">{card.issues.join('；')}</p>}</article>)}</div>}
    </section>
    <section className="analysis-transfer"><h3>用到我的小说</h3><p>选择目标作品与章节。Codex 会结合本书计划判断适用性，并给出具体改造；本页只准备接入请求。</p><div className="transfer-controls"><label>目标小说<select value={targetId} onChange={event => setTargetId(event.target.value)}><option value="">请选择作品</option>{targets.map(target => <option key={target.id} value={target.id}>{target.title}</option>)}</select></label><label>目标章节<input type="number" min={1} max={99999} step={1} value={chapter} onChange={event => setChapter(Math.max(1, Math.min(99999, Math.trunc(Number(event.target.value) || 1))))} /></label></div><p className="transfer-hint">{targets.length === 0 ? '当前阅读目录里没有小说工作区；加入后即可选择。' : `已选择 ${picked.length} 张机制，通常一章只需 1–3 张。`}</p><button className="analysis-action" disabled={!target || picked.length === 0} onClick={() => void copyRequest(false)}><Copy size={15} />复制接入请求</button></section>
    {request && <aside className="transfer-request" aria-live="polite"><p>{copied ? '已复制，可粘贴到 Codex 继续。' : '请求已准备，可选中文本复制到 Codex。'}</p><textarea aria-label="拆书接入请求" readOnly value={request} rows={7} /><p>生成完成后，回到小说工作区查看章节参考与审校记录。</p></aside>}
  </section>;
}

export function NovelReferencePanel({ references, sources }: { references: ReferenceUsage[]; sources: { id: string; title: string }[] }) {
  return <section className="novel-references"><h2><Layers3 size={19} /> 本书的拆书参考</h2>{references.length === 0 ? <><p>尚未选择章节参考。可以到拆书工作台，先整理机制，再结合本书计划提出改造方案。</p><div className="reference-sources">{sources.map(source => <Link key={source.id} to={`/workspaces/${source.id}`}>{source.title} <ArrowUpRight size={13} /></Link>)}</div></> : references.map((reference, index) => <article key={`${reference.chapter}-${reference.id}-${index}`}><div className="reference-heading"><strong>第 {reference.chapter} 章 · {reference.title}</strong><small>{reference.matched ? '来源匹配 · 待装配校验' : '需重新核对'}</small></div><p>{reference.useFor}</p><details><summary>查看本书改造与审校目标</summary><p>改造：{reference.adaptation || '尚未登记'}</p><p>审校：{reference.successCheck || '尚未登记'}</p>{reference.sourceId ? <Link to={`/workspaces/${reference.sourceId}`}>{reference.sourceTitle} ↗</Link> : <p>{reference.sourceTitle}</p>}</details></article>)}</section>;
}
