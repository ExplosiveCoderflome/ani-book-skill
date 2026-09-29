import { useMemo, useState } from 'react';
import { Link, useLoaderData, useSearchParams, type LoaderFunctionArgs } from 'react-router';
import { DocsLayout } from 'fumadocs-ui/layouts/docs';
import { DocsPage, DocsBody, DocsTitle } from 'fumadocs-ui/layouts/docs/page';
import defaultMdxComponents from 'fumadocs-ui/mdx';
import { rendererFromSerialized } from '@fumadocs/local-md/client';
import type * as PageTree from 'fumadocs-core/page-tree';
import { ArrowLeft, ArrowRight, FileText, FolderTree, List, BookOpen } from 'lucide-react';
import { getCatalog } from '../lib/workspaces.server';
import { getAnalysisDetails, getNovelReferences } from '../lib/analysis.server';
import { AnalysisPanel, NovelReferencePanel } from '../analysis-panel';
import { documentUrl, type Workspace } from '../lib/model';
import { loadDocument } from '../lib/content.server';
import { Brand, LiveRefresh, StatusBadge, DocumentLink } from '../components';

export async function loader({ params }: LoaderFunctionArgs) {
  const catalog = await getCatalog();
  const workspace = catalog.workspaces.find(workspace => workspace.id === params.id);
  if (!workspace) throw new Response('工作区不存在', { status: 404 });
  const relative = params['*'];
  const current = relative ? workspace.documents.find(document => document.path === relative) : undefined;
  if (relative && !current) throw new Response('资料不存在', { status: 404 });
  const render = current ? await loadDocument(workspace, current) : undefined;
  const { root: _root, ...publicWorkspace } = workspace;
  const analysis = workspace.kind === 'analysis' && !current ? await getAnalysisDetails(workspace) : undefined;
  const targets = analysis ? catalog.workspaces.filter(workspace => workspace.kind === 'novel').map(({ id, title, root }) => ({ id, title, root })) : [];
  const analysisSources = catalog.workspaces.filter(workspace => workspace.kind === 'analysis');
  const references = workspace.kind === 'novel' && !current ? await getNovelReferences(workspace, analysisSources) : undefined;
  return { workspace: publicWorkspace, current, render, analysis, targets, references, sources: analysisSources.map(({ id, title }) => ({ id, title })) };
}

function buildTree(workspace: Pick<Workspace, 'id' | 'title' | 'documents'>, files: boolean): PageTree.Root {
  const tree: PageTree.Root = { name: workspace.title, children: [{ type: 'page', name: '工作区总览', url: `/workspaces/${workspace.id}` }] };
  const groupOrder = ['总览与设定', '章节', '分段笔记', '专项分析', '人物', '分卷规划', '机制卡', '证据', '连续性', '上下文', '生产与审校', '来源资料', '其他资料'];
  const documents = files ? workspace.documents : [...workspace.documents].sort((a, b) => groupOrder.indexOf(a.group) - groupOrder.indexOf(b.group));
  for (const document of documents) {
    const folders = files ? document.path.split('/').slice(0, -1) : [document.group];
    let children = tree.children;
    for (const name of folders) {
      let folder = children.find(node => node.type === 'folder' && node.name === name) as PageTree.Folder | undefined;
      if (!folder) { folder = { type: 'folder', name, children: [], defaultOpen: files ? folders.length === 1 : ['总览与设定', '章节', '分段笔记'].includes(name) }; children.push(folder); }
      children = folder.children;
    }
    children.push({ type: 'page', name: files ? document.path.split('/').at(-1)! : document.title, url: documentUrl(workspace.id, document.path) });
  }
  return tree;
}

