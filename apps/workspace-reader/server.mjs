import { createServer } from 'node:http';
import { readFile, realpath, stat } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequestHandler } from 'react-router';

const appRoot = path.dirname(fileURLToPath(import.meta.url));
process.chdir(appRoot);
const clientRoot = await realpath(path.join(appRoot, 'build/client'));
const build = await import('./build/server/index.js');
const handle = createRequestHandler(build, 'production');
const port = Number(process.env.PORT ?? 8790);
const mime = { '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon', '.woff2': 'font/woff2' };

createServer(async (incoming, outgoing) => {
  const host = incoming.headers.host ?? '';
  if (!['127.0.0.1', 'localhost', '[::1]'].includes(host.replace(/:\d+$/, ''))) {
    outgoing.writeHead(403).end('仅支持本机访问'); return;
  }
  if (incoming.method !== 'GET' && incoming.method !== 'HEAD') {
    outgoing.writeHead(405, { Allow: 'GET, HEAD' }).end('阅读台只提供读取'); return;
  }
  outgoing.setHeader('X-Content-Type-Options', 'nosniff');
  outgoing.setHeader('Referrer-Policy', 'no-referrer');
  outgoing.setHeader('Cache-Control', 'no-store');
  outgoing.setHeader('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'");
  try {
    const url = new URL(incoming.url ?? '/', `http://${host}`);
    const relative = decodeURIComponent(url.pathname).slice(1);
    const candidate = path.resolve(clientRoot, relative);
    const offset = path.relative(clientRoot, candidate);
    if (offset && !offset.startsWith('..') && !path.isAbsolute(offset)) {
      try {
        const canonical = await realpath(candidate);
        const resolvedOffset = path.relative(clientRoot, canonical);
        if (!resolvedOffset.startsWith('..') && !path.isAbsolute(resolvedOffset) && (await stat(canonical)).isFile()) {
          const content = await readFile(canonical);
          outgoing.setHeader('Content-Type', mime[path.extname(canonical)] ?? 'application/octet-stream');
          outgoing.end(incoming.method === 'HEAD' ? undefined : content); return;
        }
      } catch (error) { if (error.code !== 'ENOENT' && error.code !== 'ENOTDIR') throw error; }
    }
    const request = new Request(url, { method: incoming.method, headers: incoming.headers });
    const response = await handle(request);
    outgoing.statusCode = response.status;
    response.headers.forEach((value, key) => outgoing.setHeader(key, value));
    if (!response.body || incoming.method === 'HEAD') { outgoing.end(); return; }
    for await (const chunk of response.body) {
      if (!outgoing.write(chunk)) await new Promise(resolve => outgoing.once('drain', resolve));
    }
    outgoing.end();
  } catch (error) {
    console.error('阅读请求失败：', error.message);
    if (!outgoing.headersSent) outgoing.writeHead(500, { 'Content-Type': 'text/plain; charset=utf-8' });
    outgoing.end('读取失败，请检查本地工作区后重试。');
  }
}).listen(port, '127.0.0.1', () => console.log(`ANI 阅读台：http://127.0.0.1:${port}`));
