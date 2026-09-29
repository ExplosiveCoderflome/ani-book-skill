import { Links, Meta, Outlet, Scripts, ScrollRestoration, isRouteErrorResponse, useRouteError, Link, useLocation, useMatches } from 'react-router';
import { RootProvider } from 'fumadocs-ui/provider/react-router';
import type { ReactNode } from 'react';
import './app.css';

export const meta = () => [{ title: 'ANI · 本地阅读台' }, { name: 'description', content: '阅读本地拆书资料与小说工件' }];

export function Layout({ children }: { children: ReactNode }) {
  const location = useLocation();
  const workspaceId = /^\/workspaces\/([^/]+)/.exec(location.pathname)?.[1];
  const matches = useMatches();
  const page = matches.at(-1)?.data as { workspace?: { revision: string }; workspaces?: { revision: string }[] } | undefined;
  const revision = page?.workspace?.revision ?? page?.workspaces?.map(workspace => workspace.revision).join('-') ?? '';
  const searchApi = `/api/search?revision=${encodeURIComponent(revision)}`;
  return <html lang="zh-CN" suppressHydrationWarning>
    <head><meta charSet="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" /><link rel="icon" type="image/svg+xml" href="/favicon.svg" /><Meta /><Links /></head>
    <body><RootProvider
      theme={{ defaultTheme: 'light', hotKey: false }}
      i18n={{ locale: 'zh', translations: {
        'Search(search trigger)': '搜索资料', 'Search(search dialog)': '搜索资料',
        'Open Search(search trigger)(aria-label)': '打开搜索', 'Close Search(search dialog)(aria-label)': '关闭搜索',
        'No results found(search dialog)': '没有找到相关资料', 'On this page(table of contents)': '本页目录',
        'No Headings(table of contents)': '暂无标题', 'Table of Contents(inline table of contents)': '本页目录',
        'Toggle Theme(theme switcher)(aria-label)': '切换明暗主题', 'Light(theme switcher)(aria-label)': '浅色',
        'Dark(theme switcher)(aria-label)': '深色', 'System(theme switcher)(aria-label)': '跟随系统',
        'Collapse Sidebar(sidebar)(aria-label)': '收起目录', 'Open Sidebar(sidebar)(aria-label)': '展开目录',
        'Close Sidebar(sidebar)(aria-label)': '关闭目录', 'Close Sidebar(aria-label)': '关闭目录',
        'Show Sidebar(sidebar)': '展开目录', 'Hide Sidebar(sidebar)': '隐藏目录',
        'Toggle Menu(mobile menu)(aria-label)': '展开菜单',
        'Copy Anchor Link(heading anchor)(aria-label)': '复制标题链接',
        'Copied Anchor Link(heading anchor)(aria-label)': '已复制标题链接',
        'Copy Text(code block)(aria-label)': '复制代码', 'Copied Text(code block)(aria-label)': '已复制代码',
        'Next Page(pagination)': '下一页', 'Previous Page(pagination)': '上一页',
      } }}
      search={{ options: { api: searchApi, defaultTag: workspaceId } }}
    >{children}</RootProvider><ScrollRestoration /><Scripts /></body>
  </html>;
}

export default function App() { return <Outlet />; }

export function ErrorBoundary() {
  const error = useRouteError();
  const missing = isRouteErrorResponse(error) && error.status === 404;
  return <main className="error-page"><span className="eyebrow">ANI / READER</span><h1>{missing ? '这份资料暂时找不到了' : '这份资料暂时无法打开'}</h1><p>{missing ? '文件可能已经移动或删除，可以回到书架重新选择。' : '请检查工作区是否可读，然后刷新页面重试。'}</p><Link className="primary-link" to="/">返回书架</Link></main>;
}
