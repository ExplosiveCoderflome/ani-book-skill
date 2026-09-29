import { createHash } from 'node:crypto';
import { readFile, readdir, realpath, stat } from 'node:fs/promises';
import path from 'node:path';
import { parse } from 'yaml';

import { documentUrl, type WorkspaceKind, type DocumentInfo, type Workspace, type Catalog } from './model';
export { documentUrl } from './model';
export type { WorkspaceKind, DocumentInfo, Workspace, Catalog } from './model';

// npm runs both development and packaged launch scripts from this optional app directory.
const repoRoot = path.resolve(process.cwd(), '../..');
const sort = new Intl.Collator('zh-CN', { numeric: true });
const ignored = new Set(['.git', 'node_modules', '.reader', '.reader-cache']);
const labels: Record<string, string> = {
  'novel-brief': '作品简报', 'story-bible': '故事主线', 'world-bible': '世界设定',
  plan: '章节计划', draft: '初稿', 'draft-humanized': '修订正文', review: '审校意见',
  'context-package': '章节上下文', overview: '拆书总览', 'analysis-overview': '拆书总览',
  'character-roster': '人物总览', 'volume-strategy': '分卷策略',
  'source-manifest': '来源与范围', 'fact-ledger': '事实台账',
  'payoff-ledger': '伏笔台账', 'resource-ledger': '资源台账',
};
const groupLabels: Record<string, string> = {
  chapters: '章节', characters: '人物', volumes: '分卷规划', continuity: '连续性',
  production: '生产与审校', 'context-packages': '上下文', exports: '导出资料',
  source: '来源资料', segments: '分段笔记', notes: '分段笔记', dimensions: '专项分析',
  evidence: '证据', patterns: '机制卡', 'pattern-cards': '机制卡',
  'mechanism-cards': '机制卡', sections: '专项分析',
};
const actionLabels: Record<string, string> = {
  novel_brief: '完善作品简报', story_bible: '完善故事主线', world_bible: '完善世界设定',
  world_and_cast: '完善世界与人物', character_roster: '整理人物档案',
  volume_strategy: '规划分卷策略', volume_skeleton: '准备卷纲', beat_sheet: '准备节奏板',
  plan: '准备章节计划', context_package: '准备章节上下文', draft: '撰写章节正文',
  humanized: '修订章节正文', review: '审校章节', repair: '修复章节问题', continuity: '更新连续性资料',
};

function actionDescription(action: Record<string, unknown>): string | undefined {
  const target = typeof action.target === 'string' ? action.target : '';
  const chapter = /^chapter_(\d+)_(.+)$/.exec(target);
  if (chapter && actionLabels[chapter[2]]) return `第 ${Number(chapter[1])} 章 · ${actionLabels[chapter[2]]}`;
  if (actionLabels[target]) return actionLabels[target];
  const analysisActions: Record<string, string> = { prepare_segment_notes: '继续分段笔记', prepare_overview: '整理阶段总览', prepare_pattern_cards: '整理可复用机制' };
  if (typeof action.type === 'string' && analysisActions[action.type]) return `${analysisActions[action.type]}${target ? ` · ${target}` : ''}`;
  return typeof action.reason === 'string' ? action.reason : undefined;
}

export function documentGroup(relative: string): string {
  const parts = relative.split('/');
  return parts.length === 1 ? '总览与设定' : groupLabels[parts[0]] ?? '其他资料';
}

export function documentTitle(relative: string, content: string): string {
  const filename = path.posix.basename(relative, '.md');
  const label = labels[filename];
  const chapter = /(?:^|\/)chapter-(\d+)(?:\/|\.)/.exec(relative);
  if (chapter && label) return `第 ${Number(chapter[1])} 章 · ${label}`;
  // Ignore headings inside YAML frontmatter and fenced examples.
  const body = content.replace(/^\uFEFF/, '').replace(/^---\r?\n[\s\S]*?\r?\n---(?:\r?\n|$)/, '');
  let fence = '';
  for (const line of body.split(/\r?\n/)) {
    const marker = /^\s{0,3}(`{3,}|~{3,})/.exec(line)?.[1];
    if (marker) { if (!fence) fence = marker[0]; else if (marker[0] === fence) fence = ''; continue; }
    if (!fence) {
      const heading = /^\s{0,3}#{1,6}\s+(.+?)(?:\s+#+)?\s*$/.exec(line)?.[1];
      if (heading) return heading.replace(/\[([^\]]+)\]\([^)]*\)/g, '$1').replace(/[*`]/g, '').trim();
    }
  }
  return label ?? filename;
}

