import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { localMd, type MarkdownRendererSerializedOptions } from '@fumadocs/local-md';
import { createSearchAPI, type SearchAPI } from 'fumadocs-core/search/server';
import { z } from 'zod';
import { safeFile, resolveContentLink, documentUrl, getCatalog, type Workspace, type DocumentInfo } from './workspaces.server';

const cache = new Map<string, { fingerprint: string; render: MarkdownRendererSerializedOptions }>();
const searches = new Map<string, { revision: string; server: SearchAPI }>();

export async function loadDocument(workspace: Workspace, document: DocumentInfo) {
  const absolute = await safeFile(workspace.root, document.path);
  const key = `${workspace.id}:${document.path}`;
  const fingerprint = `${document.fingerprint}:${workspace.revision}`;
  const cached = cache.get(key);
  if (cached?.fingerprint === fingerprint) return cached.render;
  // Use the library's Markdown path (AST), never compile workspace content as MDX.
  const source = localMd({
    dir: path.dirname(absolute),
    include: [path.basename(absolute).replace(/([*?{}()[\]!])/g, '\\$1')],
    frontmatterSchema: z.record(z.string(), z.unknown()),
    mdOptions: {
      remarkNpmOptions: false,
      remarkCodeTabOptions: false,
      rehypeCodeOptions: false,
      rehypePlugins: [() => (tree: { children?: unknown[] }) => {
        function visit(node: unknown) {
          if (!node || typeof node !== 'object') return;
          const item = node as { tagName?: string; properties?: Record<string, unknown>; children?: unknown[] };
          if (item.properties && item.tagName === 'a' && typeof item.properties.href === 'string') {
            item.properties.href = resolveContentLink(workspace, document.path, item.properties.href);
          }
          if (item.properties && item.tagName === 'img' && typeof item.properties.src === 'string') {
            // Remote images are shown as links rather than fetched while reading private work.
            const src = item.properties.src;
            if (/^(?:https?:)?\/\//i.test(src)) {
              Object.assign(item, { tagName: 'a', properties: { href: src.startsWith('//') ? `https:${src}` : src, target: '_blank', rel: 'noreferrer' }, children: [{ type: 'text', value: `图片：${String(item.properties.alt ?? src)}` }] });
            } else item.properties.src = resolveContentLink(workspace, document.path, src);
          }
          item.children?.forEach(visit);
        }
        visit(tree);
      }],
    },
  });
  const file = (await source.staticSource()).files.find(file => file.type === 'page');
  if (!file || file.type !== 'page') throw new Error('Markdown 暂时无法解析，请查看原文件。');
  const render = (await file.data.load()).serialize();
  if (render.type !== 'ast') throw new Error('只支持纯 Markdown 文件');
  cache.delete(key);
  cache.set(key, { fingerprint, render });
  // ponytail: keep at most 64 rendered files; add a byte budget if large single files become common.
  if (cache.size > 64) cache.delete(cache.keys().next().value!);
  return render;
}

export async function searchWorkspace(request: Request) {
  const url = new URL(request.url);
  const query = url.searchParams.get('query')?.trim();
  if (!query) return Response.json([]);
  if (query.length > 200) return Response.json({ error: '搜索词过长' }, { status: 400 });
  const catalog = await getCatalog();
  const tag = url.searchParams.get('tag');
  const selected = tag ? catalog.workspaces.filter(workspace => workspace.id === tag) : catalog.workspaces;
  if (tag && selected.length === 0) return Response.json([]);
  const revision = selected.map(workspace => workspace.revision).join(':');
  const key = tag ?? 'all';
  let cached = searches.get(key);
  if (cached?.revision !== revision) {
    const indexes = [];
    for (const workspace of selected) for (const document of workspace.documents) {
      const content = await readFile(await safeFile(workspace.root, document.path), 'utf8');
      indexes.push({ title: document.title, description: `${workspace.title} · ${document.group}`, content,
        breadcrumbs: [workspace.title, document.group], url: documentUrl(workspace.id, document.path) });
    }
    cached = { revision, server: createSearchAPI('simple', { indexes }) };
    searches.delete(key);
    searches.set(key, cached);
    if (searches.size > 4) searches.delete(searches.keys().next().value!);
  }
  // Filter is already applied before indexing; simple search does not support advanced tag fields.
  url.searchParams.delete('tag');
  return cached.server.GET(new Request(url, request));
}
