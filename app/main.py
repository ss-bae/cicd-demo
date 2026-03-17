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
      width: 10px; height: 10px; border-radius: 50%;
      background: #56d364; box-shadow: 0 0 6px #56d364;
      animation: pulse 2s infinite;
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
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
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 40px;
      margin-bottom: 48px;
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
    .step-tags {
      display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px;
    }
    .tag {
      background: #161b22; border: 1px solid #30363d;
      border-radius: 4px; padding: 2px 8px;
      font-size: .75rem; color: #8b949e; font-family: monospace;
    }
    .ci   .step-icon { background: #1f3a6e; color: #79c0ff; }
    .cd   .step-icon { background: #1a3a2a; color: #56d364; }
    .live .step-icon { background: #3a2a1a; color: #ffa657; }
    .dev  .step-icon { background: #2a1a3a; color: #d2a8ff; }
    .anim-panel {
      display: flex; flex-direction: column;
      align-items: center; justify-content: center;
      background: #161b22; border: 1px solid #21262d;
      border-radius: 12px; padding: 32px 24px;
    }
    .anim-title {
      font-size: .8rem; color: #8b949e;
      text-transform: uppercase; letter-spacing: .08em;
      margin-bottom: 28px;
    }
    .anim-track {
      display: flex; flex-direction: column;
      align-items: stretch; width: 100%;
    }
    .anim-node {
      display: flex; align-items: center; gap: 14px;
      width: 100%; padding: 12px 16px;
      border-radius: 8px; border: 1px solid #30363d;
      background: #0d1117; transition: all .4s ease;
    }
    .anim-node.active {
      border-color: var(--color);
      background: var(--bg);
      box-shadow: 0 0 16px var(--glow);
    }
    .anim-icon {
      width: 36px; height: 36px; border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      font-size: 1rem; background: #21262d;
      transition: background .4s ease; flex-shrink: 0;
    }
    .anim-node.active .anim-icon { background: var(--bg-icon); }
    .anim-label { flex: 1; }
    .anim-step-num {
      font-size: .7rem; color: #8b949e;
      text-transform: uppercase; letter-spacing: .06em;
      transition: color .4s ease;
    }
    .anim-node.active .anim-step-num { color: var(--color); }
    .anim-name {
      font-size: .9rem; font-weight: 600;
      color: #484f58; transition: color .4s ease;
    }
    .anim-node.active .anim-name { color: #f0f6fc; }
    .anim-connector {
      width: 2px; height: 24px; background: #21262d;
      position: relative; margin: 0 auto;
    }
    .signal-dot {
      width: 6px; height: 6px; border-radius: 50%;
      background: #58a6ff; position: absolute;
      left: 50%; transform: translateX(-50%); opacity: 0;
    }
    .signal-dot.go { animation: travel .7s ease-in forwards; }
    @keyframes travel {
      0%   { top: 0; opacity: 1; }
      100% { top: 24px; opacity: 0; }
    }
    .api-demo {
      border: 1px solid #21262d; border-radius: 12px;
      background: #161b22; padding: 28px; margin-bottom: 32px;
    }
    .api-demo h3 {
      font-size: 1rem; font-weight: 600;
      color: #f0f6fc; margin-bottom: 4px;
    }
    .api-desc { font-size: .85rem; color: #8b949e; margin-bottom: 20px; }
    .api-input-row { display: flex; gap: 10px; margin-bottom: 20px; }
    .api-input {
      flex: 1; background: #0d1117; border: 1px solid #30363d;
      border-radius: 6px; padding: 10px 14px;
      color: #e6edf3; font-size: .9rem; outline: none;
    }
    .api-input:focus { border-color: #58a6ff; }
    .api-btn {
      background: #238636; border: none; border-radius: 6px;
      padding: 10px 20px; color: #fff;
      font-size: .9rem; font-weight: 600;
      cursor: pointer; transition: background .2s;
    }
    .api-btn:hover { background: #2ea043; }
    .api-btn:disabled {
      background: #21262d; color: #484f58; cursor: not-allowed;
    }
    .items-list { display: flex; flex-direction: column; gap: 8px; }
    .item-row {
      display: flex; align-items: center; gap: 12px;
      background: #0d1117; border: 1px solid #21262d;
      border-radius: 6px; padding: 10px 14px;
      animation: fadeIn .3s ease;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(-4px); }
      to { opacity: 1; }
    }
    .item-id {
      font-size: .75rem; color: #8b949e;
      font-family: monospace; min-width: 40px;
    }
    .item-name { font-size: .9rem; color: #e6edf3; }
    .empty-state { color: #484f58; font-size: .85rem; font-style: italic; }
    .api-status { font-size: .8rem; color: #8b949e; margin-top: 8px; }
    .api-status.ok { color: #56d364; }
    .api-status.err { color: #f85149; }
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

      <!-- RIGHT: Animation -->
      <div class="anim-panel">
        <div class="anim-title">Pipeline in action</div>
        <div class="anim-track">

          <div class="anim-node" id="anim-0"
            style="--color:#d2a8ff;--bg:#2a1a3a;
                   --bg-icon:#3d2657;--glow:#d2a8ff33">
            <div class="anim-icon">&#x270F;</div>
            <div class="anim-label">
              <div class="anim-step-num">Step 1</div>
              <div class="anim-name">Push Code</div>
            </div>
          </div>

          <div class="anim-connector">
            <div class="signal-dot" id="sig-0"></div>
          </div>

          <div class="anim-node" id="anim-1"
            style="--color:#79c0ff;--bg:#1f3a6e;
                   --bg-icon:#2a4a8e;--glow:#79c0ff33">
            <div class="anim-icon">&#x2699;</div>
            <div class="anim-label">
              <div class="anim-step-num">Step 2</div>
              <div class="anim-name">CI Runs</div>
            </div>
          </div>

          <div class="anim-connector">
            <div class="signal-dot" id="sig-1"></div>
          </div>

          <div class="anim-node" id="anim-2"
            style="--color:#79c0ff;--bg:#1f3a6e;
                   --bg-icon:#2a4a8e;--glow:#79c0ff33">
            <div class="anim-icon">&#x1F512;</div>
            <div class="anim-label">
              <div class="anim-step-num">Step 3</div>
              <div class="anim-name">Branch Protection</div>
            </div>
          </div>

          <div class="anim-connector">
            <div class="signal-dot" id="sig-2"></div>
          </div>

          <div class="anim-node" id="anim-3"
            style="--color:#56d364;--bg:#1a3a2a;
                   --bg-icon:#1f4a35;--glow:#56d36433">
            <div class="anim-icon">&#x1F680;</div>
            <div class="anim-label">
              <div class="anim-step-num">Step 4</div>
              <div class="anim-name">CD Deploys</div>
            </div>
          </div>

          <div class="anim-connector">
            <div class="signal-dot" id="sig-3"></div>
          </div>

          <div class="anim-node" id="anim-4"
            style="--color:#ffa657;--bg:#3a2a1a;
                   --bg-icon:#4a3520;--glow:#ffa65733">
            <div class="anim-icon">&#x2665;</div>
            <div class="anim-label">
              <div class="anim-step-num">Step 5</div>
              <div class="anim-name">Health Check</div>
            </div>
          </div>

        </div>
      </div>
    </div>

    <!-- Items API Demo -->
    <div class="api-demo">
      <h3>Try the Items API live</h3>
      <p class="api-desc">
        POST and GET requests hit the real Flask backend &mdash;
        deployed automatically by the pipeline above.
      </p>
      <div class="api-input-row">
        <input
          class="api-input"
          id="item-input"
          type="text"
          placeholder="Enter an item name..."
          maxlength="60"
        />
        <button class="api-btn" id="add-btn" onclick="addItem()">
          Add
        </button>
      </div>
      <div class="items-list" id="items-list">
        <div class="empty-state" id="empty-msg">
          No items yet &mdash; add one above.
        </div>
      </div>
      <div class="api-status" id="api-status"></div>
    </div>

    <div class="links">
      <a href="https://github.com/ss-bae/cicd-demo" target="_blank">
        GitHub Repo &rarr;
      </a>
      <a href="/items">Items API &rarr;</a>
    </div>
  </div>

  <script>
    // Animation
    const STEPS = 5;
    let current = 0;

    function tick() {
      for (let i = 0; i < STEPS; i++) {
        document.getElementById('anim-' + i).classList.remove('active');
      }
      document.getElementById('anim-' + current).classList.add('active');
      if (current < STEPS - 1) {
        const dot = document.getElementById('sig-' + current);
        dot.classList.remove('go');
        void dot.offsetWidth;
        dot.classList.add('go');
      }
      current = (current + 1) % STEPS;
    }

    tick();
    setInterval(tick, 1600);

    // Items API
    function setStatus(msg, type) {
      const el = document.getElementById('api-status');
      el.textContent = msg;
      el.className = 'api-status ' + (type || '');
    }

    async function loadItems() {
      try {
        const res = await fetch('/items');
        const data = await res.json();
        renderItems(data.items);
      } catch (e) {
        setStatus('Could not reach API', 'err');
      }
    }

    function escHtml(str) {
      return str.replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');
    }

    function renderItems(its) {
      const list = document.getElementById('items-list');
      const empty = document.getElementById('empty-msg');
      list.querySelectorAll('.item-row').forEach(r => r.remove());
      if (!its.length) { empty.style.display = ''; return; }
      empty.style.display = 'none';
      its.forEach(item => {
        const row = document.createElement('div');
        row.className = 'item-row';
        row.innerHTML =
          '<span class="item-id">id: ' + item.id + '</span>' +
          '<span class="item-name">' + escHtml(item.name) + '</span>';
        list.appendChild(row);
      });
    }

    async function addItem() {
      const input = document.getElementById('item-input');
      const btn = document.getElementById('add-btn');
      const name = input.value.trim();
      if (!name) return;
      btn.disabled = true;
      setStatus('Adding...', '');
      try {
        const res = await fetch('/items', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name })
        });
        if (!res.ok) throw new Error('bad response');
        input.value = '';
        setStatus('Added!', 'ok');
        await loadItems();
        setTimeout(() => setStatus('', ''), 2000);
      } catch (e) {
        setStatus('Error adding item', 'err');
      } finally {
        btn.disabled = false;
        input.focus();
      }
    }

    document.getElementById('item-input')
      .addEventListener('keydown', e => {
        if (e.key === 'Enter') addItem();
      });

    loadItems();
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
