from flask import Flask, jsonify, request

app = Flask(__name__)

items = []

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
      background: #0d1117;
      color: #e6edf3;
      min-height: 100vh;
      padding: 48px 24px;
    }
    h1 {
      font-size: 1.8rem;
      font-weight: 700;
      text-align: center;
      margin-bottom: 8px;
      color: #f0f6fc;
    }
    .subtitle {
      text-align: center;
      color: #8b949e;
      margin-bottom: 48px;
      font-size: 0.95rem;
    }
    .pipeline {
      display: flex;
      flex-direction: column;
      gap: 0;
      max-width: 560px;
      margin: 0 auto;
    }
    .step {
      display: flex;
      align-items: flex-start;
      gap: 16px;
    }
    .step-left {
      display: flex;
      flex-direction: column;
      align-items: center;
      flex-shrink: 0;
      width: 40px;
    }
    .step-icon {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.1rem;
      flex-shrink: 0;
    }
    .step-line {
      width: 2px;
      flex: 1;
      min-height: 24px;
      background: #30363d;
      margin: 4px 0;
    }
    .step-body {
      padding-bottom: 28px;
      flex: 1;
    }
    .step-title {
      font-weight: 600;
      font-size: 0.95rem;
      margin-bottom: 4px;
      color: #f0f6fc;
    }
    .step-desc {
      font-size: 0.85rem;
      color: #8b949e;
      line-height: 1.5;
    }
    .step-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 8px;
    }
    .tag {
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 4px;
      padding: 2px 8px;
      font-size: 0.75rem;
      color: #8b949e;
      font-family: monospace;
    }
    .ci   .step-icon { background: #1f3a6e; color: #79c0ff; }
    .cd   .step-icon { background: #1a3a2a; color: #56d364; }
    .live .step-icon { background: #3a2a1a; color: #ffa657; }
    .dev  .step-icon { background: #2a1a3a; color: #d2a8ff; }
    .links {
      display: flex;
      gap: 16px;
      justify-content: center;
      margin-top: 8px;
    }
    .links a {
      color: #58a6ff;
      font-size: 0.85rem;
      text-decoration: none;
    }
    .links a:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <h1>CI/CD Pipeline Demo</h1>
  <p class="subtitle">How code goes from a local change to a live deployment</p>

  <div class="pipeline">

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
        <div class="step-tags"><span class="tag">git push</span></div>
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
          GitHub Actions spins up a fresh Ubuntu VM and runs three quality
          gates in sequence. If any step fails, the pipeline stops and the
          PR is blocked from merging.
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
        <div class="step-title">3. Branch protection gates the merge</div>
        <div class="step-desc">
          The <code>main</code> branch requires the CI <code>test</code> job to pass
          before any pull request can be merged. No exceptions, not even for admins.
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
          A separate CD workflow fires only on pushes to <code>main</code>.
          It sends a deploy webhook to Render, which rebuilds and restarts the app.
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
          The CD workflow polls <code>/health</code> every 15s for up to 5 minutes.
          Once the app responds healthy, the pipeline is marked green.
        </div>
        <div class="step-tags">
          <span class="tag">curl --fail /health</span>
          <span class="tag">retry loop</span>
        </div>
      </div>
    </div>

  </div>

  <div class="links" style="margin-top: 40px;">
    <a href="https://github.com/ss-bae/cicd-demo" target="_blank">GitHub Repo &rarr;</a>
    <a href="/health">Health Check &rarr;</a>
    <a href="/items">Items API &rarr;</a>
  </div>
</body>
</html>"""

HEALTH_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Health</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #0d1117;
      color: #e6edf3;
      min-height: 100vh;
    }
    .status-bar {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 14px 20px;
      border-bottom: 1px solid #21262d;
      background: #161b22;
    }
    .dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: #56d364;
      box-shadow: 0 0 6px #56d364;
      animation: pulse 2s infinite;
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }
    .status-text {
      font-size: 0.9rem;
      font-weight: 600;
      color: #56d364;
    }
    .status-label {
      font-size: 0.9rem;
      color: #8b949e;
    }
    .body {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: calc(100vh - 53px);
      flex-direction: column;
      gap: 8px;
    }
    .big-dot {
      width: 64px;
      height: 64px;
      border-radius: 50%;
      background: #56d364;
      box-shadow: 0 0 32px #56d36466;
      animation: pulse 2s infinite;
    }
    h2 { font-size: 1.4rem; color: #f0f6fc; margin-top: 16px; }
    p { color: #8b949e; font-size: 0.9rem; }
  </style>
</head>
<body>
  <div class="status-bar">
    <div class="dot"></div>
    <span class="status-text">healthy</span>
    <span class="status-label">&mdash; all systems operational</span>
  </div>
  <div class="body">
    <div class="big-dot"></div>
    <h2>All Systems Operational</h2>
    <p>cicd-demo is running normally</p>
  </div>
</body>
</html>"""


@app.route("/")
def index():
    return INDEX_HTML


@app.route("/health")
def health():
    return HEALTH_HTML


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
