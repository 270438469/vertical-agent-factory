"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type PipelineStep = {
  id: string;
  index: string;
  title: string;
  role: string;
  detail: string;
  contract: string;
};

type Scenario = {
  label: string;
  task: string;
  input: string;
  terminal: "SUCCESS" | "INSUFFICIENT_EVIDENCE" | "ERROR" | "APPROVAL_REQUIRED";
  summary: string;
  events: string[];
};

const pipeline: PipelineStep[] = [
  { id: "domain", index: "01", title: "Domain", role: "定义边界", detail: "声明领域范围、实体、任务类型与自治边界。它决定系统能处理什么，也明确拒绝什么。", contract: "domains/<id>/domain.yaml" },
  { id: "agent", index: "02", title: "Agent", role: "选择负责人", detail: "Agent 只声明允许的任务、Skills、Capabilities 和运行预算，不直接绑定任何厂商工具。", contract: "agents/<id>/agent.yaml" },
  { id: "skill", index: "03", title: "Skill", role: "描述怎么做", detail: "Skill 负责可复用的过程、输入输出、验证与失败处理，并且只依赖语义 Capability。", contract: "skills/<id>/<skill>/skill.yaml" },
  { id: "capability", index: "04", title: "Capability", role: "表达需要什么", detail: "稳定的业务语义层。更换数据源或工具时，Agent 与 Skill 不需要修改。", contract: "capabilities/<id>.yaml" },
  { id: "policy", index: "05", title: "Policy", role: "决定是否允许", detail: "所有调用先经过确定性策略。读操作可自动执行，高风险写操作进入审批，禁止项直接失败。", contract: "policies/<id>/*.yaml" },
  { id: "binding", index: "06", title: "Binding", role: "解析实现", detail: "Resolver 从健康 Provider 中按优先级选择实现。Binding 可替换，但不泄漏到业务层。", contract: "mcp/bindings/<id>.yaml" },
  { id: "tool", index: "07", title: "Tool", role: "执行动作", detail: "本地 Handler 或 MCP Tool 接收结构化参数，返回可验证结果。失败会进入 Workflow 的失败路径。", contract: "vertical_agent_factory/providers.py" },
  { id: "trace", index: "08", title: "Trace", role: "留下证据", detail: "每次选择、策略判断、工具调用和状态迁移都写入 JSONL，支持审计、Replay 与回归。", contract: ".runs/<run-id>.jsonl" },
];

const scenarios: Record<string, Scenario> = {
  success: {
    label: "证据查询",
    task: "research.answer.query",
    input: 'query="shared Harness"',
    terminal: "SUCCESS",
    summary: "找到 1 条证据，生成结构化答案并通过证据校验。",
    events: ["run.started", "skill.selected", "policy.allowed", "capability.resolved", "tool.completed", "workflow.transitioned", "validation.completed", "run.completed"],
  },
  empty: {
    label: "无足够证据",
    task: "research.answer.query",
    input: 'query="latest market price"',
    terminal: "INSUFFICIENT_EVIDENCE",
    summary: "检索没有命中，系统明确保留答案，而不是编造事实。",
    events: ["run.started", "skill.selected", "policy.allowed", "capability.resolved", "tool.completed", "workflow.transitioned", "validation.completed", "run.completed"],
  },
  failure: {
    label: "Provider 故障",
    task: "research.answer.query",
    input: "simulate_failure=true",
    terminal: "ERROR",
    summary: "Provider 故障被捕获，Workflow 进入 FAILED，Trace 保留错误类型。",
    events: ["run.started", "skill.selected", "policy.allowed", "capability.resolved", "tool.started", "workflow.transitioned", "run.failed"],
  },
  approval: {
    label: "审批拦截",
    task: "research.report.publish",
    input: 'target="demo"',
    terminal: "APPROVAL_REQUIRED",
    summary: "高风险写操作在调用 Tool 前停止，等待明确审批。",
    events: ["run.started", "skill.selected", "approval.requested", "workflow.transitioned", "run.failed"],
  },
  approved: {
    label: "已批准写入",
    task: "research.report.publish",
    input: 'target="demo" + approval',
    terminal: "SUCCESS",
    summary: "审批令牌通过后才执行发布 Provider；演示实现不会修改外部系统。",
    events: ["run.started", "skill.selected", "policy.allowed", "capability.resolved", "tool.started", "tool.completed", "run.completed"],
  },
};

const buildSteps = [
  ["界定领域", "先写 domain.yaml：目标、范围、用户、自治与风险。不要从 System Prompt 开始。"],
  ["建立业务语言", "用 ontology.yaml 定义实体与关系；避免 SalesforceAccount 这类厂商对象名。"],
  ["拆解任务", "为每类任务声明证据、Capability、风险、完成条件和对应 Workflow。"],
  ["封装执行", "Skill 只依赖 Capability；Binding 再把 Capability 映射到本地 Handler 或 MCP Tool。"],
  ["先写护栏", "对 READ、WRITE、DESTRUCTIVE、PRIVILEGED 分层决策；低层只能收紧。"],
  ["用失败证明设计", "至少覆盖 Happy、Edge、Ambiguous、Tool Failure、Policy、Adversarial 六类 Eval。"],
];

