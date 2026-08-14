"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

type Market = "macro" | "a-share" | "us-stock";

const panels = {
  macro: {
    eyebrow: "MACRO / GLOBAL",
    title: "宏观温度计",
    subject: "中国 + 美国",
    date: "样例数据 · 2026-08-14",
    verdict: "增长与通胀信号分化，结论应按地区拆开观察。",
    metrics: [["美国实际 GDP", "+1.4%", "季度环比年率"], ["美国 CPI", "+2.7%", "同比"], ["中国 GDP", "+5.0%", "同比"], ["联邦基金利率", "4.33%", "政策利率"]],
    facts: ["每个指标保留观测日期、单位和来源代码。", "最新值与前值分开存储，不把模型判断写成事实。", "真实模式由 FRED 与 Tushare 提供时间序列。"],
  },
  "a-share": {
    eyebrow: "EQUITY / CN",
    title: "A 股风险扫描",
    subject: "600000.SH",
    date: "样例数据 · 20 个交易日",
    verdict: "区间小幅上涨，但最大回撤提示路径风险仍然存在。",
    metrics: [["区间收益", "+4.8%", "首尾收盘价"], ["历史波动率", "21.3%", "日收益年化"], ["最大回撤", "-6.1%", "区间峰谷"], ["证据状态", "充分", "20 条日线"]],
    facts: ["证券代码会规范化为交易所后缀格式。", "所有指标由确定性代码计算，不交给大模型心算。", "真实模式使用 Tushare 日线接口。"],
  },
  "us-stock": {
    eyebrow: "EQUITY / US",
    title: "美股风险扫描",
    subject: "AAPL",
    date: "样例数据 · 20 个交易日",
    verdict: "趋势为正不等于风险消失，波动率与回撤需同时阅读。",
    metrics: [["区间收益", "+6.2%", "首尾收盘价"], ["历史波动率", "24.8%", "日收益年化"], ["最大回撤", "-5.4%", "区间峰谷"], ["证据状态", "充分", "20 条日线"]],
    facts: ["只接受规范的美股代码，拒绝注入式输入。", "数据时间与分析生成时间分别记录。", "真实模式使用 Alpha Vantage 日线接口。"],
  },
} as const;

const commands = [
  ["宏观 中国", "返回中国 GDP 等宏观指标与证据日期。"],
  ["宏观 美国", "返回美国增长、通胀、就业与利率观察。"],
  ["宏观 全球", "组合中美指标，明确事实与推断。"],
  ["A股 600000", "规范化为 600000.SH 后计算风险指标。"],
  ["美股 AAPL", "读取美股日线并生成非个性化研究摘要。"],
];

