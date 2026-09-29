import { index, route, type RouteConfig } from '@react-router/dev/routes';

export default [
  index('routes/home.tsx'),
  route('workspaces/:id/*', 'routes/workspace.tsx'),
  route('api/search', 'routes/search.ts'),
  route('assets/:id/*', 'routes/asset.ts'),
] satisfies RouteConfig;