const tests = [
  ["Package validation", "PASS", "引用、版本、Schema、Workflow 与高风险 Policy"],
  ["Runtime tests", "14 / 14", "查询、无证据、审批、漂移、Provider、CLI 与 Trace"],
  ["Golden evals", "30 / 30", "6 类真实边界，每类 5 个用例"],
  ["Skill validation", "VALID", "Codex frontmatter 与 UI metadata"],
  ["Build + HTML", "PASS", "生产构建、服务端渲染与无障碍语义"],
];

export default function Home() {
  const [selectedStep, setSelectedStep] = useState(0);
  const [scenarioKey, setScenarioKey] = useState("success");
  const [eventIndex, setEventIndex] = useState(-1);
  const [running, setRunning] = useState(false);
  const [copied, setCopied] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const scenario = scenarios[scenarioKey];
  const step = pipeline[selectedStep];

  const progress = useMemo(() => {
    if (eventIndex < 0) return 0;
    return Math.round(((eventIndex + 1) / scenario.events.length) * 100);
  }, [eventIndex, scenario.events.length]);

  useEffect(() => () => { if (timer.current) clearInterval(timer.current); }, []);

  function selectScenario(key: string) {
    if (timer.current) clearInterval(timer.current);
    setScenarioKey(key);
    setEventIndex(-1);
    setRunning(false);
  }

  function runTrace() {
    if (timer.current) clearInterval(timer.current);
    setRunning(true);
    setEventIndex(0);
    let next = 0;
    timer.current = setInterval(() => {
      next += 1;
      if (next >= scenario.events.length) {
        if (timer.current) clearInterval(timer.current);
        setRunning(false);
        return;
      }
      setEventIndex(next);
    }, 420);
  }

  async function copyCommand() {
    await navigator.clipboard.writeText("python -m vertical_agent_factory.cli --root . run --domain research --task research.answer.query --input \"query=shared Harness\"");
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }

  return (
    <main>
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Vertical Agent Factory 首页"><span>VAF</span><b>Vertical Agent Factory</b></a>
        <nav aria-label="页面导航">
          <a href="/setup">配置中心</a><a href="#runtime">运行链</a><a href="#build">搭建</a><a href="#tests">自测试</a>
        </nav>
        <a className="repo-link" href="https://github.com/270438469/vertical-agent-factory" target="_blank" rel="noreferrer">GitHub ↗</a>
      </header>

      <section className="hero" id="top">
        <div className="hero-kicker"><span className="pulse" /> Shared Harness · Domain Package · Evidence First</div>
        <h1>把 Agent 系统<br /><em>拆开给你看。</em></h1>
        <p className="hero-copy">一套可运行、可审计、可替换 Provider 的垂直 Agent 工厂。这里不是架构幻灯片——每个节点都对应仓库里的真实契约。</p>
        <div className="hero-actions">
          <a className="button primary" href="/setup">无代码配置 Agent <span>→</span></a>
          <button className="button ghost" onClick={copyCommand}>{copied ? "已复制命令 ✓" : "复制快速运行命令"}</button>
        </div>
        <div className="score-strip" aria-label="系统验证摘要">
          <div><strong>30/30</strong><span>Golden Evals</span></div>
          <div><strong>14/14</strong><span>Runtime Tests</span></div>
          <div><strong>0</strong><span>Policy Violations</span></div>
          <div><strong>8</strong><span>Traceable Layers</span></div>
        </div>
      </section>

      <section className="runtime-section" id="runtime">
        <div className="section-heading">
          <div><span className="section-no">01</span><p className="eyebrow">LIVE EXECUTION MAP</p><h2>一次请求，经过哪些层？</h2></div>
          <p>点击任意节点查看职责。右侧选择场景并运行，观察策略、Provider 与 Workflow 如何改变终态。</p>
        </div>

        <div className="runtime-grid">
          <div className="pipeline-panel">
            <div className="pipeline" aria-label="Agent 执行链">
              {pipeline.map((item, index) => (
                <button key={item.id} className={`pipeline-node ${selectedStep === index ? "active" : ""}`} onClick={() => setSelectedStep(index)} aria-pressed={selectedStep === index}>
                  <span className="node-index">{item.index}</span><span className="node-title">{item.title}</span><span className="node-role">{item.role}</span><span className="node-arrow">→</span>
                </button>
              ))}
            </div>
            <article className="node-detail" aria-live="polite">
              <div><span>{step.index} / ARCHITECTURE CONTRACT</span><h3>{step.title}</h3></div>
              <p>{step.detail}</p><code>{step.contract}</code>
            </article>
            <div className="invariant"><span>核心不变量</span><strong>Agent → Skill → Capability → Binding → Tool</strong><small>禁止 Agent 直连厂商工具；禁止 Skill 接触 Secret；禁止模型绕过 Policy。</small></div>
          </div>

          <aside className="trace-lab" aria-label="Trace 运行实验室">
            <div className="lab-head"><div><span className="terminal-dot" /> TRACE LAB</div><span>{progress}%</span></div>
            <div className="scenario-tabs" role="tablist" aria-label="运行场景">
              {Object.entries(scenarios).map(([key, value]) => <button key={key} role="tab" aria-selected={scenarioKey === key} onClick={() => selectScenario(key)}>{value.label}</button>)}
            </div>
            <div className="request-card"><span>TASK</span><code>{scenario.task}</code><span>INPUT</span><code>{scenario.input}</code></div>
            <div className="event-log" aria-live="polite">
              {scenario.events.map((event, index) => {
                const state = index < eventIndex ? "done" : index === eventIndex ? "current" : "idle";
                return <div className={`event ${state}`} key={`${scenarioKey}-${event}-${index}`}><span>{String(index + 1).padStart(2, "0")}</span><i /><code>{event}</code><b>{state === "done" ? "✓" : state === "current" ? "●" : "·"}</b></div>;
              })}
            </div>
            <button className="run-button" onClick={runTrace} disabled={running}>{running ? "正在执行…" : eventIndex >= scenario.events.length - 1 ? "重新运行 Trace" : "运行这个场景"}<span>▶</span></button>
            {eventIndex >= scenario.events.length - 1 && <div className={`terminal-result result-${scenario.terminal.toLowerCase()}`}><span>TERMINAL</span><strong>{scenario.terminal}</strong><p>{scenario.summary}</p></div>}
          </aside>
        </div>
      </section>

      <section className="build-section" id="build">
        <div className="section-heading light">
          <div><span className="section-no">02</span><p className="eyebrow">PACKAGE BLUEPRINT</p><h2>从零搭建一个 Domain Pack</h2></div>
          <p>共享 Harness 只维护一套。新增垂直领域时，安装业务资产，不复制 Runtime。</p>
        </div>
        <div className="build-layout">
          <div className="file-tree" aria-label="标准目录结构">
            <div className="tree-title"><span>research/</span><b>v1.0.0</b></div>
            <pre>{`domains/research/
├─ domain.yaml
├─ ontology.yaml
├─ task-taxonomy.yaml
├─ knowledge.yaml
├─ schemas/
└─ workflows/

agents/research/
skills/research/
capabilities/research.yaml
mcp/bindings/research.yaml
policies/research/
evals/research/`}</pre>
            <div className="tree-footer"><span>✓</span> Capability / Tool 已解耦</div>
          </div>
          <ol className="build-steps">
            {buildSteps.map(([title, text], index) => <li key={title}><span>{String(index + 1).padStart(2, "0")}</span><div><h3>{title}</h3><p>{text}</p></div></li>)}
          </ol>
        </div>
      </section>

      <section className="tests-section" id="tests">
        <div className="section-heading">
          <div><span className="section-no">03</span><p className="eyebrow">SYSTEM SELF-TEST</p><h2>不是“能跑”，是可证明。</h2></div>
          <p>测试覆盖成功路径，也刻意验证无证据、Provider 故障、审批门与对抗输入。</p>
        </div>
        <div className="test-board">
          <div className="test-summary"><span>RELEASE GATE</span><strong>PASS</strong><p>所有关键契约、运行时与边界用例均通过。</p><div className="ring"><span>100<small>%</small></span></div></div>
          <div className="test-list">
            {tests.map(([name, score, scope]) => <div className="test-row" key={name}><span className="check">✓</span><div><h3>{name}</h3><p>{scope}</p></div><strong>{score}</strong></div>)}
          </div>
        </div>
        <div className="eval-grid">
          {[["Happy Path","5/5"],["Edge Case","5/5"],["Ambiguous","5/5"],["Tool Failure","5/5"],["Policy Boundary","5/5"],["Adversarial","5/5"]].map(([name, score]) => <div key={name}><span>{name}</span><strong>{score}</strong><i /></div>)}
        </div>
      </section>

      <section className="cta">
        <p className="eyebrow">READY TO EXTEND</p><h2>换领域，不换 Harness。</h2><p>复制 `research` 的契约结构，替换业务本体、Skills 与 Bindings，再让 30 个边界用例证明它。</p>
        <div><a className="button primary dark" href="https://github.com/270438469/vertical-agent-factory" target="_blank" rel="noreferrer">查看 GitHub 仓库 ↗</a><button className="button ghost dark" onClick={copyCommand}>{copied ? "已复制 ✓" : "复制 CLI 示例"}</button></div>
      </section>

      <footer><div className="brand"><span>VAF</span><b>Vertical Agent Factory</b></div><p>Shared Harness + Domain Package</p><p>Built for evidence, policy and replay.</p></footer>
    </main>
  );
}