export function isInside(root: string, candidate: string): boolean {
  const relative = path.relative(root, candidate);
  return relative === '' || (!path.isAbsolute(relative) && relative !== '..' && !relative.startsWith(`..${path.sep}`));
}

export async function safeFile(root: string, relative: string): Promise<string> {
  if (!relative || relative.includes('\0') || relative.includes('\\') || path.isAbsolute(relative)) throw new Error('无效文件路径');
  const base = await realpath(root);
  const candidate = path.resolve(base, relative);
  if (!isInside(base, candidate)) throw new Error('文件超出工作区');
  const resolved = await realpath(candidate);
  if (!isInside(base, resolved) || !(await stat(resolved)).isFile()) throw new Error('文件超出工作区或不是文件');
  return resolved;
}

function object(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

async function stateAt(root: string, kind: WorkspaceKind, warnings: string[]) {
  for (const filename of kind === 'novel' ? ['novel-state.yaml'] : ['analysis-state.yaml', 'analysis-manifest.yaml']) {
    try { return object(parse(await readFile(await safeFile(root, filename), 'utf8'))); }
    catch (error) {
      if ((error as NodeJS.ErrnoException).code !== 'ENOENT') warnings.push(`${filename} 无法读取，状态暂不可用。`);
    }
  }
  return {};
}

async function scanWorkspace(root: string, kind: WorkspaceKind): Promise<Workspace> {
  root = await realpath(root);
  const warnings: string[] = [];
  const state = await stateAt(root, kind, warnings);
  const artifactMap = new Map<string, Record<string, unknown>>();
  for (const raw of Object.values(object(state.artifacts))) {
    const artifact = object(raw);
    if (typeof artifact.path === 'string') artifactMap.set(artifact.path.replaceAll('\\', '/'), artifact);
  }
  const documents: DocumentInfo[] = [];
  async function walk(directory: string) {
    const entries = await readdir(directory, { withFileTypes: true });
    entries.sort((a, b) => sort.compare(a.name, b.name));
    for (const entry of entries) {
      if (ignored.has(entry.name) || entry.isSymbolicLink()) continue;
      const absolute = path.join(directory, entry.name);
      try {
        if (!isInside(root, await realpath(absolute))) continue;
        if (entry.isDirectory()) { await walk(absolute); continue; }
        if (!entry.isFile() || path.extname(entry.name).toLowerCase() !== '.md') continue;
        const relative = path.relative(root, absolute).split(path.sep).join('/');
        const content = await readFile(await safeFile(root, relative), 'utf8');
        const info = await stat(absolute);
        const artifact = artifactMap.get(relative);
        const fingerprint = createHash('sha256').update(content).digest('hex');
        const changed = typeof artifact?.sha256 === 'string' && artifact.sha256 !== fingerprint;
        documents.push({
          path: relative, title: documentTitle(relative, content), group: documentGroup(relative),
          updatedAt: info.mtime.toISOString(), size: info.size, fingerprint,
          status: changed ? 'changed' : typeof artifact?.status === 'string' ? artifact.status : undefined,
          approval: typeof artifact?.approval === 'string' ? artifact.approval : undefined,
          protected: typeof artifact?.protected === 'boolean' ? artifact.protected : undefined,
        });
      } catch { warnings.push(`${path.relative(root, absolute)} 暂时无法读取。`); }
    }
  }
  await walk(root);
  const novel = object(state.novel);
  const analysis = object(state.analysis);
  const action = object(state.next_action);
  const title = typeof novel.title === 'string' ? novel.title : typeof analysis.title === 'string' ? analysis.title : path.basename(root);
  return {
    id: createHash('sha256').update(root).digest('hex').slice(0, 16), title, kind, root, documents, warnings,
    revision: createHash('sha256').update(JSON.stringify([state, documents])).digest('hex'),
    updatedAt: documents.reduce((latest, doc) => doc.updatedAt > latest ? doc.updatedAt : latest, ''),
    stage: typeof novel.current_stage === 'string' ? novel.current_stage : undefined,
    nextAction: actionDescription(action),
  };
}

export function configuredRoots(): string[] {
  if (!process.env.ANI_READER_ROOTS) return [repoRoot];
  const input: unknown = JSON.parse(process.env.ANI_READER_ROOTS);
  if (!Array.isArray(input) || input.length === 0 || input.some(root => typeof root !== 'string' || !path.isAbsolute(root))) {
    throw new Error('ANI_READER_ROOTS 必须是绝对路径组成的 JSON 数组');
  }
  return [...new Set(input as string[])];
}

export async function getCatalog(roots = configuredRoots()): Promise<Catalog> {
  const warnings: string[] = [];
  const discovered = new Map<string, WorkspaceKind>();
  for (const input of roots) {
    try {
      const root = await realpath(input);
      const entries = await readdir(root, { withFileTypes: true });
      const names = new Set(entries.map(entry => entry.name));
      if (names.has('novel-state.yaml') || names.has('analysis-state.yaml') || names.has('analysis-manifest.yaml') || names.has('source-manifest.md')) {
        discovered.set(root, names.has('novel-state.yaml') ? 'novel' : 'analysis');
        continue;
      }
      for (const [category, kind] of [['novels', 'novel'], ['analyses', 'analysis']] as const) {
        const directory = path.basename(root) === category ? root : path.join(root, category);
        try {
          const canonical = await realpath(directory);
          if (!isInside(root, canonical)) continue;
          for (const entry of await readdir(canonical, { withFileTypes: true })) {
            if (!entry.isDirectory() || entry.isSymbolicLink() || entry.name.startsWith('.')) continue;
            const workspace = await realpath(path.join(canonical, entry.name));
            if (isInside(canonical, workspace)) discovered.set(workspace, kind);
          }
        } catch (error) {
          if ((error as NodeJS.ErrnoException).code !== 'ENOENT') warnings.push(`${directory} 暂时无法读取。`);
        }
      }
    } catch { warnings.push(`${input} 无法访问，请检查阅读目录配置。`); }
  }
  const workspaces: Workspace[] = [];
  for (const [root, kind] of discovered) {
    try { workspaces.push(await scanWorkspace(root, kind)); }
    catch { warnings.push(`${root} 暂时无法读取。`); }
  }
  workspaces.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt) || sort.compare(a.title, b.title));
  return { workspaces, warnings, roots };
}

export async function findWorkspace(id: string): Promise<Workspace> {
  const workspace = (await getCatalog()).workspaces.find(item => item.id === id);
  if (!workspace) throw new Response('工作区不存在或已移走', { status: 404 });
  return workspace;
}

export function resolveContentLink(workspace: Pick<Workspace, 'id' | 'documents'>, current: string, href: string): string | undefined {
  if (!href || href.startsWith('#')) return href;
  if (/^(https?:|mailto:)/i.test(href)) return href;
  if (/^[a-z][a-z\d+.-]*:/i.test(href) || href.startsWith('//') || href.includes('\\')) return undefined;
  try {
    const url = new URL(href, `http://reader/${current.split('/').map(encodeURIComponent).join('/')}`);
    const relative = decodeURIComponent(url.pathname.slice(1));
    if (workspace.documents.some(doc => doc.path === relative)) return documentUrl(workspace.id, relative) + url.hash;
    return `/assets/${workspace.id}/${relative.split('/').map(encodeURIComponent).join('/')}` + url.hash;
  } catch { return undefined; }
}
