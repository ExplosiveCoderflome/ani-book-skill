export type WorkspaceKind = 'novel' | 'analysis';
export interface DocumentInfo {
  path: string;
  title: string;
  group: string;
  updatedAt: string;
  size: number;
  fingerprint: string;
  status?: string;
  approval?: string;
  protected?: boolean;
}
export interface Workspace {
  id: string;
  title: string;
  kind: WorkspaceKind;
  root: string;
  documents: DocumentInfo[];
  revision: string;
  updatedAt: string;
  warnings: string[];
  nextAction?: string;
  stage?: string;
}
export interface Catalog { workspaces: Workspace[]; warnings: string[]; roots: string[] }

export function documentUrl(id: string, relative: string): string {
  return `/workspaces/${id}/${relative.split('/').map(encodeURIComponent).join('/')}`;
}
