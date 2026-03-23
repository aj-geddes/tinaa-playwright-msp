---
layout: home
title: TINAA MSP
---

<style>
  /* ── Reset & base ─────────────────────────────────────────── */
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: #0f172a;
    color: #e2e8f0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    line-height: 1.6;
  }

  a { color: #3b82f6; text-decoration: none; }
  a:hover { text-decoration: underline; }

  /* ── Layout helpers ───────────────────────────────────────── */
  .section {
    padding: 80px 24px;
    max-width: 1100px;
    margin: 0 auto;
  }

  .section--wide {
    max-width: 1200px;
  }

  .section-label {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #3b82f6;
    margin-bottom: 12px;
  }

  .section-heading {
    font-size: 2rem;
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 16px;
    line-height: 1.25;
  }

  .section-sub {
    font-size: 1.05rem;
    color: #94a3b8;
    max-width: 620px;
    margin-bottom: 48px;
  }

  /* ── Dividers ─────────────────────────────────────────────── */
  .divider {
    border: none;
    border-top: 1px solid #1e293b;
    margin: 0;
  }

  /* ── Hero ─────────────────────────────────────────────────── */
  .hero {
    background: linear-gradient(160deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
    padding: 100px 24px 80px;
    text-align: center;
    position: relative;
    overflow: hidden;
  }

  .hero::before {
    content: "";
    position: absolute;
    inset: 0;
    background:
      radial-gradient(ellipse 70% 50% at 50% 0%, rgba(59,130,246,0.15) 0%, transparent 70%),
      radial-gradient(ellipse 40% 30% at 80% 80%, rgba(139,92,246,0.10) 0%, transparent 60%);
    pointer-events: none;
  }

  .hero-badge {
    display: inline-block;
    background: rgba(59,130,246,0.15);
    border: 1px solid rgba(59,130,246,0.35);
    color: #93c5fd;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 5px 14px;
    border-radius: 999px;
    margin-bottom: 28px;
  }

  .hero-title {
    font-size: clamp(2.4rem, 6vw, 4.2rem);
    font-weight: 800;
    line-height: 1.1;
    color: #f8fafc;
    margin-bottom: 24px;
    letter-spacing: -0.02em;
  }

  .hero-title span {
    background: linear-gradient(90deg, #3b82f6 0%, #8b5cf6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .hero-tagline {
    font-size: 1.2rem;
    color: #94a3b8;
    max-width: 600px;
    margin: 0 auto 40px;
    line-height: 1.7;
  }

  .hero-cta {
    display: flex;
    gap: 16px;
    justify-content: center;
    flex-wrap: wrap;
    margin-bottom: 64px;
  }

  .btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 13px 28px;
    border-radius: 8px;
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.18s ease;
    border: none;
    text-decoration: none;
  }

  .btn-primary {
    background: #3b82f6;
    color: #fff;
    box-shadow: 0 4px 24px rgba(59,130,246,0.35);
  }

  .btn-primary:hover {
    background: #2563eb;
    box-shadow: 0 6px 32px rgba(59,130,246,0.5);
    text-decoration: none;
    color: #fff;
    transform: translateY(-1px);
  }

  .btn-secondary {
    background: rgba(255,255,255,0.07);
    color: #e2e8f0;
    border: 1px solid rgba(255,255,255,0.12);
  }

  .btn-secondary:hover {
    background: rgba(255,255,255,0.12);
    text-decoration: none;
    color: #f1f5f9;
    transform: translateY(-1px);
  }

  .hero-image-wrap {
    max-width: 960px;
    margin: 0 auto;
    border-radius: 14px;
    overflow: hidden;
    box-shadow:
      0 0 0 1px rgba(59,130,246,0.2),
      0 8px 32px rgba(0,0,0,0.6),
      0 0 80px rgba(59,130,246,0.12);
    position: relative;
  }

  .hero-image-wrap img {
    display: block;
    width: 100%;
    height: auto;
    border-radius: 14px;
  }

  /* ── Stats bar ────────────────────────────────────────────── */
  .stats-bar {
    background: #1e293b;
    border-top: 1px solid #334155;
    border-bottom: 1px solid #334155;
  }

  .stats-inner {
    max-width: 900px;
    margin: 0 auto;
    padding: 32px 24px;
    display: flex;
    justify-content: space-around;
    align-items: center;
    flex-wrap: wrap;
    gap: 24px;
  }

  .stat-item {
    text-align: center;
  }

  .stat-num {
    font-size: 1.9rem;
    font-weight: 800;
    color: #3b82f6;
    display: block;
    line-height: 1;
    margin-bottom: 4px;
  }

  .stat-desc {
    font-size: 0.82rem;
    color: #64748b;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.07em;
  }

  .stat-sep {
    width: 1px;
    height: 40px;
    background: #334155;
  }

  /* ── What is TINAA ────────────────────────────────────────── */
  .what-is {
    background: #0f172a;
  }

  .what-is-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 48px;
    align-items: center;
  }

  @media (max-width: 720px) {
    .what-is-grid { grid-template-columns: 1fr; }
  }

  .what-is-pill {
    display: inline-block;
    background: rgba(59,130,246,0.12);
    border: 1px solid rgba(59,130,246,0.25);
    color: #60a5fa;
    font-size: 0.8rem;
    font-weight: 600;
    padding: 3px 12px;
    border-radius: 999px;
    margin-bottom: 8px;
  }

  .what-is-body {
    color: #94a3b8;
    line-height: 1.8;
    margin-bottom: 16px;
    font-size: 1.02rem;
  }

  .compare-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
  }

  .compare-table th {
    background: #1e293b;
    color: #94a3b8;
    font-weight: 600;
    padding: 10px 14px;
    text-align: left;
    border: 1px solid #334155;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }

  .compare-table td {
    padding: 10px 14px;
    border: 1px solid #1e293b;
    color: #cbd5e1;
    background: #0f172a;
  }

  .compare-table tr:hover td { background: #1e293b; }

  .check { color: #22c55e; font-weight: 700; }
  .cross { color: #475569; }

  /* ── Features grid ────────────────────────────────────────── */
  .features-bg {
    background: #080f1e;
  }

  .features-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 24px;
  }

  .feature-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 28px;
    transition: border-color 0.2s, box-shadow 0.2s, transform 0.2s;
  }

  .feature-card:hover {
    border-color: #3b82f6;
    box-shadow: 0 4px 24px rgba(59,130,246,0.15);
    transform: translateY(-2px);
  }

  .feature-icon {
    width: 44px;
    height: 44px;
    background: rgba(59,130,246,0.12);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 18px;
  }

  .feature-icon svg {
    width: 22px;
    height: 22px;
    color: #60a5fa;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.8;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .feature-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 10px;
  }

  .feature-desc {
    font-size: 0.9rem;
    color: #94a3b8;
    line-height: 1.65;
  }

  /* ── Screenshot gallery ───────────────────────────────────── */
  .gallery-bg {
    background: #0f172a;
  }

  .gallery-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
  }

  @media (max-width: 640px) {
    .gallery-grid { grid-template-columns: 1fr; }
  }

  .gallery-item {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    overflow: hidden;
    transition: border-color 0.2s, box-shadow 0.2s;
  }

  .gallery-item:hover {
    border-color: #475569;
    box-shadow: 0 4px 24px rgba(0,0,0,0.4);
  }

  .gallery-item img {
    display: block;
    width: 100%;
    height: auto;
  }

  .gallery-caption {
    padding: 14px 18px;
    font-size: 0.85rem;
    color: #64748b;
    font-weight: 500;
    border-top: 1px solid #1e293b;
  }

  .gallery-caption strong {
    color: #94a3b8;
    display: block;
    margin-bottom: 2px;
  }

  /* ── How it works ─────────────────────────────────────────── */
  .how-bg {
    background: #080f1e;
  }

  .steps {
    display: flex;
    gap: 0;
    position: relative;
  }

  @media (max-width: 700px) {
    .steps { flex-direction: column; }
    .step-connector { display: none; }
  }

  .step {
    flex: 1;
    text-align: center;
    padding: 0 24px;
    position: relative;
  }

  .step-num {
    width: 52px;
    height: 52px;
    background: linear-gradient(135deg, #3b82f6, #6366f1);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.3rem;
    font-weight: 800;
    color: #fff;
    margin: 0 auto 20px;
    box-shadow: 0 0 24px rgba(99,102,241,0.4);
  }

  .step-connector {
    align-self: flex-start;
    margin-top: 26px;
    color: #334155;
    font-size: 1.5rem;
    flex-shrink: 0;
  }

  .step-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 10px;
  }

  .step-desc {
    font-size: 0.88rem;
    color: #64748b;
    line-height: 1.65;
  }

  /* ── Architecture ─────────────────────────────────────────── */
  .arch-bg {
    background: #0f172a;
  }

  .arch-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 48px;
    align-items: start;
  }

  @media (max-width: 720px) {
    .arch-grid { grid-template-columns: 1fr; }
  }

  .arch-agents {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }

  .agent-chip {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 0.85rem;
  }

  .agent-chip-name {
    font-weight: 700;
    color: #60a5fa;
    margin-bottom: 2px;
  }

  .agent-chip-role {
    color: #64748b;
    font-size: 0.78rem;
  }

  .orchestrator-chip {
    grid-column: 1 / -1;
    background: rgba(59,130,246,0.08);
    border-color: rgba(59,130,246,0.3);
    text-align: center;
    padding: 14px;
  }

  .orchestrator-chip .agent-chip-name {
    font-size: 0.95rem;
    color: #93c5fd;
  }

  .arch-stack {
    list-style: none;
  }

  .arch-stack li {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 12px 0;
    border-bottom: 1px solid #1e293b;
    font-size: 0.9rem;
    color: #94a3b8;
  }

  .arch-stack li:last-child { border-bottom: none; }

  .arch-stack li span {
    font-weight: 600;
    color: #cbd5e1;
    min-width: 120px;
    flex-shrink: 0;
  }

  /* ── Quick Start ──────────────────────────────────────────── */
  .quickstart-bg {
    background: #080f1e;
  }

  .quickstart-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 48px;
    align-items: start;
  }

  @media (max-width: 720px) {
    .quickstart-grid { grid-template-columns: 1fr; }
  }

  .code-block {
    background: #020617;
    border: 1px solid #1e293b;
    border-radius: 10px;
    overflow: hidden;
  }

  .code-block-header {
    background: #1e293b;
    padding: 10px 16px;
    font-size: 0.78rem;
    color: #64748b;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .code-block-header::before {
    content: "";
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #334155;
    box-shadow: 16px 0 0 #334155, 32px 0 0 #334155;
  }

  .code-block pre {
    margin: 0;
    padding: 20px;
    overflow-x: auto;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 0.85rem;
    line-height: 1.7;
    color: #e2e8f0;
  }

  .code-block pre .comment { color: #475569; }
  .code-block pre .cmd { color: #93c5fd; }
  .code-block pre .str { color: #86efac; }
  .code-block pre .kw { color: #c084fc; }

  .qs-steps {
    list-style: none;
    counter-reset: qs-counter;
  }

  .qs-steps li {
    counter-increment: qs-counter;
    display: flex;
    gap: 16px;
    padding: 16px 0;
    border-bottom: 1px solid #1e293b;
    font-size: 0.92rem;
    color: #94a3b8;
  }

  .qs-steps li:last-child { border-bottom: none; }

  .qs-steps li::before {
    content: counter(qs-counter);
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: rgba(59,130,246,0.15);
    border: 1px solid rgba(59,130,246,0.3);
    color: #60a5fa;
    font-size: 0.78rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    margin-top: 1px;
  }

  .qs-steps li strong {
    color: #e2e8f0;
    display: block;
    margin-bottom: 2px;
  }

  /* ── CTA section ──────────────────────────────────────────── */
  .cta-bg {
    background: linear-gradient(160deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
    border-top: 1px solid #1e293b;
    text-align: center;
    padding: 96px 24px;
    position: relative;
    overflow: hidden;
  }

  .cta-bg::before {
    content: "";
    position: absolute;
    inset: 0;
    background: radial-gradient(ellipse 60% 60% at 50% 50%, rgba(59,130,246,0.1) 0%, transparent 70%);
    pointer-events: none;
  }

  .cta-inner { position: relative; }

  .cta-title {
    font-size: clamp(1.8rem, 4vw, 3rem);
    font-weight: 800;
    color: #f8fafc;
    margin-bottom: 16px;
    line-height: 1.2;
    letter-spacing: -0.02em;
  }

  .cta-sub {
    font-size: 1.1rem;
    color: #94a3b8;
    max-width: 520px;
    margin: 0 auto 40px;
  }

  .cta-buttons {
    display: flex;
    gap: 16px;
    justify-content: center;
    flex-wrap: wrap;
  }

  /* ── Footer ───────────────────────────────────────────────── */
  .site-footer {
    background: #020617;
    border-top: 1px solid #1e293b;
    padding: 32px 24px;
    text-align: center;
    font-size: 0.82rem;
    color: #475569;
  }

  .site-footer a { color: #64748b; }
  .site-footer a:hover { color: #94a3b8; }
</style>

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- HERO                                                         -->
<!-- ═══════════════════════════════════════════════════════════ -->
<section class="hero">
  <div class="hero-badge">Managed Service Platform &nbsp;·&nbsp; v2.0</div>
  <h1 class="hero-title">
    Continuous Quality,<br><span>Automated.</span>
  </h1>
  <p class="hero-tagline">
    TINAA MSP is an autonomous quality platform that generates Playwright tests,
    monitors performance, computes a composite Quality Score, and gates deploys —
    all from a single AI-coordinated system.
  </p>
  <div class="hero-cta">
    <a href="guide/getting-started" class="btn btn-primary">
      <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"/></svg>
      Get Started
    </a>
    <a href="https://github.com/aj-geddes/tinaa-playwright-msp" class="btn btn-secondary">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/></svg>
      View on GitHub
    </a>
  </div>
  <div class="hero-image-wrap">
    <img src="assets/screenshots/dashboard.png" alt="TINAA MSP Dashboard — quality score, agent status, and recent test runs" loading="lazy">
  </div>
</section>

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- STATS BAR                                                    -->
<!-- ═══════════════════════════════════════════════════════════ -->
<div class="stats-bar">
  <div class="stats-inner">
    <div class="stat-item">
      <span class="stat-num">1,400+</span>
      <span class="stat-desc">Tests generated</span>
    </div>
    <div class="stat-sep"></div>
    <div class="stat-item">
      <span class="stat-num">6</span>
      <span class="stat-desc">AI agents</span>
    </div>
    <div class="stat-sep"></div>
    <div class="stat-item">
      <span class="stat-num">14</span>
      <span class="stat-desc">MCP tools</span>
    </div>
    <div class="stat-sep"></div>
    <div class="stat-item">
      <span class="stat-num">0–100</span>
      <span class="stat-desc">Quality score</span>
    </div>
    <div class="stat-sep"></div>
    <div class="stat-item">
      <span class="stat-num">5</span>
      <span class="stat-desc">Web vitals tracked</span>
    </div>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- WHAT IS TINAA                                                -->
<!-- ═══════════════════════════════════════════════════════════ -->
<hr class="divider">
<section class="what-is">
  <div class="section">
    <div class="what-is-grid">
      <div>
        <div class="section-label">What is TINAA MSP?</div>
        <h2 class="section-heading">Not just testing. Not just APM.<br>Both — fully autonomous.</h2>
        <p class="what-is-body">
          Traditional testing tools require you to write and maintain tests manually.
          Traditional APM tools alert you after something breaks. TINAA MSP does both
          proactively: it reads your codebase, generates Playwright test playbooks
          automatically, monitors your live endpoints in real time, and computes a
          single Quality Score that tells you — and your CI pipeline — whether a
          deployment is safe.
        </p>
        <p class="what-is-body">
          Six specialised AI agents work under a central Orchestrator so that every
          product registered in TINAA is permanently under supervised quality watch.
        </p>
      </div>
      <div>
        <table class="compare-table">
          <thead>
            <tr>
              <th>Capability</th>
              <th>TINAA MSP</th>
              <th>Traditional tools</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Auto-generate tests from code</td>
              <td class="check">&#10003;</td>
              <td class="cross">&#10007;</td>
            </tr>
            <tr>
              <td>Composite Quality Score</td>
              <td class="check">&#10003;</td>
              <td class="cross">&#10007;</td>
            </tr>
            <tr>
              <td>Synthetic monitoring + Web Vitals</td>
              <td class="check">&#10003;</td>
              <td class="cross">partial</td>
            </tr>
            <tr>
              <td>Block deploys on quality failure</td>
              <td class="check">&#10003;</td>
              <td class="cross">&#10007;</td>
            </tr>
            <tr>
              <td>GitHub Check Runs on PRs</td>
              <td class="check">&#10003;</td>
              <td class="cross">&#10007;</td>
            </tr>
            <tr>
              <td>Claude Code / MCP integration</td>
              <td class="check">&#10003;</td>
              <td class="cross">&#10007;</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</section>

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- FEATURES GRID                                                -->
<!-- ═══════════════════════════════════════════════════════════ -->
<hr class="divider">
<section class="features-bg">
  <div class="section">
    <div class="section-label">Platform features</div>
    <h2 class="section-heading">Everything quality requires, built in.</h2>
    <p class="section-sub">Six focused capabilities that work together so you ship with confidence.</p>

    <div class="features-grid">

      <!-- Autonomous Testing -->
      <div class="feature-card">
        <div class="feature-icon">
          <svg viewBox="0 0 24 24"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
        </div>
        <div class="feature-title">Autonomous Testing</div>
        <p class="feature-desc">
          The Explorer and Test Designer agents analyse your repository structure and
          running application to auto-generate comprehensive Playwright playbooks.
          No manual test authoring required.
        </p>
      </div>

      <!-- Quality Scoring -->
      <div class="feature-card">
        <div class="feature-icon">
          <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
        </div>
        <div class="feature-title">Quality Scoring</div>
        <p class="feature-desc">
          A composite 0–100 Quality Score weighs test health (40 %), performance
          (30 %), security (15 %), and accessibility (15 %) into one actionable
          number tracked over time.
        </p>
      </div>

      <!-- APM & Web Vitals -->
      <div class="feature-card">
        <div class="feature-icon">
          <svg viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
        </div>
        <div class="feature-title">APM &amp; Web Vitals</div>
        <p class="feature-desc">
          Continuous synthetic monitoring tracks LCP, FCP, CLS, INP, and TTFB
          against configurable thresholds. The APM agent correlates performance
          regressions directly to deployments.
        </p>
      </div>

      <!-- Deployment Gates -->
      <div class="feature-card">
        <div class="feature-icon">
          <svg viewBox="0 0 24 24"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
        </div>
        <div class="feature-title">Deployment Gates</div>
        <p class="feature-desc">
          Define minimum Quality Score thresholds per environment. TINAA posts a
          GitHub Check Run on every PR — green to merge, red to block — keeping bad
          code out of production automatically.
        </p>
      </div>

      <!-- GitHub Integration -->
      <div class="feature-card">
        <div class="feature-icon">
          <svg viewBox="0 0 24 24"><circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M6 21V9a9 9 0 0 0 9 9"/></svg>
        </div>
        <div class="feature-title">GitHub Integration</div>
        <p class="feature-desc">
          Deep GitHub App integration: Check Runs on pull requests, deployment
          environment tracking, automatic issue creation on quality regressions, and
          webhook-driven test triggers on push.
        </p>
      </div>

      <!-- MCP / Claude Code -->
      <div class="feature-card">
        <div class="feature-icon">
          <svg viewBox="0 0 24 24"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
        </div>
        <div class="feature-title">Claude Code / MCP</div>
        <p class="feature-desc">
          A full MCP server exposes 14 tools so Claude Code can register products,
          trigger test runs, query Quality Scores, and manage alerts — all from your
          terminal without leaving your editor.
        </p>
      </div>

    </div>
  </div>
</section>

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- SCREENSHOT GALLERY                                           -->
<!-- ═══════════════════════════════════════════════════════════ -->
<hr class="divider">
<section class="gallery-bg">
  <div class="section section--wide">
    <div class="section-label">Platform screenshots</div>
    <h2 class="section-heading">See it in action.</h2>
    <p class="section-sub">A dark-first web dashboard built with Web Components and Tailwind CSS, deployed at <a href="https://tinaa.hvs">tinaa.hvs</a>.</p>

    <div class="gallery-grid">
      <div class="gallery-item">
        <img src="assets/screenshots/dashboard.png" alt="TINAA MSP main dashboard showing Quality Score gauge, agent status, and recent activity" loading="lazy">
        <div class="gallery-caption">
          <strong>Dashboard</strong>
          Quality Score gauge, live agent status, and recent test-run history at a glance.
        </div>
      </div>
      <div class="gallery-item">
        <img src="assets/screenshots/alerts.png" alt="Alerts view with severity levels and alert rules table" loading="lazy">
        <div class="gallery-caption">
          <strong>Alerts</strong>
          Multi-channel alert rules with severity classification — Slack, Teams, PagerDuty, and more.
        </div>
      </div>
      <div class="gallery-item">
        <img src="assets/screenshots/metrics.png" alt="Metrics view with time range selector and Web Vitals tabs" loading="lazy">
        <div class="gallery-caption">
          <strong>Metrics &amp; Web Vitals</strong>
          Time-series charts for LCP, FCP, CLS, INP, and TTFB with configurable time ranges.
        </div>
      </div>
      <div class="gallery-item">
        <img src="assets/screenshots/integrations.png" alt="GitHub integration setup screen" loading="lazy">
        <div class="gallery-caption">
          <strong>GitHub Integration</strong>
          Connect a GitHub App in minutes — Check Runs, deployment tracking, and issue creation included.
        </div>
      </div>
    </div>
  </div>
</section>

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- HOW IT WORKS                                                 -->
<!-- ═══════════════════════════════════════════════════════════ -->
<hr class="divider">
<section class="how-bg">
  <div class="section">
    <div class="section-label">How it works</div>
    <h2 class="section-heading">Three steps to autonomous quality.</h2>
    <p class="section-sub" style="margin-bottom: 56px;">From first registration to gated deploys in under an hour.</p>

    <div class="steps">
      <div class="step">
        <div class="step-num">1</div>
        <div class="step-title">Register a product</div>
        <p class="step-desc">
          Point TINAA at your repository and deployed environments.
          Provide a base URL and optional credentials. That is all the
          configuration required to start.
        </p>
      </div>
      <div class="step-connector">&#8594;</div>
      <div class="step">
        <div class="step-num">2</div>
        <div class="step-title">TINAA explores</div>
        <p class="step-desc">
          The Explorer agent crawls your live application and analyses your
          codebase. The Test Designer generates a prioritised Playwright
          playbook. The APM agent begins endpoint monitoring.
        </p>
      </div>
      <div class="step-connector">&#8594;</div>
      <div class="step">
        <div class="step-num">3</div>
        <div class="step-title">Continuous quality</div>
        <p class="step-desc">
          The Test Runner executes playbooks on every deploy. The Analyst
          computes the Quality Score. The Reporter gates your GitHub Check
          Run and sends alerts when thresholds are breached.
        </p>
      </div>
    </div>
  </div>
</section>

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- ARCHITECTURE                                                 -->
<!-- ═══════════════════════════════════════════════════════════ -->
<hr class="divider">
<section class="arch-bg">
  <div class="section">
    <div class="section-label">Architecture</div>
    <h2 class="section-heading">Agent-based, event-driven.</h2>
    <p class="section-sub">An Orchestrator coordinates six specialised agents over an async message bus.</p>

    <div class="arch-grid">
      <div>
        <div class="arch-agents">
          <div class="agent-chip orchestrator-chip">
            <div class="agent-chip-name">Orchestrator</div>
            <div class="agent-chip-role">Coordinates all agents, manages state &amp; scheduling</div>
          </div>
          <div class="agent-chip">
            <div class="agent-chip-name">Explorer</div>
            <div class="agent-chip-role">Crawls app, maps routes</div>
          </div>
          <div class="agent-chip">
            <div class="agent-chip-name">Test Designer</div>
            <div class="agent-chip-role">Generates Playwright playbooks</div>
          </div>
          <div class="agent-chip">
            <div class="agent-chip-name">Test Runner</div>
            <div class="agent-chip-role">Executes tests, reports results</div>
          </div>
          <div class="agent-chip">
            <div class="agent-chip-name">APM</div>
            <div class="agent-chip-role">Synthetic monitoring + Web Vitals</div>
          </div>
          <div class="agent-chip">
            <div class="agent-chip-name">Analyst</div>
            <div class="agent-chip-role">Computes Quality Score</div>
          </div>
          <div class="agent-chip">
            <div class="agent-chip-name">Reporter</div>
            <div class="agent-chip-role">Alerts, GitHub Checks, issues</div>
          </div>
        </div>
      </div>
      <div>
        <ul class="arch-stack">
          <li><span>API layer</span> FastAPI, async Python 3.11+</li>
          <li><span>Test engine</span> Playwright (Chromium, Firefox, WebKit)</li>
          <li><span>Primary store</span> PostgreSQL + TimescaleDB (time-series metrics)</li>
          <li><span>Cache / pub-sub</span> Redis</li>
          <li><span>Dashboard</span> Web Components, Tailwind CSS, dark mode</li>
          <li><span>MCP server</span> FastMCP — 14 tools for Claude Code</li>
          <li><span>Deployment</span> Docker Compose or Kubernetes (Helm chart)</li>
          <li><span>Alerts</span> Slack, Teams, Email, PagerDuty, Webhooks, GitHub Issues</li>
        </ul>
      </div>
    </div>
  </div>
</section>

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- QUICK START                                                  -->
<!-- ═══════════════════════════════════════════════════════════ -->
<hr class="divider">
<section class="quickstart-bg">
  <div class="section">
    <div class="section-label">Quick start</div>
    <h2 class="section-heading">Up and running in minutes.</h2>
    <p class="section-sub">Docker Compose is the fastest path to a working TINAA MSP instance.</p>

    <div class="quickstart-grid">
      <div class="code-block">
        <div class="code-block-header">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;bash</div>
        <pre><span class="comment"># 1 — Clone the repository</span>
<span class="cmd">git clone</span> https://github.com/aj-geddes/tinaa-playwright-msp.git
<span class="cmd">cd</span> tinaa-playwright-msp

<span class="comment"># 2 — Copy and edit environment variables</span>
<span class="cmd">cp</span> .env.example .env
<span class="comment">#   Set GITHUB_TOKEN, DB credentials, etc.</span>

<span class="comment"># 3 — Start all services</span>
<span class="cmd">docker compose up -d</span>

<span class="comment"># 4 — Confirm the API is ready</span>
<span class="cmd">curl</span> http://localhost:8000/health

<span class="comment"># 5 — Open the dashboard</span>
<span class="comment">#   http://localhost:8000</span></pre>
      </div>

      <ol class="qs-steps">
        <li>
          <div>
            <strong>Clone &amp; configure</strong>
            Copy <code>.env.example</code> to <code>.env</code> and fill in your
            database credentials and GitHub token.
          </div>
        </li>
        <li>
          <div>
            <strong>Start services</strong>
            <code>docker compose up -d</code> brings up the API, PostgreSQL,
            TimescaleDB, and Redis in one command.
          </div>
        </li>
        <li>
          <div>
            <strong>Register your first product</strong>
            POST to <code>/api/v1/products</code> with your repo URL and base
            application URL, or use the dashboard form.
          </div>
        </li>
        <li>
          <div>
            <strong>Connect GitHub</strong>
            Install the GitHub App and configure the webhook. TINAA will post
            Check Runs on your next pull request automatically.
          </div>
        </li>
        <li>
          <div>
            <strong>Connect Claude Code (optional)</strong>
            Add TINAA's MCP server to your Claude Code config for 14 AI-powered
            quality tools directly in your terminal.
          </div>
        </li>
      </ol>
    </div>
  </div>
</section>

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- CTA                                                          -->
<!-- ═══════════════════════════════════════════════════════════ -->
<section class="cta-bg">
  <div class="cta-inner">
    <h2 class="cta-title">Ready to automate quality?</h2>
    <p class="cta-sub">
      Start with the getting-started guide or explore the full documentation to
      see how TINAA MSP fits into your delivery pipeline.
    </p>
    <div class="cta-buttons">
      <a href="guide/getting-started" class="btn btn-primary">
        Read the guide
      </a>
      <a href="https://github.com/aj-geddes/tinaa-playwright-msp" class="btn btn-secondary">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/></svg>
        View on GitHub
      </a>
    </div>
  </div>
</section>

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- FOOTER                                                       -->
<!-- ═══════════════════════════════════════════════════════════ -->
<footer class="site-footer">
  <p>
    TINAA MSP &mdash; Testing Intelligence Network Automation Assistant &mdash; Managed Service Platform
    &nbsp;&nbsp;|&nbsp;&nbsp;
    <a href="https://github.com/aj-geddes/tinaa-playwright-msp">GitHub</a>
    &nbsp;&middot;&nbsp;
    <a href="guide/getting-started">Getting Started</a>
    &nbsp;&middot;&nbsp;
    <a href="https://github.com/aj-geddes/tinaa-playwright-msp/blob/main/LICENSE">License</a>
  </p>
</footer>
