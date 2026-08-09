"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

type Provider = {
  id: string;
  name: string;
  keyEnv: string;
  models: string[];
  url: string;
  preparation: string;
  baseUrlEnv?: string;
  customModels?: boolean;
};

type ProviderValue = { apiKey: string; baseUrl: string; models: string[] };

const providers: Provider[] = [
  { id: "openai", name: "OpenAI", keyEnv: "OPENAI_API_KEY", models: ["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"], url: "https://platform.openai.com/api-keys", preparation: "API Project、已开通计费的 API Key、模型权限" },
  { id: "anthropic", name: "Anthropic Claude", keyEnv: "ANTHROPIC_API_KEY", models: ["claude-fable-5", "claude-opus-5", "claude-sonnet-5"], url: "https://console.anthropic.com/settings/keys", preparation: "Claude Console 组织、API Key、模型权限" },
  { id: "gemini", name: "Google Gemini", keyEnv: "GEMINI_API_KEY", models: ["gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite"], url: "https://aistudio.google.com/app/apikey", preparation: "Google AI Studio 项目、API Key、项目配额" },
  { id: "qwen", name: "阿里云百炼 / 千问", keyEnv: "DASHSCOPE_API_KEY", baseUrlEnv: "DASHSCOPE_BASE_URL", models: ["qwen3.7-max", "qwen3.7-plus", "qwen3.6-flash"], url: "https://help.aliyun.com/zh/model-studio/get-api-key", preparation: "百炼工作空间、API Key；新工作空间还需地域专属 Base URL" },
  { id: "deepseek", name: "DeepSeek", keyEnv: "DEEPSEEK_API_KEY", models: ["deepseek-v4-pro", "deepseek-v4-flash"], url: "https://platform.deepseek.com/api_keys", preparation: "API Key、账户余额或组织授权" },
  { id: "zhipu", name: "智谱 BigModel / GLM", keyEnv: "ZHIPU_API_KEY", models: ["glm-5.2", "glm-5.1", "glm-5"], url: "https://open.bigmodel.cn/usercenter/apikeys", preparation: "BigModel 账号和 API Key" },
  { id: "moonshot", name: "月之暗面 Kimi", keyEnv: "MOONSHOT_API_KEY", baseUrlEnv: "MOONSHOT_BASE_URL", models: ["kimi-k3", "kimi-k2.6", "kimi-k2.5"], url: "https://platform.kimi.com/docs/api/overview", preparation: "Kimi 开放平台 API Key；国际账号另备 Base URL" },
  { id: "minimax", name: "MiniMax", keyEnv: "MINIMAX_API_KEY", baseUrlEnv: "MINIMAX_BASE_URL", models: ["MiniMax-M3", "MiniMax-M2.7", "MiniMax-M2.7-highspeed"], url: "https://platform.minimaxi.com/docs/api-reference/api-overview", preparation: "MiniMax API Key；国际账号另备 Base URL" },
  { id: "doubao", name: "火山方舟 / 豆包", keyEnv: "ARK_API_KEY", baseUrlEnv: "ARK_BASE_URL", models: ["doubao-seed-evolving", "doubao-seed-2.1-pro", "doubao-seed-2.1-turbo"], url: "https://www.volcengine.com/docs/82379/1330626", preparation: "方舟 API Key；部分账号需创建并复制三档 Endpoint ID", customModels: true },
  { id: "hunyuan", name: "腾讯混元", keyEnv: "HUNYUAN_API_KEY", models: ["hunyuan-a13b", "hunyuan-turbos-latest", "hunyuan-lite"], url: "https://cloud.tencent.com/document/product/1729/111007", preparation: "OpenAI 兼容接口凭证，并确认旧平台仍可用" },
  { id: "qianfan", name: "百度千帆 / 文心", keyEnv: "QIANFAN_API_KEY", models: ["ernie-5.1", "ernie-5.0", "ernie-4.5-turbo-128k"], url: "https://cloud.baidu.com/doc/Qianfan/index.html", preparation: "OpenAI 兼容 API 专用 Key，不是旧接口 AK/SK" },
  { id: "stepfun", name: "阶跃星辰 StepFun", keyEnv: "STEPFUN_API_KEY", models: ["step-3.5-flash", "step-3", "step-2-mini"], url: "https://platform.stepfun.ai/docs", preparation: "开放平台 API Key、所选模型权限" },
  { id: "yi", name: "零一万物 Yi", keyEnv: "YI_API_KEY", models: ["yi-lightning"], url: "https://platform.lingyiwanwu.com/", preparation: "开放平台 API Key；当前通用文本模型只有一档" },
  { id: "baichuan", name: "百川智能", keyEnv: "BAICHUAN_API_KEY", models: ["Baichuan4-Turbo", "Baichuan4", "Baichuan4-Air"], url: "https://platform.baichuan-ai.com/console/authentication", preparation: "完成账号认证并创建 API Key" },
  { id: "spark", name: "讯飞星火 / 星辰", keyEnv: "SPARK_API_KEY", models: ["xsparkx2agent", "xsparkx2", "xsparkx2flash"], url: "https://www.xfyun.cn/doc/spark/TokenPlan.html", preparation: "Token Plan 套餐专属 API Key，不是旧版 API Password" },
  { id: "siliconflow", name: "SiliconFlow 硅基流动", keyEnv: "SILICONFLOW_API_KEY", models: ["replace-with-siliconflow-top1-model-id", "replace-with-siliconflow-top2-model-id", "replace-with-siliconflow-top3-model-id"], url: "https://docs.siliconflow.cn/cn/userguide/quickstart", preparation: "API Key、模型广场中本账号可用的前三个文本模型 ID", customModels: true },
  { id: "sensenova", name: "商汤 SenseNova", keyEnv: "SENSENOVA_API_KEY", models: ["replace-with-sensenova-v6.5-pro-model-id", "replace-with-sensenova-v6.5-turbo-model-id", "replace-with-sensenova-v6-reasoner-model-id"], url: "https://platform.sensenova.cn/product/APIService/document", preparation: "API 凭证、从模型列表取得的三个真实模型 ID", customModels: true },
  { id: "mimo", name: "小米 MiMo", keyEnv: "MIMO_API_KEY", models: ["mimo-v2.5-pro", "mimo-v2.5"], url: "https://mimo.mi.com/docs/zh-CN/quick-start/summary/first-api-call", preparation: "MiMo 平台 API Key；当前通用文本模型只有两档" },
  { id: "longcat", name: "美团 LongCat", keyEnv: "LONGCAT_API_KEY", models: ["LongCat-2.0"], url: "https://longcat.chat/platform/docs/", preparation: "API Key 和可用额度；当前生产文本模型只有一档" },
];