export default function WorkspacePage() {
  const { workspace, current, render, analysis, targets, references, sources } = useLoaderData<typeof loader>();
  const [searchParams, setSearchParams] = useSearchParams();
  const files = searchParams.get('view') === 'files';
  const tree = useMemo(() => buildTree(workspace, files), [workspace, files]);
  const parsed = useMemo(() => render ? rendererFromSerialized(render).renderSync(defaultMdxComponents) : undefined, [render]);
  const [fontSize, setFontSize] = useState(18);
  const [showSource, setShowSource] = useState(false);
  const prose = !!current && /(?:^|\/)draft(?:-humanized)?\.md$/i.test(current.path);
  const chapters = workspace.documents.filter(document => /chapters\/chapter-\d+\/draft(?:-humanized)?\.md$/i.test(document.path));
  const preferred = chapters.filter(document => document.path.endsWith('draft-humanized.md') || !chapters.some(other => other.path === document.path.replace(/draft\.md$/, 'draft-humanized.md')));
  const navigation = prose ? preferred : workspace.documents;
  const chapterDir = current?.path.slice(0, current.path.lastIndexOf('/'));
  const index = navigation.findIndex(document => prose ? document.path.slice(0, document.path.lastIndexOf('/')) === chapterDir : document.path === current?.path);
  const previous = index > 0 ? navigation[index - 1] : undefined;
  const next = index >= 0 ? navigation[index + 1] : undefined;
  const rawPath = current ? `/assets/${workspace.id}/${current.path.split('/').map(encodeURIComponent).join('/')}` : '';
  const documentGroups = Array.from(new Set(workspace.documents.map(document => document.group))).map(group => <section className="overview-section" key={group}><h2>{group}<span>{workspace.documents.filter(document => document.group === group).length}</span></h2>{workspace.documents.filter(document => document.group === group).map(document => <DocumentLink key={document.path} title={document.title} detail={document.path} href={documentUrl(workspace.id, document.path)} />)}</section>);
  return <DocsLayout tree={tree} tabs={false}
    nav={{ title: <Brand />, url: '/' }}
    links={[{ text: '返回书架', url: '/', icon: <ArrowLeft size={15} /> }]}
    sidebar={{ defaultOpenLevel: 1, banner: <div className="workspace-sidebar-head"><span className="eyebrow">{workspace.kind === 'analysis' ? 'BOOK ANALYSIS' : 'NOVEL WORKSPACE'}</span><h2>{workspace.title}</h2><div className="view-toggle"><button aria-pressed={!files} className={!files ? 'active' : ''} onClick={() => setSearchParams({})}><List size={13} />资料视图</button><button aria-pressed={files} className={files ? 'active' : ''} onClick={() => setSearchParams({ view: 'files' })}><FolderTree size={13} />全部文件</button></div></div>, footer: <div className="sidebar-footer"><span>{workspace.documents.length} 份资料</span><LiveRefresh compact /></div> }}
  ><DocsPage toc={parsed?.toc ?? []} footer={{ enabled: false }} tableOfContent={{ enabled: !!parsed?.toc.length }} tableOfContentPopover={{ enabled: !!parsed?.toc.length }} breadcrumb={{ enabled: false }}
    className={prose ? 'reader-page prose-page' : 'reader-page'} style={{ '--reader-font-size': `${fontSize}px` } as React.CSSProperties}>
    <div className="page-kicker"><Link to={`/workspaces/${workspace.id}`}>{workspace.title}</Link><span>/</span><span>{current?.group ?? '工作区总览'}</span></div>
    {current ? <><DocsTitle>{current.title}</DocsTitle><div className="document-meta"><StatusBadge status={current.status} /><span>{current.updatedAt.slice(0, 10)}</span><span>{Math.ceil(current.size / 1024)} KB</span>{current.protected && <span>作者已保护</span>}<LiveRefresh /></div>
      <div className="reading-toolbar"><div><button aria-label="减小字号" disabled={fontSize <= 14} onClick={() => setFontSize(size => Math.max(14, size - 2))}>A−</button><span>{fontSize}</span><button aria-label="增大字号" disabled={fontSize >= 26} onClick={() => setFontSize(size => Math.min(26, size + 2))}>A＋</button></div><button onClick={() => setShowSource(value => !value)}><FileText size={14} />{showSource ? '收起来源' : '查看来源'}</button></div>
      {showSource && <aside className="source-info"><code>{current.path}</code><span>SHA-256：{current.fingerprint}</span><a href={rawPath} target="_blank" rel="noreferrer">打开原始 Markdown ↗</a></aside>}
      <DocsBody className="reader-content">{parsed?.body}</DocsBody>
      <nav className="document-pagination" aria-label={prose ? '章节导航' : '资料导航'}>{previous ? <Link to={documentUrl(workspace.id, previous.path)}><ArrowLeft size={17} /><span><small>{prose ? '上一章' : '上一篇'}</small>{previous.title}</span></Link> : <span />}{next && <Link to={documentUrl(workspace.id, next.path)}><span><small>{prose ? '下一章' : '下一篇'}</small>{next.title}</span><ArrowRight size={17} /></Link>}</nav>
    </> : <><DocsTitle>{workspace.title}</DocsTitle><p className="workspace-description">{workspace.kind === 'analysis' ? '回看分析结论，沿着笔记与证据重新理解这本书。' : '沿着设定、规划和正文，继续你的故事。'}</p><div className="workspace-summary"><div><strong>{workspace.documents.length}</strong><span>资料文件</span></div><div><strong>{new Set(workspace.documents.map(document => document.group)).size}</strong><span>资料分类</span></div><div><strong>{analysis ? analysis.cards.filter(card => card.usable).length : preferred.length}</strong><span>{analysis ? '可选机制' : '正文章节'}</span></div></div>
      {workspace.nextAction && <aside className="next-action"><span className="eyebrow">下一步</span><p>{workspace.nextAction}</p></aside>}
      {workspace.warnings.length > 0 && <aside className="notice">{workspace.warnings.map(warning => <p key={warning}>{warning}</p>)}</aside>}
      {analysis && <AnalysisPanel workspace={workspace} analysis={analysis} targets={targets} />}
      {references && <NovelReferencePanel references={references} sources={sources} />}
      {preferred.length > 0 && <section className="overview-section"><h2><BookOpen size={19} />继续阅读正文</h2><DocumentLink title={preferred[0].title} detail="按章节顺序阅读，可随时查看计划与审校" href={documentUrl(workspace.id, preferred[0].path)} /></section>}
      {analysis ? <details className="analysis-files"><summary>全部分析资料 · {workspace.documents.length} 份</summary>{documentGroups}</details> : documentGroups}
      {workspace.documents.length === 0 && <div className="empty-state"><FileText size={28} /><p>这个工作区暂时没有 Markdown 资料。</p></div>}
    </>}
  </DocsPage></DocsLayout>;
}
