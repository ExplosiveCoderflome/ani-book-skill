import type { LoaderFunctionArgs } from 'react-router';
import { searchWorkspace } from '../lib/content.server';

export async function loader({ request }: LoaderFunctionArgs) {
  const url = new URL(request.url);
  const workspace = url.searchParams.get('workspace');
  if (workspace) url.searchParams.set('tag', workspace);
  return searchWorkspace(new Request(url, request));
}
