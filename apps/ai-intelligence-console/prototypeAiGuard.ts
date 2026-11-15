import type { RequestHandler } from 'express';

/** Public prototype inference has no accepted identity, tenant or cost boundary.
 * Keep it closed; a provider key or a budget acknowledgement is not permission.
 * The separately protected Devobs diagnostics proxy owns its own authorization.
 */
export const prototypeAiGuard: RequestHandler = (req, res, next) => {
  // Match Express's default case-insensitive/non-strict route behavior too:
  // https://expressjs.com/en/5x/api.html#app.settings.table
  const path = req.path.toLowerCase().replace(/\/+$/, '');
  const prototype = (path === '/api/ai' || path.startsWith('/api/ai/'))
    && path !== '/api/ai/analyze-incident';
  if (!prototype && !['/api/github/generate-release-notes', '/api/github/generate-pr-summary'].includes(path)) {
    next();
    return;
  }
  res.set({ 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' });
  res.status(503).json({
    code: 'prototype_ai_disabled',
    error: 'ميزات الذكاء الاصطناعي التجريبية غير مفعّلة.',
  });
};
