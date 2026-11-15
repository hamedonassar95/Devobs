/** Resolve only the public snapshot in the free profile; never a backend API. */
export function dashboardRequestUrl(path, { staticDemo = false, moduleUrl } = {}) {
  if (!staticDemo) return path;
  if (path !== '/api/v1/intelligence') throw new Error('static_demo_api_disabled');
  return new URL('./snapshot.json', moduleUrl).href;
}
