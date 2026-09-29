import assert from 'node:assert/strict';
import test from 'node:test';
import { mkdtemp, mkdir, readFile, writeFile, symlink, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { getCatalog, safeFile, documentTitle, documentUrl, resolveContentLink } from '../app/lib/workspaces.server';
import { loadDocument, searchWorkspace } from '../app/lib/content.server';
import { rendererFromSerialized } from '@fumadocs/local-md/client';
import { renderToStaticMarkup } from 'react-dom/server';
import { getAnalysisDetails, getNovelReferences } from '../app/lib/analysis.server';
import { createHash } from 'node:crypto';
import { stringify } from 'yaml';

test('real workspace reading, updates, Markdown rendering, links and Chinese search', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'ani-reader-'));
  const previousRoots = process.env.ANI_READER_ROOTS;
  try {
    const novel = path.join(root, 'novels', '月灯');
    const analysis = path.join(root, 'analyses', '拆书资料');
    await mkdir(path.join(novel, 'chapters', 'chapter-002'), { recursive: true });
    await mkdir(analysis, { recursive: true });
    const original = '# 月灯简报\n\n人物林舟。\n\n[第二章](chapters/chapter-002/draft.md#夜归)\n\n| 人物 | 欲望 |\n| --- | --- |\n| 林舟 | 真相 |\n\n<script>alert(1)</script>\n\n{这不是 JSX} <不是组件>\n';
    await writeFile(path.join(novel, 'novel-brief.md'), original);
    await writeFile(path.join(novel, 'novel-state.yaml'), 'novel:\n  title: 月灯\nartifacts:\n  brief:\n    path: novel-brief.md\n    status: ready\n    sha256: old\n');
    await writeFile(path.join(novel, 'chapters/chapter-002/draft.md'), '# 夜归\n\n林舟走进灯下。');
    await writeFile(path.join(analysis, 'overview.md'), '# 拆书总览\n\n信息差驱动冲突。');
    process.env.ANI_READER_ROOTS = JSON.stringify([root]);
    const catalog = await getCatalog();
    assert.equal(catalog.workspaces.length, 2);
    const workspace = catalog.workspaces.find(workspace => workspace.kind === 'novel')!;
    assert.equal(workspace.title, '月灯');
    const doc = workspace.documents.find(doc => doc.path === 'novel-brief.md')!;
    assert.equal(doc.status, 'changed');
    assert.equal(workspace.documents.find(doc => doc.path.endsWith('draft.md'))?.title, '第 2 章 · 初稿');
    const render = await loadDocument(workspace, doc);
    assert.equal(render.type, 'ast');
    const html = renderToStaticMarkup(rendererFromSerialized(render).renderSync().body);
    assert.ok(html.includes('<table>'));
    assert.ok(html.includes(`${documentUrl(workspace.id, 'chapters/chapter-002/draft.md')}#${encodeURIComponent('夜归')}`));
    assert.ok(!html.includes('<script>'));
    assert.ok(html.includes('{这不是 JSX}'));
    const response = await searchWorkspace(new Request(`http://localhost/api/search?query=${encodeURIComponent('林舟')}&tag=${workspace.id}`));
    assert.equal(response.status, 200);
    const matches = await response.json() as { url: string }[];
    assert.ok(matches.length > 0);
    assert.ok(matches.every(match => match.url.startsWith(`/workspaces/${workspace.id}/`)));
    const oldRevision = workspace.revision;
    await writeFile(path.join(novel, 'novel-brief.md'), '# 已更新的简报\n\n赵平握住钥匙。');
    await writeFile(path.join(novel, 'new-note.md'), '# 新资料');
    const refreshed = (await getCatalog()).workspaces.find(item => item.id === workspace.id)!;
    assert.notEqual(refreshed.revision, oldRevision);
    assert.equal(refreshed.documents.length, 3);
    const newer = await loadDocument(refreshed, refreshed.documents.find(item => item.path === 'novel-brief.md')!);
    assert.ok(renderToStaticMarkup(rendererFromSerialized(newer).renderSync().body).includes('赵平'));
    const newResponse = await searchWorkspace(new Request(`http://localhost/api/search?query=${encodeURIComponent('赵平')}&tag=${workspace.id}`));
    assert.ok((await newResponse.json() as unknown[]).length > 0);
    assert.equal(await readFile(path.join(novel, 'novel-state.yaml'), 'utf8'), 'novel:\n  title: 月灯\nartifacts:\n  brief:\n    path: novel-brief.md\n    status: ready\n    sha256: old\n');
    assert.equal((await getCatalog([novel])).workspaces.length, 1);
    assert.equal((await getCatalog([path.join(root, 'novels')])).workspaces.length, 1);
  } finally {
    if (previousRoots === undefined) delete process.env.ANI_READER_ROOTS; else process.env.ANI_READER_ROOTS = previousRoots;
    assert.equal(path.dirname(root), os.tmpdir());
    assert.ok(path.basename(root).startsWith('ani-reader-'));
    await rm(root, { recursive: true, force: true });
  }
});

