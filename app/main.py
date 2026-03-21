import base64
import json
import os
import threading
import time
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from flask import Flask, jsonify, request

app = Flask(__name__)

items = []

_visitors = {}
_visitors_lock = threading.Lock()
VISITOR_TTL = 30

REPO = "ss-bae/cicd-demo"
GH_API = "https://api.github.com"


def gh(path, method="GET", data=None):
    token = os.environ.get("GITHUB_TOKEN", "")
    body = json.dumps(data).encode() if data else None
    req = Request(
        GH_API + path,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urlopen(req, timeout=10) as r:
            raw = r.read()
            return (json.loads(raw) if raw else {}), r.status
    except HTTPError as e:
        raw = e.read()
        return (json.loads(raw) if raw else {}), e.code


@app.route("/demo/trigger", methods=["POST"])
def demo_trigger():
    if not os.environ.get("GITHUB_TOKEN"):
        return jsonify({"error": "GITHUB_TOKEN not configured"}), 500

    # Get main branch SHA
    ref, status = gh(f"/repos/{REPO}/git/refs/heads/main")
    if status != 200:
        return jsonify({"error": "Could not get main SHA"}), 500
    main_sha = ref["object"]["sha"]

    # Create demo branch
    branch = f"demo/run-{int(time.time())}"
    _, status = gh(
        f"/repos/{REPO}/git/refs",
        method="POST",
        data={"ref": f"refs/heads/{branch}", "sha": main_sha},
    )
    if status != 201:
        return jsonify({"error": "Could not create branch"}), 500

    # Get current demo_run.txt SHA if it exists
    file_data, file_status = gh(f"/repos/{REPO}/contents/demo_run.txt?ref=main")

    # Push a commit to trigger CI
    content = base64.b64encode(f"demo run: {branch}\n".encode()).decode()
    payload = {
        "message": f"demo: trigger CI [{branch}]",
        "content": content,
        "branch": branch,
    }
    if file_status == 200:
        payload["sha"] = file_data["sha"]

    _, status = gh(
        f"/repos/{REPO}/contents/demo_run.txt",
        method="PUT",
        data=payload,
    )
    if status not in (200, 201):
        return jsonify({"error": "Could not push commit"}), 500

    return jsonify({"branch": branch})


@app.route("/demo/status/<path:branch>")
def demo_status(branch):
    if not os.environ.get("GITHUB_TOKEN"):
        return jsonify({"error": "GITHUB_TOKEN not configured"}), 500

    encoded = quote(branch, safe="")
    runs_data, _ = gh(f"/repos/{REPO}/actions/runs?branch={encoded}&per_page=1")
    runs = runs_data.get("workflow_runs", [])
    if not runs:
        return jsonify({"phase": "pending"})

    run = runs[0]
    run_id = run["id"]
    run_status = run["status"]
    run_conclusion = run.get("conclusion")

    jobs_data, _ = gh(f"/repos/{REPO}/actions/runs/{run_id}/jobs")
    jobs = jobs_data.get("jobs", [])
    steps = {}
    if jobs:
        for step in jobs[0].get("steps", []):
            steps[step["name"]] = {
                "status": step["status"],
                "conclusion": step.get("conclusion"),
            }

    branch_deleted = False
    if run_status == "completed":
        gh(
            f"/repos/{REPO}/git/refs/heads/{branch}",
            method="DELETE",
        )
        branch_deleted = True

    return jsonify(
        {
            "phase": run_status,
            "run_id": run_id,
            "run_url": run["html_url"],
            "conclusion": run_conclusion,
            "steps": steps,
            "branch_deleted": branch_deleted,
        }
    )


@app.route("/demo/ping", methods=["POST"])
def demo_ping():
    sid = (request.json or {}).get("sid", "")
    now = time.time()
    with _visitors_lock:
        if sid:
            _visitors[sid] = now
        cutoff = now - VISITOR_TTL
        stale = [k for k, v in _visitors.items() if v < cutoff]
        for k in stale:
            del _visitors[k]
        count = len(_visitors)
    return jsonify({"users": count})


INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CI/CD Demo</title>
  <style>
    *, *::before, *::after {
      box-sizing: border-box; margin: 0; padding: 0;
    }
    :root {
      --bg:      #0c1017;
      --surface: #111827;
      --border:  rgba(255,255,255,.07);
      --text:    #e2e8f0;
      --muted:   #6b7280;
      --dim:     #374151;
      --blue:    #3b82f6;
      --green:   #10b981;
      --red:     #ef4444;
    }
    [data-theme="light"] {
      --bg:      #f4ede0;
      --surface: #ede5d5;
      --border:  rgba(100,80,60,.12);
      --text:    #2c1f0f;
      --muted:   #7a6450;
      --dim:     #b09880;
      --blue:    #1d4ed8;
      --green:   #059669;
      --red:     #dc2626;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont,
        'Segoe UI', system-ui, sans-serif;
      background: var(--bg); color: var(--text);
      min-height: 100vh; line-height: 1.5;
    }

    /* Nav */
    nav {
      height: 52px; padding: 0 24px;
      display: flex; align-items: center; gap: 14px;
      border-bottom: 1px solid var(--border);
      background: rgba(12,16,23,.88);
      backdrop-filter: blur(10px);
      position: sticky; top: 0; z-index: 10;
    }
    .brand {
      display: flex; align-items: center; gap: 9px;
      font-weight: 600; font-size: .88rem; color: var(--text);
      text-decoration: none; flex: 1; letter-spacing: -.01em;
    }
    .brand-mark {
      width: 22px; height: 22px; border-radius: 6px; flex-shrink: 0;
      background: linear-gradient(135deg, #3b82f6, #6366f1);
    }
    .nav-badge {
      display: flex; align-items: center; gap: 6px;
      padding: 3px 10px; border-radius: 20px;
      background: rgba(16,185,129,.08);
      border: 1px solid rgba(16,185,129,.18);
      font-size: .72rem; font-weight: 500; color: var(--green);
    }
    .nav-pip {
      width: 6px; height: 6px; border-radius: 50%;
      background: var(--green); flex-shrink: 0;
      animation: breathe 3s ease-in-out infinite;
    }
    @keyframes breathe {
      0%, 100% { opacity: 1; } 50% { opacity: .35; }
    }
    .nav-link {
      font-size: .8rem; color: var(--muted); text-decoration: none;
      padding: 4px 8px; border-radius: 6px; transition: all .15s;
    }
    .nav-link:hover { color: var(--text); background: var(--border); }
    .nav-users {
      display: flex; align-items: center; gap: 5px;
      font-size: .75rem; color: var(--muted); font-weight: 500;
    }
    .users-dot {
      width: 6px; height: 6px; border-radius: 50%;
      background: #a78bfa; flex-shrink: 0;
      animation: breathe 3s ease-in-out infinite;
    }

    /* Page */
    .page {
      max-width: 1020px; margin: 0 auto;
      padding: 44px 24px 72px;
    }
    .page-head { margin-bottom: 36px; }
    .kicker {
      font-size: .68rem; font-weight: 600; letter-spacing: .12em;
      text-transform: uppercase; color: var(--blue); margin-bottom: 8px;
    }
    h1 {
      font-size: 1.85rem; font-weight: 700; line-height: 1.2;
      letter-spacing: -.03em; color: #f1f5f9; margin-bottom: 8px;
    }
    .sub { font-size: .875rem; color: var(--muted); }

    /* Grid */
    .grid {
      display: grid;
      grid-template-columns: 310px 1fr;
      gap: 20px; align-items: start;
    }

    /* Panel shell */
    .panel {
      border-radius: 12px; border: 1px solid var(--border);
      overflow: hidden;
    }
    .panel-head {
      display: flex; align-items: center;
      justify-content: space-between;
      padding: 11px 16px;
      background: var(--surface);
      border-bottom: 1px solid var(--border);
    }
    .panel-title {
      font-size: .68rem; font-weight: 600;
      letter-spacing: .1em; text-transform: uppercase;
      color: var(--muted);
    }

    /* Demo panel */
    .demo-panel { background: var(--surface); }
    .demo-body {
      padding: 16px;
      display: flex; flex-direction: column; gap: 18px;
    }

    .run-btn {
      width: 100%; padding: 9px 16px; border: none;
      border-radius: 8px; cursor: pointer;
      font-family: inherit; font-size: .84rem; font-weight: 600;
      color: #fff; letter-spacing: -.01em;
      background: #1d4ed8;
      box-shadow:
        0 1px 3px rgba(0,0,0,.5),
        inset 0 1px 0 rgba(255,255,255,.07);
      transition: background .15s, transform .1s, box-shadow .15s;
      display: flex; align-items: center;
      justify-content: center; gap: 8px;
    }
    .run-btn:hover {
      background: #2563eb;
      transform: translateY(-1px);
      box-shadow:
        0 4px 12px rgba(37,99,235,.35),
        inset 0 1px 0 rgba(255,255,255,.07);
    }
    .run-btn:active { transform: translateY(0); }
    .run-btn:disabled {
      background: #1a2234; color: #2d3748;
      cursor: not-allowed; transform: none; box-shadow: none;
    }

    /* Pipeline */
    .pipeline { display: flex; flex-direction: column; }
    .p-step { display: flex; gap: 12px; }
    .p-track {
      display: flex; flex-direction: column;
      align-items: center; width: 26px; flex-shrink: 0;
    }
    .p-node {
      width: 26px; height: 26px; border-radius: 50%;
      border: 2px solid var(--dim);
      background: var(--bg);
      display: flex; align-items: center; justify-content: center;
      font-size: .68rem; font-weight: 600; color: var(--dim);
      flex-shrink: 0; transition: all .3s; z-index: 1;
    }
    .p-node.success {
      border-color: #065f46; background: #052e16; color: var(--green);
    }
    .p-node.failure {
      border-color: #7f1d1d; background: #2d0a0a; color: var(--red);
    }
    .p-node.running {
      border-color: #3b82f6; background: #1e3a8a;
      color: #93c5fd; border-top-color: transparent;
      animation: spin .75s linear infinite;
    }
    .p-node.locked {
      border-color: #1a2234; background: var(--bg); color: #1a2234;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .p-wire {
      width: 1px; flex: 1; min-height: 12px;
      background: var(--dim); margin: 3px 0; opacity: .3;
    }
    .p-body { flex: 1; padding-bottom: 18px; padding-top: 4px; }
    .p-name {
      font-size: .84rem; font-weight: 500;
      color: #d1d5db; margin-bottom: 1px;
    }
    .p-msg {
      font-size: .74rem; color: var(--dim);
      min-height: 16px; transition: color .2s;
    }
    .p-msg.ok { color: var(--green); }
    .p-msg.fail { color: var(--red); }
    .p-msg.run { color: #60a5fa; }
    .p-msg.lock { color: #1f2937; font-style: italic; }

    /* Sub-steps */
    .sub-steps {
      margin-top: 8px; display: flex;
      flex-direction: column; gap: 4px;
    }
    .sub-step {
      display: flex; align-items: center;
      gap: 7px; font-size: .75rem;
    }
    .s-dot {
      width: 5px; height: 5px; border-radius: 50%;
      background: var(--dim); flex-shrink: 0; transition: all .25s;
    }
    .s-dot.ok {
      background: var(--green);
      box-shadow: 0 0 5px rgba(16,185,129,.5);
    }
    .s-dot.fail { background: var(--red); }
    .s-dot.run {
      background: #60a5fa; animation: breathe .8s infinite;
    }
    .s-label {
      color: var(--muted); flex: 1;
      font-family: 'SF Mono', Consolas, monospace;
    }
    .s-res {
      color: var(--dim); font-family: 'SF Mono', Consolas, monospace;
    }
    .s-res.ok { color: var(--green); }
    .s-res.fail { color: var(--red); }
    .s-res.run { color: #60a5fa; }

    /* Log panel */
    .log-panel {
      background: #090d14;
      display: flex; flex-direction: column;
      font-family: 'SF Mono', 'Cascadia Code',
        Consolas, 'Liberation Mono', monospace;
    }
    .log-titlebar {
      display: flex; align-items: center; gap: 7px;
      padding: 9px 14px;
      background: #0f1623;
      border-bottom: 1px solid var(--border); flex-shrink: 0;
    }
    .titlebar-label {
      flex: 1; text-align: center; font-size: .7rem; color: #2d3748;
    }
    .gh-link {
      font-size: .7rem; color: #2d3748;
      text-decoration: none; transition: color .15s;
    }
    .gh-link:hover { color: #60a5fa; }
    .log-body {
      flex: 1; overflow-y: auto;
      padding: 6px 0; min-height: 370px;
    }
    .log-empty {
      min-height: 370px;
      display: flex; flex-direction: column;
      align-items: center; justify-content: center;
      gap: 6px; color: #1f2937;
      font-family: -apple-system, sans-serif;
      font-size: .8rem;
    }
    .log-empty-glyph {
      font-size: 1.5rem; opacity: .4; margin-bottom: 2px;
    }
    .log-row {
      display: flex; align-items: baseline;
      gap: 8px; padding: 1px 14px;
      font-size: .76rem; line-height: 1.9;
    }
    .log-row:hover { background: rgba(255,255,255,.02); }
    .log-lno {
      width: 22px; text-align: right; flex-shrink: 0;
      color: #1f2937; font-size: .67rem; user-select: none;
    }
    .log-ic {
      width: 13px; text-align: center; flex-shrink: 0; font-size: .7rem;
    }
    .log-ic.ok { color: #10b981; }
    .log-ic.fail { color: #ef4444; }
    .log-ic.run { color: #60a5fa; }
    .log-ic.queued { color: #1f2937; }
    .log-txt { color: #4b5563; }
    .log-txt.run { color: #d1d5db; font-weight: 500; }
    .log-txt.fail { color: #fca5a5; }

    /* Footer */
    .foot {
      margin-top: 40px; padding-top: 20px;
      border-top: 1px solid var(--border);
      display: flex; align-items: center; gap: 20px;
    }
    .foot-link {
      font-size: .8rem; color: var(--dim);
      text-decoration: none; transition: color .15s;
    }
    .foot-link:hover { color: var(--muted); }

    /* Theme toggle button */
    .theme-toggle {
      background: none; border: 1px solid var(--border);
      border-radius: 6px; cursor: pointer;
      padding: 4px 8px; color: var(--muted);
      font-size: .8rem; font-family: inherit;
      display: flex; align-items: center; gap: 5px;
      transition: all .15s;
    }
    .theme-toggle:hover { color: var(--text); background: var(--border); }

    /* Light mode hardcoded overrides */
    [data-theme="light"] nav {
      background: rgba(244,237,224,.92);
    }
    [data-theme="light"] h1 { color: #1a0f05; }
    [data-theme="light"] .p-name { color: #3d2a18; }
    [data-theme="light"] .p-msg.lock { color: #c4b09a; }
    [data-theme="light"] .p-node { background: var(--bg); }
    [data-theme="light"] .p-node.success {
      border-color: #065f46; background: #d1fae5; color: #059669;
    }
    [data-theme="light"] .p-node.failure {
      border-color: #7f1d1d; background: #fee2e2; color: #dc2626;
    }
    [data-theme="light"] .p-node.running {
      border-color: #1d4ed8; background: #dbeafe; color: #1d4ed8;
    }
    [data-theme="light"] .p-node.locked {
      border-color: #d4c4b0; color: #d4c4b0;
    }
    [data-theme="light"] .run-btn:disabled {
      background: #ddd5c8; color: #b09880;
    }
    [data-theme="light"] .log-panel { background: #e8dece; }
    [data-theme="light"] .log-titlebar {
      background: #ddd2c0; border-bottom-color: rgba(100,80,60,.12);
    }
    [data-theme="light"] .titlebar-label { color: #9a8470; }
    [data-theme="light"] .gh-link { color: #9a8470; }
    [data-theme="light"] .log-lno { color: #c4b09a; }
    [data-theme="light"] .log-txt { color: #5c4a38; }
    [data-theme="light"] .log-txt.run { color: #2c1f0f; }
    [data-theme="light"] .log-txt.fail { color: #9f1239; }
    [data-theme="light"] .log-row:hover { background: rgba(0,0,0,.03); }
    [data-theme="light"] .log-empty { color: #c4b09a; }
    [data-theme="light"] .log-ic.queued { color: #c4b09a; }

    @media (max-width: 720px) {
      .grid { grid-template-columns: 1fr; }
      h1 { font-size: 1.5rem; }
      .nav-badge span { display: none; }
    }
  </style>
</head>
<body>

<nav>
  <a class="brand" href="#">
    <div class="brand-mark"></div>
    cicd-demo
  </a>
  <div class="nav-badge">
    <div class="nav-pip"></div>
    <span>all systems operational</span>
  </div>
  <div class="nav-users" id="nav-users" title="Live viewers">
    <span class="users-dot"></span>
    <span id="users-count">1</span>
  </div>
  <a class="nav-link"
     href="https://github.com/ss-bae/cicd-demo"
     target="_blank">GitHub</a>
  <button class="theme-toggle" id="theme-toggle" onclick="toggleTheme()">
    <span id="theme-icon">&#9788;</span>
    <span id="theme-label">Light</span>
  </button>
</nav>

<div class="page">
  <div class="page-head">
    <div class="kicker">Live Demo</div>
    <h1>CI/CD Pipeline</h1>
    <p class="sub">
      Trigger a real GitHub Actions workflow and watch it run.
    </p>
  </div>

  <div class="grid">

    <!-- Left: pipeline controls -->
    <div class="panel demo-panel">
      <div class="panel-head">
        <span class="panel-title">Pipeline</span>
      </div>
      <div class="demo-body">

        <button class="run-btn" id="run-btn" onclick="runDemo()">
          &#x25B6; Run Pipeline
        </button>

        <div class="pipeline">

          <div class="p-step">
            <div class="p-track">
              <div class="p-node" id="d-dot-1">1</div>
              <div class="p-wire"></div>
            </div>
            <div class="p-body">
              <div class="p-name">Push Code</div>
              <div class="p-msg" id="d-st-1">&mdash;</div>
            </div>
          </div>

          <div class="p-step">
            <div class="p-track">
              <div class="p-node" id="d-dot-2">2</div>
              <div class="p-wire"></div>
            </div>
            <div class="p-body">
              <div class="p-name">CI Checks</div>
              <div class="p-msg" id="d-st-2">&mdash;</div>
              <div class="sub-steps">
                <div class="sub-step">
                  <div class="s-dot" id="s-dot-flake8"></div>
                  <span class="s-label">flake8</span>
                  <span class="s-res" id="s-res-flake8">&mdash;</span>
                </div>
                <div class="sub-step">
                  <div class="s-dot" id="s-dot-black"></div>
                  <span class="s-label">black</span>
                  <span class="s-res" id="s-res-black">&mdash;</span>
                </div>
                <div class="sub-step">
                  <div class="s-dot" id="s-dot-pytest"></div>
                  <span class="s-label">pytest</span>
                  <span class="s-res" id="s-res-pytest">&mdash;</span>
                </div>
              </div>
            </div>
          </div>

          <div class="p-step">
            <div class="p-track">
              <div class="p-node" id="d-dot-3">3</div>
              <div class="p-wire"></div>
            </div>
            <div class="p-body">
              <div class="p-name">Merge Gate</div>
              <div class="p-msg" id="d-st-3">&mdash;</div>
            </div>
          </div>

          <div class="p-step">
            <div class="p-track">
              <div class="p-node locked">4</div>
              <div class="p-wire"></div>
            </div>
            <div class="p-body">
              <div class="p-name">Deploy</div>
              <div class="p-msg lock">on merge to main</div>
            </div>
          </div>

          <div class="p-step">
            <div class="p-track">
              <div class="p-node locked">5</div>
            </div>
            <div class="p-body">
              <div class="p-name">Health Check</div>
              <div class="p-msg lock">on merge to main</div>
            </div>
          </div>

        </div>
      </div>
    </div>

    <!-- Right: log panel -->
    <div class="panel log-panel">
      <div class="log-titlebar">
        <span class="titlebar-label">github-actions &mdash; test</span>
        <a class="gh-link" id="gh-link" href="#"
           target="_blank" style="display:none">open &#x2197;</a>
      </div>
      <div class="log-body" id="log-body">
        <div class="log-empty">
          <div class="log-empty-glyph">&#x25A1;</div>
          <span>waiting for run&hellip;</span>
        </div>
      </div>
    </div>

  </div>

  <div class="foot">
    <a class="foot-link"
       href="https://github.com/ss-bae/cicd-demo"
       target="_blank">GitHub &rarr;</a>
  </div>
</div>

<script>
  // Theme toggle
  (function() {
    const saved = localStorage.getItem('theme') || 'dark';
    applyTheme(saved);
  })();

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    const icon = document.getElementById('theme-icon');
    const label = document.getElementById('theme-label');
    if (icon && label) {
      if (theme === 'light') {
        icon.textContent = '\u263D';
        label.textContent = 'Dark';
      } else {
        icon.innerHTML = '&#9788;';
        label.textContent = 'Light';
      }
    }
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    localStorage.setItem('theme', next);
    applyTheme(next);
  }

  // Live user count
  const _sid = Math.random().toString(36).slice(2);
  async function pingPresence() {
    try {
      const r = await fetch('/demo/ping', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({sid: _sid})
      });
      const d = await r.json();
      document.getElementById('users-count').textContent = d.users;
    } catch(_) {}
  }
  pingPresence();
  setInterval(pingPresence, 15000);

  let pollTimer = null;
  let currentBranch = null;

  async function runDemo() {
    const btn = document.getElementById('run-btn');
    btn.disabled = true;
    clearInterval(pollTimer);
    reset();
    setStep(1, 'running', 'creating branch\u2026');
    try {
      const res = await fetch('/demo/trigger', { method: 'POST' });
      const data = await res.json();
      if (data.error) {
        setStep(1, 'failure', data.error);
        btn.disabled = false;
        return;
      }
      currentBranch = data.branch;
      setStep(1, 'success', 'branch pushed \u2713');
      setStep(2, 'running', 'waiting for runner\u2026');
      pollTimer = setInterval(poll, 3000);
    } catch (e) {
      setStep(1, 'failure', 'network error');
      btn.disabled = false;
    }
  }

  async function poll() {
    if (!currentBranch) return;
    try {
      const res = await fetch('/demo/status/' + currentBranch);
      const data = await res.json();
      apply(data);
      if (data.phase === 'completed' || data.branch_deleted) {
        clearInterval(pollTimer);
        document.getElementById('run-btn').disabled = false;
      }
    } catch (e) { /* keep polling */ }
  }

  const STEP_MAP = {
    'Lint with flake8': 'flake8',
    'Check formatting with black': 'black',
    'Run tests with coverage': 'pytest',
  };

  function apply(data) {
    if (data.phase === 'pending') {
      setStep(2, 'running', 'waiting for runner\u2026');
      return;
    }
    if (data.run_url) {
      const lnk = document.getElementById('gh-link');
      lnk.href = data.run_url;
      lnk.style.display = '';
    }
    if (data.steps) updateLog(data.steps);
    for (const [name, key] of Object.entries(STEP_MAP)) {
      const s = data.steps[name];
      if (!s) continue;
      const st = s.conclusion === 'success' ? 'ok'
        : s.conclusion === 'failure' ? 'fail'
        : s.status === 'in_progress' ? 'run' : '';
      const lb = s.conclusion === 'success' ? '\u2713'
        : s.conclusion === 'failure' ? '\u2717'
        : s.status === 'in_progress' ? '\u2026' : '\u2014';
      setSub(key, st, lb);
    }
    if (data.phase === 'in_progress') {
      setStep(2, 'running', 'running checks\u2026');
    } else if (data.phase === 'completed') {
      if (data.conclusion === 'success') {
        setStep(2, 'success', 'all checks passed \u2713');
        setStep(3, 'success', 'merge unblocked \u2713');
      } else {
        setStep(2, 'failure', 'a check failed \u2717');
        setStep(3, 'failure', 'merge blocked \u2717');
      }
    }
  }

  function updateLog(steps) {
    const body = document.getElementById('log-body');
    body.innerHTML = '';
    let n = 1;
    for (const [name, step] of Object.entries(steps)) {
      const st = step.conclusion === 'success' ? 'ok'
        : step.conclusion === 'failure' ? 'fail'
        : step.status === 'in_progress' ? 'run' : 'queued';
      const ic = st === 'ok' ? '\u2713'
        : st === 'fail' ? '\u2717'
        : st === 'run' ? '\u25b6' : '\u25cb';
      const row = document.createElement('div');
      row.className = 'log-row';
      const lno = document.createElement('span');
      lno.className = 'log-lno';
      lno.textContent = n++;
      const icon = document.createElement('span');
      icon.className = 'log-ic ' + st;
      icon.textContent = ic;
      const txt = document.createElement('span');
      txt.className = 'log-txt ' + st;
      txt.textContent = name;
      row.appendChild(lno);
      row.appendChild(icon);
      row.appendChild(txt);
      body.appendChild(row);
    }
  }

  function setStep(n, state, text) {
    const node = document.getElementById('d-dot-' + n);
    const msg = document.getElementById('d-st-' + n);
    node.className = 'p-node ' + state;
    node.textContent = state === 'success' ? '\u2713'
      : state === 'failure' ? '\u2717' : n;
    msg.textContent = text;
    msg.className = 'p-msg'
      + (state === 'success' ? ' ok'
        : state === 'failure' ? ' fail'
        : state === 'running' ? ' run' : '');
  }

  function setSub(key, state, label) {
    const dot = document.getElementById('s-dot-' + key);
    const res = document.getElementById('s-res-' + key);
    dot.className = 's-dot ' + state;
    res.textContent = label;
    res.className = 's-res ' + state;
  }

  function reset() {
    for (let i = 1; i <= 3; i++) {
      const node = document.getElementById('d-dot-' + i);
      const msg = document.getElementById('d-st-' + i);
      node.className = 'p-node';
      node.textContent = i;
      msg.textContent = '\u2014';
      msg.className = 'p-msg';
    }
    ['flake8', 'black', 'pytest'].forEach(k => setSub(k, '', '\u2014'));
    const lnk = document.getElementById('gh-link');
    lnk.style.display = 'none';
    lnk.href = '#';
    document.getElementById('log-body').innerHTML =
      '<div class="log-empty">'
      + '<div class="log-empty-glyph">\u25a1</div>'
      + '<span>waiting for run\u2026</span>'
      + '</div>';
  }
</script>
</body>
</html>"""


@app.route("/")
def index():
    return INDEX_HTML


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


@app.route("/items", methods=["GET"])
def get_items():
    return jsonify({"items": items})


@app.route("/items", methods=["POST"])
def add_item():
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"error": "name is required"}), 400
    item = {"id": len(items) + 1, "name": data["name"]}
    items.append(item)
    return jsonify(item), 201


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
