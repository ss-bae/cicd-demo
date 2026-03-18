import base64
import json
import os
import time
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from flask import Flask, jsonify, request

app = Flask(__name__)

items = []

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


INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CI/CD Pipeline Demo</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #0d1117; color: #e6edf3; min-height: 100vh;
    }
    .status-bar {
      display: flex; align-items: center; gap: 10px;
      padding: 14px 20px; border-bottom: 1px solid #21262d;
      background: #161b22;
    }
    .dot {
      width: 10px; height: 10px; border-radius: 50%;
      background: #56d364; box-shadow: 0 0 6px #56d364;
      animation: pulse 2s infinite;
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; } 50% { opacity: 0.5; }
    }
    .status-text { font-size: .9rem; font-weight: 600; color: #56d364; }
    .status-label { font-size: .9rem; color: #8b949e; }
    .content { padding: 40px 24px; max-width: 1100px; margin: 0 auto; }
    h1 {
      font-size: 1.8rem; font-weight: 700;
      text-align: center; margin-bottom: 8px; color: #f0f6fc;
    }
    .subtitle {
      text-align: center; color: #8b949e;
      margin-bottom: 40px; font-size: .95rem;
    }
    .main-layout {
      display: grid; grid-template-columns: 1fr 1fr;
      gap: 40px; margin-bottom: 48px;
    }
    .step { display: flex; align-items: flex-start; gap: 16px; }
    .step-left {
      display: flex; flex-direction: column;
      align-items: center; flex-shrink: 0; width: 40px;
    }
    .step-icon {
      width: 40px; height: 40px; border-radius: 50%;
      display: flex; align-items: center;
      justify-content: center; font-size: 1.1rem;
    }
    .step-line {
      width: 2px; flex: 1; min-height: 24px;
      background: #30363d; margin: 4px 0;
    }
    .step-body { padding-bottom: 28px; flex: 1; }
    .step-title {
      font-weight: 600; font-size: .95rem;
      margin-bottom: 4px; color: #f0f6fc;
    }
    .step-desc { font-size: .85rem; color: #8b949e; line-height: 1.5; }
    .step-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
    .tag {
      background: #161b22; border: 1px solid #30363d;
      border-radius: 4px; padding: 2px 8px;
      font-size: .75rem; color: #8b949e; font-family: monospace;
    }
    .ci   .step-icon { background: #1f3a6e; color: #79c0ff; }
    .cd   .step-icon { background: #1a3a2a; color: #56d364; }
    .live .step-icon { background: #3a2a1a; color: #ffa657; }
    .dev  .step-icon { background: #2a1a3a; color: #d2a8ff; }
    /* Demo panel */
    .demo-panel {
      background: #161b22; border: 1px solid #21262d;
      border-radius: 12px; padding: 24px;
      display: flex; flex-direction: column; gap: 20px;
    }
    .run-btn {
      width: 100%; padding: 12px; border: none; border-radius: 8px;
      background: #238636; color: #fff;
      font-size: .95rem; font-weight: 600;
      cursor: pointer; transition: background .2s;
    }
    .run-btn:hover { background: #2ea043; }
    .run-btn:disabled {
      background: #21262d; color: #484f58; cursor: not-allowed;
    }
    .d-steps { display: flex; flex-direction: column; }
    .d-step { display: flex; align-items: flex-start; gap: 12px; }
    .d-dot {
      width: 12px; height: 12px; border-radius: 50%;
      background: #30363d; margin-top: 5px; flex-shrink: 0;
      transition: all .3s;
    }
    .d-dot.running {
      background: #58a6ff; box-shadow: 0 0 8px #58a6ff;
      animation: pulse .8s infinite;
    }
    .d-dot.success { background: #56d364; box-shadow: 0 0 6px #56d364; }
    .d-dot.failure { background: #f85149; box-shadow: 0 0 6px #f85149; }
    .d-dot.locked { background: #21262d; }
    .d-body { flex: 1; padding-bottom: 4px; }
    .d-label { display: flex; gap: 8px; align-items: baseline; }
    .d-num {
      font-size: .7rem; color: #8b949e;
      text-transform: uppercase; letter-spacing: .06em;
    }
    .d-name { font-size: .9rem; font-weight: 600; color: #e6edf3; }
    .d-st {
      font-size: .8rem; color: #8b949e;
      margin-top: 2px; min-height: 18px;
    }
    .d-st.ok { color: #56d364; }
    .d-st.fail { color: #f85149; }
    .d-st.run { color: #58a6ff; }
    .d-st.lock { color: #484f58; }
    .d-conn {
      width: 2px; height: 16px; background: #21262d; margin-left: 5px;
    }
    .d-subs { margin-top: 8px; display: flex; flex-direction: column; gap: 5px; }
    .d-sub { display: flex; align-items: center; gap: 8px; font-size: .8rem; }
    .s-dot {
      width: 6px; height: 6px; border-radius: 50%;
      background: #30363d; flex-shrink: 0; transition: all .3s;
    }
    .s-dot.run { background: #58a6ff; animation: pulse .8s infinite; }
    .s-dot.ok  { background: #56d364; }
    .s-dot.fail { background: #f85149; }
    .s-name { color: #8b949e; flex: 1; }
    .s-res { color: #8b949e; font-family: monospace; }
    .s-res.ok { color: #56d364; }
    .s-res.fail { color: #f85149; }
    .s-res.run { color: #58a6ff; }
    .gh-link {
      font-size: .8rem; color: #58a6ff;
      text-decoration: none; text-align: center;
    }
    .gh-link:hover { text-decoration: underline; }
    .links { display: flex; gap: 16px; justify-content: center; }
    .links a { color: #58a6ff; font-size: .85rem; text-decoration: none; }
    .links a:hover { text-decoration: underline; }
    @media (max-width: 700px) {
      .main-layout { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="status-bar">
    <div class="dot"></div>
    <span class="status-text">healthy</span>
    <span class="status-label">&mdash; all systems operational</span>
  </div>
  <div class="content">
    <h1>CI/CD Pipeline Demo</h1>
    <p class="subtitle">
      How code goes from a local change to a live deployment
    </p>

    <div class="main-layout">

      <!-- LEFT: Steps 1-5 -->
      <div>
        <div class="step dev">
          <div class="step-left">
            <div class="step-icon">&#x270F;</div>
            <div class="step-line"></div>
          </div>
          <div class="step-body">
            <div class="step-title">1. Developer pushes code</div>
            <div class="step-desc">
              A change is committed and pushed to GitHub on any branch,
              or a pull request is opened targeting <code>main</code>.
            </div>
            <div class="step-tags">
              <span class="tag">git push</span>
            </div>
          </div>
        </div>

        <div class="step ci">
          <div class="step-left">
            <div class="step-icon">&#x2699;</div>
            <div class="step-line"></div>
          </div>
          <div class="step-body">
            <div class="step-title">2. CI runs automatically</div>
            <div class="step-desc">
              GitHub Actions spins up a fresh Ubuntu VM and runs three
              quality gates. If any step fails the PR is blocked.
            </div>
            <div class="step-tags">
              <span class="tag">flake8</span>
              <span class="tag">black --check</span>
              <span class="tag">pytest --cov</span>
            </div>
          </div>
        </div>

        <div class="step ci">
          <div class="step-left">
            <div class="step-icon">&#x1F512;</div>
            <div class="step-line"></div>
          </div>
          <div class="step-body">
            <div class="step-title">3. Branch protection gates merge</div>
            <div class="step-desc">
              The <code>main</code> branch requires the CI
              <code>test</code> job to pass before any PR can merge.
            </div>
            <div class="step-tags">
              <span class="tag">branch protection</span>
              <span class="tag">required status checks</span>
            </div>
          </div>
        </div>

        <div class="step cd">
          <div class="step-left">
            <div class="step-icon">&#x1F680;</div>
            <div class="step-line"></div>
          </div>
          <div class="step-body">
            <div class="step-title">4. Merge to main triggers CD</div>
            <div class="step-desc">
              A separate CD workflow fires only on pushes to
              <code>main</code> and sends a deploy webhook to Render.
            </div>
            <div class="step-tags">
              <span class="tag">cd.yml</span>
              <span class="tag">render webhook</span>
            </div>
          </div>
        </div>

        <div class="step live">
          <div class="step-left">
            <div class="step-icon">&#x2665;</div>
          </div>
          <div class="step-body">
            <div class="step-title">5. Health check confirms deploy</div>
            <div class="step-desc">
              The CD workflow polls <code>/health</code> every 15s
              for up to 5 minutes. Once healthy, pipeline is green.
            </div>
            <div class="step-tags">
              <span class="tag">curl --fail /health</span>
              <span class="tag">retry loop</span>
            </div>
          </div>
        </div>
      </div>

      <!-- RIGHT: Live demo panel -->
      <div class="demo-panel">
        <button class="run-btn" id="run-btn" onclick="runDemo()">
          &#x25B6;&nbsp; Run Pipeline Demo
        </button>

        <div class="d-steps">

          <div class="d-step">
            <div class="d-dot" id="d-dot-1"></div>
            <div class="d-body">
              <div class="d-label">
                <span class="d-num">Step 1</span>
                <span class="d-name">Push Code</span>
              </div>
              <div class="d-st" id="d-st-1">&mdash;</div>
            </div>
          </div>
          <div class="d-conn"></div>

          <div class="d-step">
            <div class="d-dot" id="d-dot-2"></div>
            <div class="d-body">
              <div class="d-label">
                <span class="d-num">Step 2</span>
                <span class="d-name">CI Runs</span>
              </div>
              <div class="d-st" id="d-st-2">&mdash;</div>
              <div class="d-subs">
                <div class="d-sub">
                  <div class="s-dot" id="s-dot-flake8"></div>
                  <span class="s-name">flake8 lint</span>
                  <span class="s-res" id="s-res-flake8">&mdash;</span>
                </div>
                <div class="d-sub">
                  <div class="s-dot" id="s-dot-black"></div>
                  <span class="s-name">black format</span>
                  <span class="s-res" id="s-res-black">&mdash;</span>
                </div>
                <div class="d-sub">
                  <div class="s-dot" id="s-dot-pytest"></div>
                  <span class="s-name">pytest</span>
                  <span class="s-res" id="s-res-pytest">&mdash;</span>
                </div>
              </div>
            </div>
          </div>
          <div class="d-conn"></div>

          <div class="d-step">
            <div class="d-dot" id="d-dot-3"></div>
            <div class="d-body">
              <div class="d-label">
                <span class="d-num">Step 3</span>
                <span class="d-name">Branch Protection</span>
              </div>
              <div class="d-st" id="d-st-3">&mdash;</div>
            </div>
          </div>
          <div class="d-conn"></div>

          <div class="d-step">
            <div class="d-dot locked"></div>
            <div class="d-body">
              <div class="d-label">
                <span class="d-num">Step 4</span>
                <span class="d-name">CD Deploy</span>
              </div>
              <div class="d-st lock">
                &#x1F512; only on merge to main
              </div>
            </div>
          </div>
          <div class="d-conn"></div>

          <div class="d-step">
            <div class="d-dot locked"></div>
            <div class="d-body">
              <div class="d-label">
                <span class="d-num">Step 5</span>
                <span class="d-name">Health Check</span>
              </div>
              <div class="d-st lock">
                &#x1F512; only on merge to main
              </div>
            </div>
          </div>

        </div>

        <a class="gh-link" id="gh-link" href="#"
           target="_blank" style="display:none">
          View on GitHub Actions &rarr;
        </a>
      </div>

    </div>

    <div class="links">
      <a href="https://github.com/ss-bae/cicd-demo" target="_blank">
        GitHub Repo &rarr;
      </a>
    </div>
  </div>

  <script>
    let pollTimer = null;
    let currentBranch = null;

    async function runDemo() {
      const btn = document.getElementById('run-btn');
      btn.disabled = true;
      clearInterval(pollTimer);
      reset();
      setStep(1, 'running', 'pushing branch...');
      try {
        const res = await fetch('/demo/trigger', { method: 'POST' });
        const data = await res.json();
        if (data.error) {
          setStep(1, 'failure', data.error);
          btn.disabled = false;
          return;
        }
        currentBranch = data.branch;
        setStep(1, 'success', 'branch created \u2713');
        setStep(2, 'running', 'waiting for runner...');
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
        setStep(2, 'running', 'waiting for runner...');
        return;
      }
      if (data.run_url) {
        const lnk = document.getElementById('gh-link');
        lnk.href = data.run_url;
        lnk.style.display = '';
      }
      for (const [name, key] of Object.entries(STEP_MAP)) {
        const s = data.steps[name];
        if (!s) continue;
        const state = s.conclusion === 'success' ? 'ok'
          : s.conclusion === 'failure' ? 'fail'
          : s.status === 'in_progress' ? 'run' : '';
        const label = s.conclusion === 'success' ? '\u2713'
          : s.conclusion === 'failure' ? '\u2717'
          : s.status === 'in_progress' ? '...' : '\u2014';
        setSub(key, state, label);
      }
      if (data.phase === 'in_progress') {
        setStep(2, 'running', 'running checks...');
      } else if (data.phase === 'completed') {
        if (data.conclusion === 'success') {
          setStep(2, 'success', 'all checks passed \u2713');
          setStep(3, 'success', 'CI passed \u2014 merge unblocked \u2713');
        } else {
          setStep(2, 'failure', 'a check failed \u2717');
          setStep(3, 'failure', 'CI failed \u2014 merge blocked \u2717');
        }
      }
    }

    function setStep(n, state, text) {
      const dot = document.getElementById('d-dot-' + n);
      const st = document.getElementById('d-st-' + n);
      dot.className = 'd-dot ' + state;
      st.textContent = text;
      st.className = 'd-st'
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
        setStep(i, '', '\u2014');
      }
      ['flake8', 'black', 'pytest'].forEach(k => setSub(k, '', '\u2014'));
      const lnk = document.getElementById('gh-link');
      lnk.style.display = 'none';
      lnk.href = '#';
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
