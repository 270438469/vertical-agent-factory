import assert from "node:assert/strict";
import test from "node:test";

async function render(path = "/") {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(new Request(`http://localhost${path}`, { headers: { accept: "text/html" } }), {
    ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) },
  }, { waitUntil() {}, passThroughOnException() {} });
}

test("renders the agent factory explainer", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);
  const html = await response.text();
  assert.match(html, /Vertical Agent Factory/);
  assert.match(html, /把 Agent 系统/);
  assert.match(html, /60\/60/);
  assert.match(html, /Agent → Skill → Capability → Binding → Tool/);
  assert.match(html, /运行这个场景/);
  assert.doesNotMatch(html, /codex-preview|react-loading-skeleton|Your site is taking shape/i);
});

test("ships essential accessible controls", async () => {
  const html = await (await render()).text();
  assert.match(html, /aria-label="Agent 执行链"/);
  assert.match(html, /aria-label="运行场景"/);
  assert.match(html, /aria-live="polite"/);
  assert.match(html, /<button/);
});

test("renders the no-code agent setup wizard", async () => {
  const response = await render("/setup");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /不写代码/);
  assert.match(html, /配置 Agent/);
  assert.match(html, /客户 \/ 项目标识/);
  assert.match(html, /NO-CODE AGENT SETUP/);
  assert.match(html, /SETUP PROGRESS/);
  assert.doesNotMatch(html, /OPENAI_API_KEY=[^<&\s]+/);
});

test("renders the finance agent research lab", async () => {
  const response = await render("/finance");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /EVIDENCE-FIRST FINANCE AGENT/);
  assert.match(html, /金融宏观/);
  assert.match(html, /A 股/);
  assert.match(html, /美股/);
  assert.match(html, /微信公众号/);
  assert.match(html, /不替你下注/);
  assert.match(html, /不构成投资建议/);
});
