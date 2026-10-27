import { test, beforeEach } from 'node:test';
import assert from 'node:assert/strict';

globalThis.document = {
  cookie: 'otra=1; csrftoken=tok%2D123; ultima=2',
  getElementById: () => ({ textContent: JSON.stringify({ apiBase: '/api/v1/', csrfCookie: 'csrftoken' }) }),
};
globalThis.location = new URL('http://localhost:8000/');
const { apiGet, apiSend, ApiError } = await import('../../frontend/static/scripts/data/api-client.js');

function reply(status, body, { redirected = false, type = 'application/json' } = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    redirected,
    headers: { get: () => type },
    json: async () => {
      if (body === undefined) throw new SyntaxError('sin JSON');
      return body;
    },
  };
}

let calls;
function serve(response) {
  calls = [];
  globalThis.fetch = async (url, init) => {
    calls.push({ url: String(url), init });
    return typeof response === 'function' ? response(url, init) : response;
  };
}

beforeEach(() => serve(reply(200, { data: {} })));

test('GET uses the configured base, skips empty params and sends no CSRF', async () => {
  await apiGet('screens/eva4', { mes: '2026-10', servicio: '', cuenta: null, pagina: 0 });
  const { url, init } = calls[0];
  assert.equal(url, 'http://localhost:8000/api/v1/screens/eva4?mes=2026-10&pagina=0');
  assert.equal(init.method, 'GET');
  assert.equal(init.credentials, 'same-origin');
  assert.equal(init.headers['X-CSRFToken'], undefined);
  assert.equal(init.body, undefined);
});

test('writes send JSON with the CSRF token', async () => {
  await apiSend('PATCH', 'agreements/7', { status: 'done' });
  const { init } = calls[0];
  assert.equal(init.method, 'PATCH');
  assert.equal(init.headers['X-CSRFToken'], 'tok-123');
  assert.equal(init.headers['Content-Type'], 'application/json');
  assert.equal(init.body, '{"status":"done"}');
});

test('returns the whole envelope', async () => {
  serve(reply(200, { data: { n: 1 }, meta: { generated_at: 'ahora' } }));
  assert.deepEqual(await apiGet('x/'), { data: { n: 1 }, meta: { generated_at: 'ahora' } });
});

for (const [status, code] of [[401, 'unauthenticated'], [403, 'forbidden'], [404, 'not_found']]) {
  test(`${status} becomes ${code} with a readable message`, async () => {
    serve(reply(status, { detail: 'texto tecnico' }));
    await assert.rejects(apiGet('x/'), (error) => {
      assert.ok(error instanceof ApiError);
      assert.equal(error.code, code);
      assert.equal(error.status, status);
      assert.doesNotMatch(error.message, /tecnico/);
      return true;
    });
  });
}

test('a 502 page without JSON becomes a server error', async () => {
  serve(reply(502, undefined, { type: 'text/html' }));
  await assert.rejects(apiGet('x/'), { code: 'server', status: 502 });
});

test('the API error envelope keeps code, message and fields', async () => {
  const fields = { title: ['Obligatorio'] };
  serve(reply(400, { error: { code: 'validation', message: 'Revisa el formulario', fields } }));
  await assert.rejects(apiSend('POST', 'agreements/', {}), (error) => {
    assert.equal(error.code, 'validation');
    assert.equal(error.message, 'Revisa el formulario');
    assert.deepEqual(error.fields, fields);
    return true;
  });
});

test('a DRF detail message is shown when the status is not special', async () => {
  serve(reply(400, { detail: 'Parametro invalido' }));
  await assert.rejects(apiGet('x/'), { code: 'request', message: 'Parametro invalido' });
});

test('a redirect to an HTML page means the session ended', async () => {
  serve(reply(200, undefined, { redirected: true, type: 'text/html' }));
  await assert.rejects(apiGet('x/'), { code: 'unauthenticated', status: 401 });
});

test('a 200 without JSON is an invalid response', async () => {
  serve(reply(200, undefined));
  await assert.rejects(apiGet('x/'), { code: 'invalid_response' });
});

test('a connection failure is reported as network', async () => {
  serve(() => {
    throw new TypeError('fetch failed');
  });
  await assert.rejects(apiGet('x/'), { code: 'network', status: 0 });
});

const hangUntilAborted = (url, init) =>
  new Promise((_, reject) =>
    init.signal.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError'))),
  );

test('a slow request times out', async () => {
  serve(hangUntilAborted);
  await assert.rejects(apiGet('x/', {}, { timeout: 10 }), { code: 'timeout' });
});

test('cancelling from the screen rethrows the abort and shows no error', async () => {
  serve(hangUntilAborted);
  const controller = new AbortController();
  const pending = apiGet('x/', {}, { signal: controller.signal });
  controller.abort();
  await assert.rejects(pending, (error) => {
    assert.equal(error.name, 'AbortError');
    assert.ok(!(error instanceof ApiError));
    return true;
  });
});

test('a missing CSRF cookie sends an empty token instead of failing', async () => {
  const saved = document.cookie;
  document.cookie = 'otra=1';
  await apiSend('POST', 'x/', {});
  document.cookie = saved;
  assert.equal(calls.at(-1).init.headers['X-CSRFToken'], '');
});


test('a status read can bypass cache without changing other requests', async () => {
  await apiGet('ordinary/');
  assert.equal(Object.hasOwn(calls[0].init, 'cache'), false);
  await apiGet('status/', { anio: '2026' }, { cache: 'no-store' });
  assert.equal(calls[1].init.cache, 'no-store');
  assert.equal(new URL(calls[1].url).searchParams.get('anio'), '2026');
});
