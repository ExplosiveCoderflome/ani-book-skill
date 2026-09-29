import { readFile, readdir, realpath } from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { parse } from 'yaml';
import { safeFile, isInside, type Workspace } from './workspaces.server';

export interface MechanismCard {
  id: string; title: string; scope: string; problem: string; mechanism: string; payoff: string;
  prerequisites: string[]; failure_modes: string[]; forbidden_elements: string[];
  evidence: { path: string; sha256: string; anchor?: string }[];
  usable: boolean; issues: string[];
}
export interface AnalysisDetails {
  root: string; status?: string; profile?: string; coverage?: string; scope?: string;
  readScope?: string; remainingScope?: string; sourceFingerprint?: string;
  cards: MechanismCard[]; registryFingerprint?: string; warnings: string[];
}
export interface ReferenceUsage { chapter: number; id: string; title: string; sourceId?: string; sourceTitle: string; useFor: string; adaptation: string; successCheck: string; matched: boolean }

const object = (value: unknown): Record<string, unknown> => value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
const string = (value: unknown) => typeof value === 'string' ? value : '';
const strings = (value: unknown): string[] => Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string' && !!item.trim()) : [];

export async function getAnalysisDetails(workspace: Workspace): Promise<AnalysisDetails> {
  const result: AnalysisDetails = { root: workspace.root, cards: [], warnings: [] };
  let state: Record<string, unknown>;
  try { state = object(parse(await readFile(await safeFile(workspace.root, 'analysis-state.yaml'), 'utf8'))); }
  catch { result.warnings.push('分析状态暂不可读，覆盖范围与机制状态需要回看原资料。'); return result; }
  const source = object(state.source), analysis = object(state.analysis);
  Object.assign(result, { coverage: string(source.coverage), scope: string(source.scope),
    readScope: string(source.read_scope), remainingScope: string(source.remaining_scope),
    sourceFingerprint: string(source.fingerprint), status: string(analysis.status), profile: string(analysis.profile) });
  let registry: Record<string, unknown>;
  try {
    const bytes = await readFile(await safeFile(workspace.root, 'pattern-cards.yaml'));
    result.registryFingerprint = createHash('sha256').update(bytes).digest('hex');
    registry = object(parse(bytes.toString('utf8')));
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== 'ENOENT') result.warnings.push('机制卡清单暂不可读，请检查 pattern-cards.yaml。');
    return result;
  }
  if (registry.schema_version !== 1 || !Array.isArray(registry.cards)) { result.warnings.push('机制卡清单格式需要更新。'); return result; }
  const registrySource = object(registry.source);
  const sourceChanged = !['sampled', 'full'].includes(string(source.coverage)) || ['fingerprint', 'scope', 'coverage'].some(key => !string(source[key]).trim() || source[key] !== registrySource[key]);
  const ids = new Set<string>();
  const duplicateIds = new Set<string>();
  for (const raw of registry.cards) { const id = string(object(raw).id); if (ids.has(id)) duplicateIds.add(id); ids.add(id); }
  const invalidRegistryIds = duplicateIds.size > 0 || [...ids].some(id => !/^PATTERN-\d{3,}$/.test(id));
  for (const raw of registry.cards) {
    const card = object(raw);
    const issues: string[] = [];
    if (sourceChanged) issues.push('来源或范围已变化，需要重新核对');
    if (invalidRegistryIds) issues.push('清单含无效或重复的机制编号');
    if (card.status !== 'ready') issues.push('机制尚未就绪');
    for (const key of ['title', 'scope', 'problem', 'mechanism', 'payoff']) if (!string(card[key]).trim()) issues.push('机制说明不完整');
    for (const key of ['prerequisites', 'failure_modes', 'forbidden_elements']) {
      if (!Array.isArray(card[key]) || !card[key].length || strings(card[key]).length !== card[key].length) issues.push('机制边界不完整');
    }
    const evidence = Array.isArray(card.evidence) ? card.evidence.map(raw => { const item = object(raw); return { path: string(item.path), sha256: string(item.sha256), anchor: string(item.anchor) }; }) : [];
    if (!evidence.length) issues.push('缺少证据');
    for (const item of evidence) {
      try {
        if (!item.path.toLowerCase().endsWith('.md') || item.path.split('/').includes('..') || ['source', 'retrieval'].includes(item.path.split('/')[0])) throw new Error();
        const actual = createHash('sha256').update(await readFile(await safeFile(workspace.root, item.path))).digest('hex');
        if (actual !== item.sha256) issues.push('证据文件已有修改');
        for (const raw of Object.values(object(state.artifacts))) {
          const artifact = object(raw);
          if (artifact.path === item.path && (['stale', 'blocked', 'missing', 'in_progress'].includes(string(artifact.status)) || artifact.sha256 && artifact.sha256 !== actual)) issues.push('证据状态需要核对');
        }
      } catch { issues.push('证据不存在或超出工作区'); }
    }
    result.cards.push({ id: string(card.id), title: string(card.title), scope: string(card.scope), problem: string(card.problem),
      mechanism: string(card.mechanism), payoff: string(card.payoff), prerequisites: strings(card.prerequisites),
      failure_modes: strings(card.failure_modes), forbidden_elements: strings(card.forbidden_elements), evidence,
      usable: issues.length === 0, issues: [...new Set(issues)] });
  }
  return result;
}

export async function getNovelReferences(workspace: Workspace, sources: Workspace[]): Promise<ReferenceUsage[]> {
  const result: ReferenceUsage[] = [];
  const details = new Map<string, AnalysisDetails>();
  const normalize = (value: string) => process.platform === 'win32' ? path.normalize(value).toLowerCase() : path.normalize(value);
  let directory: string;
  try { directory = await realpath(path.join(workspace.root, 'context-packages')); if (!isInside(workspace.root, directory)) return []; }
  catch { return []; }
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const chapter = /^chapter-(\d+)\.references\.yaml$/.exec(entry.name)?.[1];
    if (!chapter || !entry.isFile() || entry.isSymbolicLink()) continue;
    try {
      const selection = object(parse(await readFile(await safeFile(workspace.root, `context-packages/${entry.name}`), 'utf8')));
      const validChapter = selection.schema_version === 1 && selection.chapter === Number(chapter) && Number(chapter) > 0;
      if (!validChapter || !Array.isArray(selection.items) || selection.items.length === 0) throw new Error('invalid reference selection');
      for (const raw of Array.isArray(selection.items) ? selection.items : []) {
        const item = object(raw);
        // Never follow unregistered absolute paths found inside a selection file.
        const source = sources.find(source => normalize(source.root) === normalize(string(item.analysis_workspace)));
        let detail: AnalysisDetails | undefined;
        if (source) { detail = details.get(source.id) ?? await getAnalysisDetails(source); details.set(source.id, detail); }
        const card = detail?.cards.find(card => card.id === item.pattern_id);
        result.push({ chapter: Number(chapter), id: string(item.pattern_id), title: card?.title ?? string(item.pattern_id), sourceId: source?.id,
          sourceTitle: source?.title ?? '来源未加入当前书架', useFor: string(item.use_for), adaptation: string(item.adaptation), successCheck: string(item.success_check),
          matched: validChapter && !!card?.usable && detail?.registryFingerprint === item.registry_sha256 });
      }
    } catch { result.push({ chapter: Number(chapter), id: entry.name, title: '参考清单暂不可读', sourceTitle: '', useFor: '', adaptation: '', successCheck: '', matched: false }); }
  }
  return result.sort((a, b) => a.chapter - b.chapter);
}