test('reject traversal and symlinks, preserve filenames and unrelated Markdown', async () => {
  const temporary = await mkdtemp(path.join(os.tmpdir(), 'ani-reader-boundary-'));
  try {
    const root = path.join(temporary, 'novels', '测试');
    await mkdir(root, { recursive: true });
    await writeFile(path.join(root, '名字 [一].md'), '# 无 frontmatter 的笔记');
    await writeFile(path.join(temporary, 'secret.md'), 'private outside workspace');
    await assert.rejects(safeFile(root, '../../secret.md'));
    await assert.rejects(safeFile(root, '..\\..\\secret.md'));
    await assert.rejects(safeFile(root, path.join(temporary, 'secret.md')));
    await symlink(temporary, path.join(root, 'outside'), 'junction');
    await assert.rejects(safeFile(root, 'outside/secret.md'));
    const workspace = (await getCatalog([temporary])).workspaces[0];
    assert.equal(workspace.documents.length, 1);
    const render = await loadDocument(workspace, workspace.documents[0]);
    assert.ok(renderToStaticMarkup(rendererFromSerialized(render).renderSync().body).includes('无 frontmatter'));
    assert.equal(resolveContentLink(workspace, '名字 [一].md', 'javascript:alert(1)'), undefined);
    assert.equal(documentTitle('notes/no-heading.md', '---\ntitle: YAML title\n---\n```md\n# Example\n```\n# Actual heading'), 'Actual heading');
  } finally {
    assert.equal(path.dirname(temporary), os.tmpdir());
    assert.ok(path.basename(temporary).startsWith('ani-reader-boundary-'));
    await rm(temporary, { recursive: true, force: true });
  }
});

test('analysis coverage stays honest and evidence changes disable reusable mechanisms', async () => {
  const temporary = await mkdtemp(path.join(os.tmpdir(), 'ani-reader-analysis-'));
  try {
    const root = path.join(temporary, 'analyses', '学习资料');
    await mkdir(path.join(root, 'notes'), { recursive: true });
    const evidence = '# 证据笔记\n\n主角主动核验线索。';
    const fingerprint = createHash('sha256').update(evidence).digest('hex');
    await writeFile(path.join(root, 'notes/segment-001.md'), evidence);
    const source = { fingerprint: `sha256:${'a'.repeat(64)}`, scope: '第1-50章', coverage: 'sampled' };
    const state = { analysis: { title: '学习资料' }, source, artifacts: { note: { path: 'notes/segment-001.md', status: 'ready', sha256: fingerprint } } };
    await writeFile(path.join(root, 'analysis-state.yaml'), stringify(state));
    const card = { id: 'PATTERN-001', title: '主动核验', status: 'ready', scope: '第1-2章', problem: '揭示缺少行动', mechanism: '主动验证引出风险', payoff: '答案与新问题', prerequisites: ['可行动线索'], failure_modes: ['没有代价'], forbidden_elements: ['源作道具'], evidence: [{ path: 'notes/segment-001.md', sha256: fingerprint }] };
    await writeFile(path.join(root, 'pattern-cards.yaml'), stringify({ schema_version: 1, source, cards: [card] }));
    const workspace = (await getCatalog([root])).workspaces[0];
    const details = await getAnalysisDetails(workspace);
    assert.equal(details.scope, '第1-50章');
    assert.equal(details.readScope, ''); // Never infer actual reading from the planned window.
    assert.equal(details.cards[0].usable, true);
    assert.ok(details.registryFingerprint);
    const novelRoot = path.join(temporary, 'novels', '原创故事');
    await mkdir(path.join(novelRoot, 'context-packages'), { recursive: true });
    const novel = { ...workspace, id: 'novel-fixture', root: novelRoot, kind: 'novel' as const };
    await writeFile(path.join(novelRoot, 'context-packages/chapter-001.references.yaml'), stringify({ schema_version: 1, chapter: 1, items: [{ analysis_workspace: root, pattern_id: card.id, registry_sha256: details.registryFingerprint, use_for: '本章揭示', adaptation: '调查证据引出新代价', success_check: '选择是否推进目标' }] }));
    assert.equal((await getNovelReferences(novel, [workspace]))[0].matched, true);
    assert.equal((await getNovelReferences(novel, []))[0].sourceTitle, '来源未加入当前书架');
    assert.equal((await getNovelReferences(novel, []))[0].matched, false);
    await writeFile(path.join(root, 'notes/segment-001.md'), '# 用户新编辑的证据');
    assert.equal((await getAnalysisDetails(workspace)).cards[0].usable, false);
    assert.equal((await getNovelReferences(novel, [workspace]))[0].matched, false);
    await writeFile(path.join(root, 'notes/segment-001.md'), evidence);
    source.scope = '第1-60章';
    await writeFile(path.join(root, 'analysis-state.yaml'), stringify(state));
    assert.equal((await getAnalysisDetails(workspace)).cards[0].usable, false);
    assert.equal(await readFile(path.join(root, 'notes/segment-001.md'), 'utf8'), evidence);
  } finally {
    assert.equal(path.dirname(temporary), os.tmpdir());
    assert.ok(path.basename(temporary).startsWith('ani-reader-analysis-'));
    await rm(temporary, { recursive: true, force: true });
  }
});
