import { useState } from 'react';
import { Link, useLoaderData } from 'react-router';
import { ArrowUpRight, BookOpen, Files, Library, ScrollText } from 'lucide-react';
import { getCatalog } from '../lib/workspaces.server';
import { LibraryHeader } from '../components';

export async function loader() {
  const catalog = await getCatalog();
  return { ...catalog, workspaces: catalog.workspaces.map(({ root: _root, ...workspace }) => workspace) };
}

export default function Home() {
  const { workspaces, warnings, roots } = useLoaderData<typeof loader>();
  const [filter, setFilter] = useState('all');
  const [query, setQuery] = useState('');
  const visible = workspaces.filter(workspace => (filter === 'all' || workspace.kind === filter) && workspace.title.toLocaleLowerCase().includes(query.toLocaleLowerCase()));
  const count = workspaces.reduce((total, workspace) => total + workspace.documents.length, 0);
  return <><LibraryHeader /><main className="library-main">
    <section className="library-hero"><div><span className="eyebrow">YOUR STORIES, IN ONE PLACE</span><h1>把故事，读清楚。</h1><p>拆书的发现，创作的脉络。<br />让散落在文件里的内容，回到同一张书桌。</p><span className="local-pill"><span />本地资料 · 自动更新</span></div><div className="hero-mark" aria-hidden="true"><span>读</span><div className="hero-caption">阅读 · 理解 · 继续创作</div></div></section>
    <section className="library-stats" aria-label="资料统计"><div><Library size={19} /><strong>{workspaces.length}</strong><span>工作区</span></div><div><ScrollText size={19} /><strong>{workspaces.filter(workspace => workspace.kind === 'analysis').length}</strong><span>拆书项目</span></div><div><BookOpen size={19} /><strong>{workspaces.filter(workspace => workspace.kind === 'novel').length}</strong><span>小说作品</span></div><div><Files size={19} /><strong>{count}</strong><span>Markdown 资料</span></div></section>
    {warnings.length > 0 && <aside className="notice" role="status">{warnings.map(warning => <p key={warning}>{warning}</p>)}</aside>}
    <section className="shelf"><div className="shelf-toolbar"><div className="filter-tabs" aria-label="工作区类型">{[['all', '全部资料'], ['analysis', '拆书'], ['novel', '小说']].map(([value, label]) => <button key={value} className={filter === value ? 'active' : ''} aria-pressed={filter === value} onClick={() => setFilter(value)}>{label}</button>)}</div><input className="shelf-filter" aria-label="筛选作品" placeholder="按作品名称筛选…" value={query} onChange={event => setQuery(event.target.value)} /></div>
      <div className="workspace-grid">{visible.map((workspace, index) => <Link className={`workspace-card kind-${workspace.kind}`} to={`/workspaces/${workspace.id}`} key={workspace.id}><div className="card-top"><span>{workspace.kind === 'analysis' ? '拆书资料' : '小说作品'}</span><span className="card-number">{String(index + 1).padStart(2, '0')}</span></div><div className="card-icon">{workspace.kind === 'analysis' ? <ScrollText size={27} strokeWidth={1.2} /> : <BookOpen size={27} strokeWidth={1.2} />}</div><h2>{workspace.title}</h2><p>{workspace.nextAction ?? (workspace.kind === 'analysis' ? '从分段笔记到机制发现，回看每一条依据。' : '从设定、规划到章节正文，沿着故事继续读。')}</p><div className="card-bottom"><span>{workspace.documents.length} 份资料<span className="card-date">{workspace.updatedAt ? ` · ${workspace.updatedAt.slice(0, 10)}` : ''}</span></span><ArrowUpRight size={18} /></div></Link>)}</div>
      {visible.length === 0 && <div className="empty-state"><BookOpen size={32} strokeWidth={1.2} /><h2>{workspaces.length ? '没有匹配的作品' : '书架还没有资料'}</h2><p>{workspaces.length ? '试试其他名称，或切换资料类型。' : '配置含 novels/ 或 analyses/ 的本地目录，再刷新书架。'}</p></div>}
    </section><footer className="library-footer"><span>文件仍保存在原来的工作区。</span><details><summary>正在阅读的目录</summary>{roots.map(root => <code key={root}>{root}</code>)}</details></footer>
  </main></>;
}