const steps = ["业务用途", "选择厂商", "密钥与模型", "权限与额度", "检查并应用"];
const taskOptions = [
  { id: "research.answer.query", title: "查询并生成答案", note: "只读任务。先检索证据，再生成有依据的答案。" },
  { id: "research.report.publish", title: "发布研究报告", note: "写操作。默认不会自动获批，运行时进入审批门。" },
];

function randomSecret() {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function tenantEnv(tenantId: string) {
  return `VAF_API_KEY_${tenantId.toUpperCase().replace(/[^A-Z0-9]/g, "_")}`;
}

function yamlQuote(value: string) {
  return JSON.stringify(value);
}

export default function SetupPage() {
  const [step, setStep] = useState(0);
  const [tenantId, setTenantId] = useState("demo-customer");
  const [tasks, setTasks] = useState(["research.answer.query"]);
  const [selected, setSelected] = useState<string[]>(["deepseek"]);
  const [values, setValues] = useState<Record<string, ProviderValue>>(() => Object.fromEntries(providers.map((provider) => [provider.id, { apiKey: "", baseUrl: "", models: [...provider.models] }])));
  const [customerKey, setCustomerKey] = useState("");
  const [defaultProvider, setDefaultProvider] = useState("local");
  const [rateLimit, setRateLimit] = useState(60);
  const [monthlyQuota, setMonthlyQuota] = useState(10000);
  const [apiBase, setApiBase] = useState("http://127.0.0.1:8000");
  const [adminKey, setAdminKey] = useState("");
  const [browserOrigin, setBrowserOrigin] = useState("");
  const [result, setResult] = useState<{ kind: "idle" | "working" | "success" | "error"; message: string }>({ kind: "idle", message: "" });
  const [previewYaml, setPreviewYaml] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setCustomerKey(randomSecret());
      setAdminKey(randomSecret());
      setBrowserOrigin(window.location.origin);
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  const chosenProviders = useMemo(() => providers.filter((provider) => selected.includes(provider.id)), [selected]);
  const payload = useMemo(() => ({
    tenant_id: tenantId.trim(),
    customer_api_key: customerKey,
    allowed_tasks: tasks,
    providers: chosenProviders.map((provider) => ({ id: provider.id, api_key: values[provider.id].apiKey, base_url: values[provider.id].baseUrl, models: values[provider.id].models.filter(Boolean) })),
    default_provider: defaultProvider,
    rate_limit_per_minute: rateLimit,
    monthly_request_quota: monthlyQuota,
  }), [tenantId, customerKey, tasks, chosenProviders, values, defaultProvider, rateLimit, monthlyQuota]);

  const localYaml = useMemo(() => {
    const lines = ["project_root: ..", "database_path: .commercial/usage.sqlite3", "providers:"];
    if (!chosenProviders.length) lines.push("  {}");
    chosenProviders.forEach((provider) => {
      lines.push(`  ${provider.id}:`, `    api_key_env: ${provider.keyEnv}`);
      if (provider.baseUrlEnv) lines.push(`    base_url_env: ${provider.baseUrlEnv}`);
    });
    lines.push("tenants:", `  - id: ${yamlQuote(tenantId.trim())}`, `    api_key_env: ${tenantEnv(tenantId.trim())}`, "    allowed_domains:", "      - research", "    allowed_tasks:");
    tasks.forEach((task) => lines.push(`      - ${task}`));
    lines.push("    allowed_providers:", "      - local");
    chosenProviders.forEach((provider) => lines.push(`      - ${provider.id}`));
    lines.push(`    default_provider: ${defaultProvider}`, "    allowed_models:");
    if (!chosenProviders.length) lines.push("      {}");
    chosenProviders.forEach((provider) => {
      lines.push(`      ${provider.id}:`);
      values[provider.id].models.filter(Boolean).forEach((model) => lines.push(`        - ${yamlQuote(model)}`));
    });
    lines.push("    default_models:");
    if (!chosenProviders.length) lines.push("      {}");
    chosenProviders.forEach((provider) => lines.push(`      ${provider.id}: ${yamlQuote(values[provider.id].models.filter(Boolean)[0] || "")}`));
    lines.push("    approved_capabilities: []", `    rate_limit_per_minute: ${rateLimit}`, `    monthly_request_quota: ${monthlyQuota}`);
    return `${lines.join("\n")}\n`;
  }, [tenantId, tasks, chosenProviders, values, defaultProvider, rateLimit, monthlyQuota]);

  function toggleProvider(id: string) {
    setSelected((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
    if (defaultProvider === id) setDefaultProvider("local");
  }

  function updateProvider(id: string, patch: Partial<ProviderValue>) {
    setValues((current) => ({ ...current, [id]: { ...current[id], ...patch } }));
  }

  function updateModel(id: string, index: number, model: string) {
    const models = [...values[id].models];
    models[index] = model;
    updateProvider(id, { models });
  }

  function validateCurrent() {
    if (step === 0 && (!/^[A-Za-z0-9_-]{1,80}$/.test(tenantId) || !tasks.length)) return "请填写合规的客户标识，并至少选择一个任务。";
    if (step === 2) {
      const incomplete = chosenProviders.find((provider) => {
        const models = values[provider.id].models.filter(Boolean);
        return !values[provider.id].apiKey || !models.length || models.some((model) => model.startsWith("replace-with-"));
      });
      if (incomplete) return `请完成 ${incomplete.name} 的 API Key 和真实模型 ID。`;
    }
    if (step === 3 && customerKey.length < 32) return "客户调用密钥至少需要 32 个字符。";
    return "";
  }

  function next() {
    const error = validateCurrent();
    if (error) return setResult({ kind: "error", message: error });
    setResult({ kind: "idle", message: "" });
    setStep((current) => Math.min(steps.length - 1, current + 1));
  }

  async function callSetup(action: "preview" | "apply") {
    if (adminKey.length < 32) return setResult({ kind: "error", message: "请填写启动本地配置服务时使用的管理员密钥。" });
    setResult({ kind: "working", message: action === "preview" ? "后台正在检查并转换配置…" : "后台正在安全写入配置…" });
    try {
      const response = await fetch(`${apiBase.replace(/\/$/, "")}/v1/setup/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${adminKey}` },
        body: JSON.stringify(payload),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body?.error?.messages?.join("；") || body?.error?.message || `请求失败（HTTP ${response.status}）`);
      if (action === "preview") setPreviewYaml(body.yaml);
      setResult({ kind: "success", message: action === "preview" ? "检查通过：后台转换结果与页面预览一致，密钥未被回显。" : `配置已写入 ${body.config_path}，私密值已写入 ${body.environment_path}。现在重启 API 服务即可生效。` });
    } catch (error) {
      setResult({ kind: "error", message: `无法连接或应用：${error instanceof Error ? error.message : "未知错误"}。可先下载配置包，或按下方命令启动本地配置服务。` });
    }
  }

  function download(name: string, content: string) {
    const url = URL.createObjectURL(new Blob([content], { type: "text/plain;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = name;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  function downloadEnvironment() {
    const lines = [`${tenantEnv(tenantId)}=${customerKey}`];
    chosenProviders.forEach((provider) => {
      lines.push(`${provider.keyEnv}=${values[provider.id].apiKey}`);
      if (provider.baseUrlEnv && values[provider.id].baseUrl) lines.push(`${provider.baseUrlEnv}=${values[provider.id].baseUrl}`);
    });
    download(".env", `${lines.join("\n")}\n`);
  }

  async function copyStartCommand() {
    const command = `python -m pip install -e ".[api]"; $env:VAF_SETUP_ADMIN_KEY="${adminKey}"; $env:VAF_SETUP_ALLOWED_ORIGINS="${browserOrigin}"; python -m vertical_agent_factory.commercial.app`;
    await navigator.clipboard.writeText(command);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }

  return (
    <main className="setup-page">
      <header className="topbar">
        <Link className="brand" href="/" aria-label="返回 Vertical Agent Factory 首页"><span>VAF</span><b>Vertical Agent Factory</b></Link>
        <nav aria-label="配置页导航"><a href="#wizard">配置向导</a><a href="#how-it-works">系统会做什么</a><Link href="/">系统地图</Link></nav>
        <a className="repo-link" href="https://github.com/270438469/vertical-agent-factory" target="_blank" rel="noreferrer">GitHub ↗</a>
      </header>

      <section className="setup-hero">
        <div><p className="hero-kicker"><span className="pulse" /> NO-CODE AGENT SETUP</p><h1>不写代码，<br /><em>配置 Agent。</em></h1></div>
        <div className="setup-intro"><p>按问题填写业务、模型厂商、密钥和额度。页面会把自然语言选择转换为运行时配置；连接本地配置服务后，可一键校验并安全落盘。</p><div className="safety-note"><strong>密钥安全</strong><span>本页不持久化密钥。只有点击“应用到本机”时，密钥才会发往你电脑上的 127.0.0.1，并写入已被 Git 忽略的 .env。</span></div></div>
      </section>

      <section className="wizard-shell" id="wizard">
        <aside className="wizard-rail" aria-label="配置进度">
          <span className="eyebrow">SETUP PROGRESS</span>
          {steps.map((title, index) => <button key={title} className={index === step ? "active" : index < step ? "done" : ""} onClick={() => setStep(index)}><i>{index < step ? "✓" : String(index + 1).padStart(2, "0")}</i><span>{title}</span></button>)}
          <div className="rail-help"><b>需要准备</b><p>业务名称、要开放的任务、至少一个厂商账号/API Key，以及希望采用的调用额度。</p></div>
        </aside>

        <div className="wizard-content">
          <div className="wizard-title"><span>STEP {String(step + 1).padStart(2, "0")} / 05</span><h2>{steps[step]}</h2></div>

          {step === 0 && <div className="form-section">
            <div className="field"><label htmlFor="tenant">客户 / 项目标识</label><input id="tenant" value={tenantId} onChange={(event) => setTenantId(event.target.value)} placeholder="例如：acme-research" /><small>用于隔离客户权限和用量。只能使用字母、数字、短横线和下划线，不是公司展示名称。</small></div>
            <fieldset><legend>这个 Agent 可以做什么？</legend>{taskOptions.map((task) => <label className="choice-row" htmlFor={`task-${task.id}`} key={task.id}><input id={`task-${task.id}`} aria-label={task.title} type="checkbox" checked={tasks.includes(task.id)} onChange={() => setTasks((current) => current.includes(task.id) ? current.filter((item) => item !== task.id) : [...current, task.id])} /><span><b>{task.title}</b><small>{task.note}</small><code>{task.id}</code></span></label>)}</fieldset>
            <div className="info-card"><b>当前领域边界</b><p>此版本已经安装 <code>research</code> 研究领域包。向导会配置现有 Agent 的运行权限；新增法务、客服等新领域仍需先安装相应 Domain Pack。</p></div>
          </div>}

          {step === 1 && <div className="form-section">
            <div className="step-explainer"><b>可以只用本地 Agent</b><p>不选厂商也能运行确定性本地流程。需要大模型生成答案时，再选择一个或多个已开户的厂商。</p></div>
            <div className="provider-grid">{providers.map((provider) => <label className={`provider-card ${selected.includes(provider.id) ? "selected" : ""}`} htmlFor={`provider-${provider.id}`} key={provider.id}><input id={`provider-${provider.id}`} aria-label={`选择 ${provider.name}`} type="checkbox" checked={selected.includes(provider.id)} onChange={() => toggleProvider(provider.id)} /><span className="provider-state">{selected.includes(provider.id) ? "已选择" : "选择"}</span><b>{provider.name}</b><code>{provider.id}</code><p>{provider.preparation}</p><a href={provider.url} target="_blank" rel="noreferrer" onClick={(event) => event.stopPropagation()}>打开官方申请页面 ↗</a></label>)}</div>
          </div>}

          {step === 2 && <div className="form-section">
            {!chosenProviders.length && <div className="empty-state"><strong>你选择了纯本地模式</strong><p>无需填写厂商密钥。点击下一步设置客户调用密钥和额度。</p></div>}
            {chosenProviders.map((provider) => <article className="credential-card" key={provider.id}>
              <div className="credential-head"><div><span>{provider.id}</span><h3>{provider.name}</h3></div><a href={provider.url} target="_blank" rel="noreferrer">不知道去哪获取？打开官方页面 ↗</a></div>
              <div className="field"><label htmlFor={`${provider.id}-key`}>API Key <code>{provider.keyEnv}</code></label><input id={`${provider.id}-key`} type="password" autoComplete="off" value={values[provider.id].apiKey} onChange={(event) => updateProvider(provider.id, { apiKey: event.target.value })} placeholder="粘贴厂商控制台生成的 Key" /><small>只保存在当前页面内存中；离开或刷新页面后清空。</small></div>
              {provider.baseUrlEnv && <div className="field"><label htmlFor={`${provider.id}-url`}>Base URL（按账号需要填写） <code>{provider.baseUrlEnv}</code></label><input id={`${provider.id}-url`} value={values[provider.id].baseUrl} onChange={(event) => updateProvider(provider.id, { baseUrl: event.target.value })} placeholder="不确定时留空，系统使用官方默认地址" /><small>只接受该厂商官方 HTTPS 域名；后台还会做一次白名单校验。</small></div>}
              <fieldset><legend>模型档位（第一项是默认模型）</legend><p className="field-note">系统最多允许三档。官方公开 ID 已预填；标有“需替换”的厂商必须从你的账号复制真实模型或 Endpoint ID。</p>{values[provider.id].models.map((model, index) => <div className="model-field" key={`${provider.id}-${index}`}><span>{index === 0 ? "高能力" : index === 1 ? "均衡" : "高速/低成本"}</span><input value={model} onChange={(event) => updateModel(provider.id, index, event.target.value)} aria-label={`${provider.name} 第 ${index + 1} 档模型`} /><i>{model.startsWith("replace-with-") ? "需替换" : "已填写"}</i></div>)}</fieldset>
            </article>)}
          </div>}

          {step === 3 && <div className="form-section">
            <div className="field"><label htmlFor="customer-key">给外部调用方的客户 API Key</label><div className="input-action"><input id="customer-key" type="password" autoComplete="off" value={customerKey} onChange={(event) => setCustomerKey(event.target.value)} /><button onClick={() => setCustomerKey(randomSecret())}>重新生成</button></div><small>这不是模型厂商 Key。你的客户调用 <code>/v1/agent/runs</code> 时使用它；每个客户必须不同，至少 32 字符。</small></div>
            <div className="two-fields"><div className="field"><label htmlFor="rate">每分钟最多请求数</label><input id="rate" type="number" min="1" max="100000" value={rateLimit} onChange={(event) => setRateLimit(Number(event.target.value))} /><small>防止突发流量压垮预算。建议试运行从 60 开始。</small></div><div className="field"><label htmlFor="quota">每月最多请求数</label><input id="quota" type="number" min="1" max="1000000000" value={monthlyQuota} onChange={(event) => setMonthlyQuota(Number(event.target.value))} /><small>超过后自动拒绝，不会继续产生模型费用。</small></div></div>
            <div className="field"><label htmlFor="default-provider">默认生成方式</label><select id="default-provider" value={defaultProvider} onChange={(event) => setDefaultProvider(event.target.value)}><option value="local">本地确定性流程（不调用大模型）</option>{chosenProviders.map((provider) => <option key={provider.id} value={provider.id}>{provider.name} / {values[provider.id].models[0]}</option>)}</select><small>调用方不指定 provider 时使用此项。仍会受到任务、模型白名单和 Policy 约束。</small></div>
            <div className="policy-lock"><span>LOCKED</span><div><b>高风险写操作不会在 UI 中预批准</b><p><code>approved_capabilities</code> 固定为空。外部请求不能携带审批，发布任务会在运行时安全失败或进入可信审批流程。</p></div></div>
          </div>}

          {step === 4 && <div className="form-section">
            <div className="review-grid"><div><span>客户</span><strong>{tenantId}</strong></div><div><span>任务</span><strong>{tasks.length} 项</strong></div><div><span>外部厂商</span><strong>{chosenProviders.length} 家</strong></div><div><span>默认方式</span><strong>{defaultProvider}</strong></div></div>
            <div className="conversion-flow" id="how-it-works"><div><span>01</span><b>表单输入</b><p>业务、人类可读选择、密钥</p></div><i>→</i><div><span>02</span><b>后台校验</b><p>厂商、域名、模型、限额</p></div><i>→</i><div><span>03</span><b>安全拆分</b><p>YAML 无密钥 / .env 有密钥</p></div><i>→</i><div><span>04</span><b>重启生效</b><p>加载权限、额度与模型网关</p></div></div>
            <details className="advanced-preview" open><summary>查看自动转换后的配置（高级，可不修改）</summary><pre>{previewYaml || localYaml}</pre></details>
            <div className="apply-panel">
              <div className="apply-copy"><span>RECOMMENDED</span><h3>一键应用到本机</h3><p>先在项目目录的 PowerShell 中粘贴下面的一次性启动命令，再回到这里点击检查和应用。管理员密钥只在本次配置期间有效。</p><button className="copy-command" onClick={copyStartCommand}>{copied ? "已复制启动命令 ✓" : "复制本地配置服务启动命令"}</button></div>
              <div className="connection-fields"><div className="field"><label htmlFor="api-base">本地配置服务地址</label><input id="api-base" value={apiBase} onChange={(event) => setApiBase(event.target.value)} /></div><div className="field"><label htmlFor="admin-key">一次性管理员密钥</label><input id="admin-key" type="password" autoComplete="off" value={adminKey} onChange={(event) => setAdminKey(event.target.value)} /></div><div className="apply-actions"><button onClick={() => callSetup("preview")} disabled={result.kind === "working"}>后台检查</button><button className="primary-action" onClick={() => callSetup("apply")} disabled={result.kind === "working"}>应用到本机</button></div></div>
            </div>
            {result.message && <div className={`setup-result ${result.kind}`} role="status">{result.message}</div>}
            <div className="download-fallback"><div><b>无法连接本地服务？</b><p>可把配置包下载到本机。<code>commercial.yaml</code> 不含密钥，可以审阅；<code>.env</code> 含密钥，请勿发送或提交 Git。</p></div><button onClick={() => download("commercial.yaml", localYaml)}>下载 YAML</button><button onClick={downloadEnvironment}>下载私密 .env</button></div>
          </div>}

          <div className="wizard-footer"><button className="back" onClick={() => setStep((current) => Math.max(0, current - 1))} disabled={step === 0}>← 上一步</button>{step < steps.length - 1 && <button className="next" onClick={next}>下一步：{steps[step + 1]} →</button>}</div>
          {step < 4 && result.message && <div className={`setup-result ${result.kind}`} role="alert">{result.message}</div>}
        </div>
      </section>

      <section className="setup-explanation"><p className="eyebrow">WHAT THE SYSTEM GENERATES</p><h2>你填业务，系统翻译成运行契约。</h2><div className="explanation-grid"><article><span>01</span><h3>权限配置</h3><p>把任务勾选转换为租户允许的 Domain、Task、Provider 和 Model 白名单。</p></article><article><span>02</span><h3>密钥隔离</h3><p>YAML 只保存环境变量名称；真实厂商密钥进入 Git 忽略的本机 .env。</p></article><article><span>03</span><h3>运行保护</h3><p>自动写入每分钟限流、每月额度，并保持写操作审批默认关闭。</p></article><article><span>04</span><h3>启动校验</h3><p>重启时再次验证配置，任何占位模型、未知厂商或短密钥都会阻止错误上线。</p></article></div></section>
      <footer><div className="brand"><span>VAF</span><b>Vertical Agent Factory</b></div><p>无代码配置中心</p><p>Secrets stay local. Policies stay deterministic.</p></footer>
    </main>
  );
}
