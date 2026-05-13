// Cloudflare Worker proxy for the Anthropic Claude API.

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

const json = (status, data) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { 'content-type': 'application/json', ...CORS },
  });

export default {
  async fetch(request, env) {
    const { pathname } = new URL(request.url);

    if (pathname !== '/api/claude') {
      return json(404, { error: { message: 'Not found' } });
    }

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS });
    }

    if (request.method !== 'POST') {
      return json(405, { error: { message: 'Method not allowed' } });
    }

    try {
      const body = await request.json();
      const { apiKey, model, max_tokens, system, messages } = body ?? {};

      const key = (apiKey && apiKey.trim()) || env.ANTHROPIC_API_KEY;
      if (!key) {
        return json(400, { error: { message: 'No API key configured' } });
      }

      const upstream = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'x-api-key': key,
          'anthropic-version': '2023-06-01',
          'content-type': 'application/json',
        },
        body: JSON.stringify({ model, max_tokens, system, messages }),
      });

      const payload = await upstream.text();
      return new Response(payload, {
        status: upstream.status,
        headers: { 'content-type': 'application/json', ...CORS },
      });
    } catch (err) {
      return json(500, { error: { message: err?.message || 'Worker error' } });
    }
  },
};