export default function FinancePage() {
  const [market, setMarket] = useState<Market>("macro");
  const [command, setCommand] = useState("宏观 全球");
  const panel = panels[market];
  const simulatedReply = useMemo(() => {
    const row = commands.find(([value]) => value === command) ?? commands[0];
    return `${row[1]}\n\n状态：样例数据 / 证据充分\n仅供研究和信息参考，不构成投资建议、收益承诺或交易指令。`;
  }, [command]);

  return (
    <main className="finance-page">
      <header className="topbar finance-nav">
        <Link className="brand" href="/" aria-label="返回 Vertical Agent Factory 首页"><span>VAF</span><b>Vertical Agent Factory</b></Link>
        <nav aria-label="金融 Agent 页面导航"><a href="#lab">分析实验室</a><a href="#architecture">运行方式</a><a href="#wechat">微信公众号</a><Link href="/setup">配置中心</Link></nav>
        <a className="repo-link" href="https://github.com/270438469/vertical-agent-factory" target="_blank" rel="noreferrer">GitHub ↗</a>
      </header>

      <section className="finance-hero">
        <div className="finance-hero-copy">
          <p className="hero-kicker"><span className="pulse" /> EVIDENCE-FIRST FINANCE AGENT</p>
          <h1>读宏观，<br />看市场，<br /><em>不替你下注。</em></h1>
          <p>面向金融宏观、A 股和美股的可审计研究 Agent。它先读取带日期的事实数据，再用确定性代码计算风险，最后才生成文字解释。</p>
          <div className="hero-actions"><Link className="button primary" href="/setup">无代码配置 <span>→</span></Link><a className="button ghost" href="#wechat">查看公众号接入</a></div>
        </div>
        <aside className="market-tape" aria-label="金融 Agent 能力摘要">
          <div className="tape-head"><span>RESEARCH TERMINAL</span><i>DATA MODE / FIXTURE</i></div>
          <div className="tape-row"><b>MACRO</b><span>CN · US · GLOBAL</span><i>DATED</i></div>
          <div className="tape-row"><b>A-SHARE</b><span>RETURN · VOL · DRAWDOWN</span><i>READ</i></div>
          <div className="tape-row"><b>US STOCK</b><span>RETURN · VOL · DRAWDOWN</span><i>READ</i></div>
          <div className="tape-row warning"><b>PUBLISH</b><span>BRIEFING</span><i>APPROVAL</i></div>
          <div className="tape-boundary"><span>HARD BOUNDARY</span><p>无个性化荐股 · 无目标价 · 无收益承诺 · 无自动下单</p></div>
        </aside>
      </section>

      <section className="finance-lab" id="lab">
        <div className="finance-section-title"><span>01 / ANALYSIS LAB</span><h2>三类研究，共用一套受控运行链。</h2><p>下方数字是可复现的内置样例，用于解释系统输出结构；切换真实模式后，计算方法和证据契约保持不变。</p></div>
        <div className="market-tabs" role="tablist" aria-label="金融市场类型">
          {(["macro", "a-share", "us-stock"] as Market[]).map((key) => <button key={key} role="tab" aria-selected={market === key} className={market === key ? "active" : ""} onClick={() => setMarket(key)}>{key === "macro" ? "金融宏观" : key === "a-share" ? "A 股" : "美股"}<span>{panels[key].subject}</span></button>)}
        </div>
        <article className="analysis-board" aria-live="polite">
          <div className="analysis-summary"><span>{panel.eyebrow}</span><h3>{panel.title}</h3><strong>{panel.subject}</strong><small>{panel.date}</small><p>{panel.verdict}</p></div>
          <div className="metric-grid">{panel.metrics.map(([label, value, note]) => <div key={label}><span>{label}</span><strong>{value}</strong><small>{note}</small></div>)}</div>
          <div className="evidence-list"><b>证据与方法</b>{panel.facts.map((fact, index) => <p key={fact}><span>{String(index + 1).padStart(2, "0")}</span>{fact}</p>)}</div>
        </article>
        <div className="research-disclaimer"><b>统一输出边界</b><p>每次回答都附带数据日期、来源、事实、推断、警告与免责声明。数据不足时终态为 <code>INSUFFICIENT_EVIDENCE</code>，不会输出虚构结论。</p></div>
      </section>

      <section className="finance-architecture" id="architecture">
        <div className="finance-section-title light"><span>02 / CONTROLLED PIPELINE</span><h2>数据先过契约，结论再过校验。</h2></div>
        <div className="finance-flow">
          <article><span>01</span><b>接收研究问题</b><p>宏观地区或证券代码先通过 Schema 和字符白名单。</p><code>finance.*.analyze</code></article>
          <article><span>02</span><b>加载带日期数据</b><p>样例或官方 API 被转换为统一结构，Secret 只从环境变量读取。</p><code>Tushare / FRED / Alpha Vantage</code></article>
          <article><span>03</span><b>确定性计算</b><p>区间收益、历史波动率、最大回撤由 Python 计算。</p><code>facts ≠ inference</code></article>
          <article><span>04</span><b>校验与留痕</b><p>验证证据、日期、免责声明和风险边界，并写入 Trace。</p><code>30 / 30 finance evals</code></article>
        </div>
      </section>

      <section className="wechat-section" id="wechat">
        <div className="wechat-copy"><span>03 / WECHAT OFFICIAL ACCOUNT</span><h2>把研究入口放进公众号。</h2><p>当前通道实现微信公众平台服务器校验、明文 XML 消息解析、命令路由、幂等键和被动文本回复。它不会主动群发，也不会执行交易。</p><ol><li>部署可公网访问的 HTTPS API。</li><li>在配置中心生成 Token 和回调 URL。</li><li>微信公众平台选择明文模式并完成服务器验证。</li><li>用右侧命令格式开始测试。</li></ol><Link className="button primary" href="/setup">配置微信公众号 <span>→</span></Link></div>
        <div className="wechat-phone" aria-label="微信公众号命令模拟器">
          <div className="phone-head"><span>金融研究助手</span><i>被动回复 · 明文模式</i></div>
          <div className="chat-bubble user">{command}</div>
          <div className="chat-bubble agent">{simulatedReply}</div>
          <label htmlFor="wechat-command">选择一条测试命令</label>
          <select id="wechat-command" value={command} onChange={(event) => setCommand(event.target.value)}>{commands.map(([value]) => <option key={value}>{value}</option>)}</select>
        </div>
      </section>

      <section className="finance-cta"><p className="eyebrow">START WITH FIXTURES. SWITCH TO LIVE WHEN READY.</p><h2>先跑通，再接真实数据。</h2><p>无代码向导会把业务选择转换为租户权限、数据模式、模型白名单、环境变量和微信公众号回调配置。</p><Link className="button dark" href="/setup">打开配置中心 <span>→</span></Link></section>
      <footer><div className="brand"><span>VAF</span><b>Vertical Agent Factory</b></div><p>金融研究 Agent · 仅供研究参考</p><p>No advice. No promises. No trades.</p></footer>
    </main>
  );
}
