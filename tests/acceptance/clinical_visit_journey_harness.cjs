// Shared request lifecycle for CW-B24 and the observed CW-B10 popup teardown race.
const assert = require('node:assert/strict');

async function trackBrowser(context, {origins, errors, external}) {
  assert(origins.every(value => ['127.0.0.1', 'localhost', '[::1]'].includes(new URL(value).hostname)));
  const handlers = new Set(), requests = new Set();
  let completed = 0;
  context.on('request', request => requests.add(request));
  const finished = request => requests.delete(request);
  context.on('requestfinished', finished);
  context.on('requestfailed', finished);
  context.on('page', page => page.on('pageerror', error => errors.push(error.message)));
  await context.route('**/*', route => {
    const job = (async () => {
      try {
        if (origins.includes(new URL(route.request().url()).origin)) await route.continue();
        else { external.push(route.request().url()); await route.abort('blockedbyclient'); }
        completed++;
      } catch (error) {
        // Catch the asynchronous rejection so evidence is written, but fail the gate.
        errors.push('route lifecycle: ' + error.message);
      }
    })();
    handlers.add(job);
    return job.finally(() => handlers.delete(job));
  });
  async function drain(page) {
    const deadline = Date.now() + 10000;
    while (handlers.size || [...requests].some(r => !page || r.frame().page() === page)) {
      assert(Date.now() < deadline, 'Browser requests did not settle before close');
      await Promise.all([...handlers]);
      await new Promise(resolve => setTimeout(resolve, 20));
    }
  }
  return {
    drain,
    async closePage(page) { await drain(page); await page.unrouteAll({behavior:'wait'}); await page.close(); },
    async close() { await drain(); await context.unrouteAll({behavior:'wait'}); await context.close(); },
    receipt() { return {completed, pending_handlers:handlers.size, pending_requests:requests.size}; },
  };
}

module.exports = {trackBrowser};
