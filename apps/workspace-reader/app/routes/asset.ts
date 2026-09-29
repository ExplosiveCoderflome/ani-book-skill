import { readFile } from 'node:fs/promises';
import path from 'node:path';
import type { LoaderFunctionArgs } from 'react-router';
import { findWorkspace, safeFile } from '../lib/workspaces.server';

const mime: Record<string, string> = { '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.gif': 'image/gif', '.md': 'text/plain; charset=utf-8', '.txt': 'text/plain; charset=utf-8' };

export async function loader({ params }: LoaderFunctionArgs) {
  const workspace = await findWorkspace(params.id!);
  const relative = params['*'] ?? '';
  const type = mime[path.extname(relative).toLowerCase()];
  if (!type) throw new Response('此文件类型不支持在线查看', { status: 404 });
  try {
    const content = await readFile(await safeFile(workspace.root, relative));
    return new Response(new Uint8Array(content), { headers: { 'Content-Type': type, 'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'no-store', 'Content-Security-Policy': "default-src 'none'; sandbox" } });
  } catch { throw new Response('文件不存在或超出工作区', { status: 404 }); }
}
