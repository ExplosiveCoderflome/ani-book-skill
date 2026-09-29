import { BookOpen, Search, Sun, Moon, RefreshCw, ArrowUpRight } from 'lucide-react';
import { Link, useRevalidator } from 'react-router';
import { useSearchContext } from 'fumadocs-ui/contexts/search';
import { useTheme } from 'fumadocs-ui/provider/base';
import { useEffect } from 'react';

export function Brand() { return <span className="brand"><BookOpen size={22} strokeWidth={1.6} /><span>ANI<span className="brand-label">阅读台</span></span></span>; }

export function SearchButton() {
  const { setOpenSearch } = useSearchContext();
  return <button className="search-button" onClick={() => setOpenSearch(true)}><Search size={16} /><span>搜索资料</span><kbd>⌘ K</kbd></button>;
}

export function ThemeButton() {
  const { resolvedTheme, setTheme } = useTheme();
  return <button className="icon-button" aria-label="切换明暗主题" title="切换明暗主题" onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}><Sun size={18} className="dark:hidden" /><Moon size={18} className="hidden dark:block" /></button>;
}

export function LiveRefresh({ compact = false }: { compact?: boolean }) {
  const revalidator = useRevalidator();
  useEffect(() => {
    const timer = setInterval(() => {
      if (document.visibilityState === 'visible' && revalidator.state === 'idle') void revalidator.revalidate();
    }, 8000);
    return () => clearInterval(timer);
  }, [revalidator]);
  return <button className={compact ? 'icon-button' : 'refresh-button'} aria-label="刷新资料" title="自动检查更新，也可手动刷新" disabled={revalidator.state !== 'idle'} onClick={() => void revalidator.revalidate()}><RefreshCw size={15} className={revalidator.state !== 'idle' ? 'spinning' : ''} />{!compact && <span>刷新资料</span>}</button>;
}

export function LibraryHeader() {
  return <header className="library-header"><Link to="/" aria-label="返回书架"><Brand /></Link><div className="header-actions"><SearchButton /><LiveRefresh compact /><ThemeButton /></div></header>;
}

export function StatusBadge({ status }: { status?: string }) {
  const labels: Record<string, string> = { ready: '已就绪', in_progress: '进行中', stale: '待更新', blocked: '待处理', missing: '缺失', changed: '文件已有修改' };
  if (!status) return null;
  return <span className={`status-badge status-${status in labels ? status : 'unknown'}`}>{labels[status] ?? status}</span>;
}

export function DocumentLink({ href, title, detail }: { href: string; title: string; detail?: string }) {
  return <Link className="document-link" to={href}><span><strong>{title}</strong>{detail && <small>{detail}</small>}</span><ArrowUpRight size={16} /></Link>;
}
