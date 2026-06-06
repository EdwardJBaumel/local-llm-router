const vramSelect = document.getElementById("vram-select");
const quantSelect = document.getElementById("quant-select");
const sourceSelect = document.getElementById("source-select");
const stackChips = document.getElementById("stack-chips");
const stackNote = document.getElementById("stack-note");
const customStackToggle = document.getElementById("custom-stack-toggle");
const customStackField = document.getElementById("custom-stack-field");
const modelsInput = document.getElementById("models-input");
const liveToggle = document.getElementById("live-toggle");
const runCompareBtn = document.getElementById("run-compare");
const compareStatus = document.getElementById("compare-status");
const summaryStrip = document.getElementById("summary-strip");
const stepGrid = document.getElementById("step-grid");
const latencySection = document.getElementById("latency-section");
const latencyBars = document.getElementById("latency-bars");
const latencyTotals = document.getElementById("latency-totals");

const promptInput = document.getElementById("prompt-input");
const hintSelect = document.getElementById("hint-select");
const runRouteBtn = document.getElementById("run-route");
const routeResult = document.getElementById("route-result");

const inventoryNote = document.getElementById("inventory-note");
const modelsDirLabel = document.getElementById("models-dir-label");
const diskModelsList = document.getElementById("disk-models-list");
const modelsStatus = document.getElementById("models-status");
const modelsList = document.getElementById("models-list");

const tierStrip = document.getElementById("tier-strip");
const hintTableWrap = document.getElementById("hint-table-wrap");
const guideNote = document.getElementById("guide-note");
const modelCards = document.getElementById("model-cards");
const inventoryAudit = document.getElementById("inventory-audit");

const HINT_EXAMPLES = {
  lookup: "what is JWT in one sentence?",
  explain: "compare session cookies vs JWT for a small SaaS API",
  design: "design a webhook retry strategy with idempotency keys",
  code: "refactor this auth module for unit tests",
  reason: "prove this token expiry policy step by step",
};

let hintsCatalog = [];
let stackState = {
  vram_gb: 16,
  quant: "qat",
  models: [],
  resolved_models: [],
  missing_models: [],
  description: "",
  notes: [],
  warning: null,
};

function tierBadge(tier) {
  return `<span class="badge ${tier}">${tier}</span>`;
}

function setStatus(el, text, isError = false) {
  el.textContent = text;
  el.classList.toggle("error", isError);
}

function activeModels() {
  if (customStackToggle.checked) {
    return modelsInput.value
      .split(",")
      .map((part) => part.trim())
      .filter(Boolean);
  }
  return stackState.resolved_models.length >= 2
    ? stackState.resolved_models
    : stackState.models;
}

function stackQueryParams() {
  const params = new URLSearchParams({
    vram_gb: String(vramSelect.value),
    quant: quantSelect.value,
    source: sourceSelect.value,
  });
  if (customStackToggle.checked && modelsInput.value.trim()) {
    params.set("models", modelsInput.value.trim());
  }
  return params;
}

function renderStackChips(data) {
  const recommended = data.models || [];
  const resolved = data.resolved_models || recommended;
  const missing = new Set(data.missing_models || []);
  const show = resolved.length >= 2 ? resolved : recommended;

  stackChips.innerHTML = show.length
    ? show
        .map(
          (name) =>
            `<span class="stack-chip${missing.has(name) ? " missing" : ""}" title="${
              missing.has(name) ? "Not found in inventory" : "In your inventory"
            }">${name}</span>`
        )
        .join("")
    : `<span class="placeholder muted">Pick VRAM and quant above.</span>`;

  const parts = [];
  if (data.description) {
    parts.push(data.description);
  }
  if (data.notes && data.notes.length) {
    parts.push(data.notes.join(" "));
  }
  if (data.warning) {
    parts.push(data.warning);
  }
  if (data.inventory_note) {
    parts.push(data.inventory_note);
  }
  stackNote.textContent = parts.join(" — ");
  stackNote.classList.toggle("error", Boolean(data.warning && data.warning.includes("unreachable")));
}

function renderCompare(data) {
  const summary = data.summary;
  summaryStrip.classList.remove("hidden");
  summaryStrip.innerHTML = `
    <strong>split-stack:</strong> ${summary.routed_models_used} models,
    ${summary.steps_avoided_largest}/${summary.total_steps} steps avoided largest
    &nbsp;|&nbsp;
    <strong>baseline:</strong> always ${summary.baseline_model}
  `;

  stepGrid.innerHTML = data.rows
    .map(
      (row) => `
      <article class="step-card">
        <h3>${row.step.replace(/_/g, " ")}</h3>
        ${tierBadge(row.routed_tier)}
        <div class="model-row routed">
          <span class="label">Routed</span>
          <span class="value">${row.routed_model}</span>
        </div>
        <div class="model-row baseline">
          <span class="label">Baseline</span>
          <span class="value">${row.baseline_model}</span>
        </div>
      </article>
    `
    )
    .join("");

  const hasLatency = data.rows.some((row) => row.routed_latency_ms != null);
  if (hasLatency) {
    latencySection.classList.remove("hidden");
    const maxMs = Math.max(
      ...data.rows.flatMap((row) => [row.routed_latency_ms || 0, row.baseline_latency_ms || 0]),
      1
    );
    latencyBars.innerHTML = data.rows
      .map((row) => {
        const routedPct = ((row.routed_latency_ms || 0) / maxMs) * 100;
        const baselinePct = ((row.baseline_latency_ms || 0) / maxMs) * 100;
        return `
        <div class="latency-row">
          <div class="step-label">${row.step.replace(/_/g, " ")}</div>
          <div class="bar-track">
            <div class="bar routed" style="width:${routedPct}%" title="routed ${row.routed_latency_ms} ms"></div>
            <div class="bar baseline" style="width:${baselinePct}%" title="baseline ${row.baseline_latency_ms} ms"></div>
          </div>
        </div>
      `;
      })
      .join("");
    latencyTotals.textContent = `Total: routed ${summary.routed_total_latency_ms} ms vs baseline ${summary.baseline_total_latency_ms} ms`;
  } else {
    latencySection.classList.add("hidden");
  }
}

function renderGuide(data) {
  const audit = data.audit || {};
  if (audit.duplicate_tags && audit.duplicate_tags.length) {
    setStatus(
      inventoryAudit,
      `Duplicate copies: ${audit.duplicate_tags.join(", ")} — keep one Ollama folder.`,
      true
    );
  } else if (data.missing_recommended && data.missing_recommended.length) {
    setStatus(inventoryAudit, `Not installed: ${data.missing_recommended.join(", ")}.`);
  } else {
    inventoryAudit.textContent = audit.primary_root
      ? `Models folder: ${audit.primary_root}`
      : "";
  }

  const tierOrder = ["simple", "medium", "complex", "reasoning", "code"];
  const tierEntries = tierOrder.filter((key) => data.tiers && data.tiers[key]);

  tierStrip.innerHTML = tierEntries.length
    ? tierEntries
        .map(
          (key) => `
      <div class="tier-chip ${key}">
        <span class="tier-name">${key}</span>
        <span class="model-name">${data.tiers[key]}</span>
      </div>
    `
        )
        .join("")
    : `<p class="placeholder">Need at least two models in your stack.</p>`;

  const routes = data.hint_routes || [];
  hintTableWrap.innerHTML = routes.length
    ? `
    <table class="hint-table">
      <thead>
        <tr>
          <th>Hint</th>
          <th>Good for</th>
          <th>Tier</th>
          <th>Model</th>
          <th>Example prompt</th>
        </tr>
      </thead>
      <tbody>
        ${routes
          .map(
            (item) => `
          <tr>
            <td><code class="hint-id">${item.hint_id}</code></td>
            <td>${item.label}<br><span class="muted" style="font-size:0.78rem">${item.summary}</span></td>
            <td>${tierBadge(item.tier)}</td>
            <td class="model-cell">${item.model}</td>
            <td class="example-cell">${item.example_prompt}</td>
          </tr>
        `
          )
          .join("")}
      </tbody>
    </table>
  `
    : `<p class="placeholder">Could not load hint routes — check your stack has 2+ models.</p>`;

  const models = (data.models || []).filter((item) => item.installed || item.in_stack);
  modelCards.innerHTML = models.length
    ? models
        .slice(0, 24)
        .map(
          (item) => `
      <article class="model-card${item.in_stack ? " in-stack" : ""}">
        <h4>${item.name}</h4>
        <p class="meta">${item.family || "model"}${item.in_stack ? " · in active stack" : ""}</p>
        <p class="best-for">${item.best_for || ""}</p>
      </article>
    `
        )
        .join("")
    : `<p class="placeholder muted">Expand this section after pointing the server at your Ollama folder.</p>`;

  const parts = [];
  if (data.vram_gb) {
    parts.push(`${data.vram_gb} GB · ${data.quant || "default"}`);
  }
  if (data.note) {
    parts.push(data.note);
  } else {
    parts.push(`Stack: ${(data.stack || []).join(", ")}`);
  }
  if (data.fallback) {
    parts.push("Restart demo server for full inventory API.");
  }
  setStatus(guideNote, parts.join(" · "), Boolean(data.fallback));
}

async function loadStackOptions() {
  const response = await fetch("/api/stack-options");
  const data = await response.json();
  vramSelect.innerHTML = (data.vram_options || [])
    .map((item) => `<option value="${item.gb}">${item.label}</option>`)
    .join("");
  quantSelect.innerHTML = (data.quant_options || [])
    .map((item) => `<option value="${item.id}">${item.label}</option>`)
    .join("");
  vramSelect.value = String(data.default_vram_gb || 16);
  quantSelect.value = data.default_quant || "qat";
}

async function refreshStack() {
  const params = stackQueryParams();
  const response = await fetch(`/api/stack?${params.toString()}`);
  const data = await response.json();
  if (!data.ready) {
    stackNote.textContent = data.error || "Could not load stack.";
    return;
  }
  stackState = {
    vram_gb: data.vram_gb,
    quant: data.quant,
    models: data.models || [],
    resolved_models: data.resolved_models || [],
    missing_models: data.missing_models || [],
    description: data.description || "",
    notes: data.notes || [],
    warning: data.warning || null,
  };
  if (!customStackToggle.checked) {
    modelsInput.value = (stackState.resolved_models.length >= 2
      ? stackState.resolved_models
      : stackState.models
    ).join(",");
  }
  renderStackChips(data);
  if (data.inventory_note && !inventoryNote.textContent) {
    inventoryNote.textContent = data.inventory_note;
    inventoryNote.classList.toggle("error", data.inventory_note.includes("unreachable"));
  }
}

async function loadGuideFallback() {
  const models = activeModels();
  if (models.length < 1) {
    throw new Error("Need at least one model in your stack.");
  }

  const hints = hintsCatalog.length ? hintsCatalog : (await (await fetch("/api/hints")).json()).hints || [];
  const hintRoutes = [];
  const tiers = {};

  for (const hint of hints) {
    const response = await fetch("/api/route", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: HINT_EXAMPLES[hint.id] || hint.summary,
        models: models.join(","),
        hint: hint.id,
        vram_gb: vramSelect.value,
        quant: quantSelect.value,
        source: sourceSelect.value,
      }),
    });
    const data = await response.json();
    if (!data.ready) {
      continue;
    }
    hintRoutes.push({
      hint_id: hint.id,
      label: hint.label,
      summary: hint.summary,
      tier: data.tier,
      model: data.model,
      example_prompt: HINT_EXAMPLES[hint.id] || hint.summary,
    });
    tiers[data.tier] = data.model;
  }

  const cards = models.map((name) => ({
    name,
    family: name.split(":")[0],
    weight: 0,
    vram_gb: null,
    vram_ok: true,
    in_stack: true,
    hints: hintRoutes.filter((item) => item.model === name).map((item) => item.hint_id),
    tier_slots: Object.entries(tiers)
      .filter(([, model]) => model === name)
      .map(([tier]) => tier),
    best_for: "In your active stack",
  }));

  renderGuide({
    ready: true,
    stack: models,
    tiers,
    hint_routes: hintRoutes,
    models: cards,
    pool_size: cards.length,
    vram_gb: Number(vramSelect.value),
    quant: quantSelect.value,
    fallback: true,
  });
}

async function loadGuide() {
  setStatus(guideNote, "Loading guide…");
  const params = stackQueryParams();

  try {
    const response = await fetch(`/api/guide?${params.toString()}`);
    if (response.status === 404) {
      await loadGuideFallback();
      return;
    }
    if (!response.ok) {
      throw new Error(`Guide API returned ${response.status}`);
    }
    const data = await response.json();
    if (!data.ready) {
      throw new Error(data.error || "Guide failed");
    }
    renderGuide(data);
  } catch (err) {
    try {
      await loadGuideFallback();
      setStatus(guideNote, `Showing stack-only guide (${err}).`, true);
    } catch (fallbackErr) {
      renderGuide({ tiers: {}, hint_routes: [], models: [], note: String(fallbackErr) });
    }
  }
}

async function runCompare() {
  const params = stackQueryParams();
  params.set("live", liveToggle.checked ? "1" : "0");
  runCompareBtn.disabled = true;
  setStatus(
    compareStatus,
    liveToggle.checked ? "Running live demo (Ollama)…" : "Running dry demo…"
  );

  try {
    const response = await fetch(`/api/compare?${params.toString()}`);
    const data = await response.json();
    if (!data.ready) {
      setStatus(compareStatus, data.error || "Demo failed", true);
      stepGrid.innerHTML = `<p class="placeholder error">${data.error || "Demo failed"}</p>`;
      return;
    }
    renderCompare(data);
    setStatus(
      compareStatus,
      liveToggle.checked
        ? "Live demo complete."
        : "Dry demo — shows routing only, no Ollama calls."
    );
  } catch (err) {
    setStatus(compareStatus, String(err), true);
    stepGrid.innerHTML = `<p class="placeholder error">${err}</p>`;
  } finally {
    runCompareBtn.disabled = false;
  }
}

async function runRoute() {
  const prompt = promptInput.value.trim();
  if (!prompt) {
    routeResult.classList.remove("hidden");
    routeResult.innerHTML = `<span class="status error">Enter a prompt first.</span>`;
    return;
  }

  runRouteBtn.disabled = true;
  try {
    const body = {
      prompt,
      hint: hintSelect.value || null,
      vram_gb: Number(vramSelect.value),
      quant: quantSelect.value,
      source: sourceSelect.value,
    };
    if (customStackToggle.checked) {
      body.models = modelsInput.value.trim();
    }
    const response = await fetch("/api/route", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await response.json();
    routeResult.classList.remove("hidden");
    if (!data.ready) {
      routeResult.innerHTML = `<span class="status error">${data.error || "Routing failed"}</span>`;
      return;
    }
    const hintLabel = data.hint_label ? `${data.hint_label} · ` : "";
    routeResult.innerHTML = `
      ${tierBadge(data.tier)}
      <strong style="margin-left:0.5rem">${data.model}</strong>
      <span class="status muted" style="display:block;margin-top:0.5rem">${hintLabel}tier ${data.tier}</span>
    `;
  } catch (err) {
    routeResult.classList.remove("hidden");
    routeResult.innerHTML = `<span class="status error">${err}</span>`;
  } finally {
    runRouteBtn.disabled = false;
  }
}

async function loadHints() {
  const response = await fetch("/api/hints");
  const data = await response.json();
  hintsCatalog = data.hints || [];

  hintSelect.innerHTML = `<option value="">auto (text heuristics)</option>`;
  hintsCatalog.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.id;
    option.textContent = `${item.id} — ${item.label}`;
    hintSelect.appendChild(option);
  });
}

async function loadModels() {
  try {
    const response = await fetch("/api/models");
    const data = await response.json();
    const disk = data.disk_models || [];
    const api = data.api_models || [];
    const roots = data.manifest_roots || [];

    if (data.models_dir) {
      modelsDirLabel.textContent = `Folder: ${data.models_dir}`;
    } else if (roots.length) {
      modelsDirLabel.textContent = `Folders: ${roots.join("; ")}`;
    } else {
      modelsDirLabel.textContent = "Folder: not found — use start.ps1 or --models-dir";
    }

    diskModelsList.innerHTML = disk.length
      ? disk.map((name) => `<li>${name}</li>`).join("")
      : `<li class="muted">None found. Point server at your Ollama models folder (e.g. <code>~/.ollama/models</code> or set <code>--models-dir</code>).</li>`;

    if (!api.length) {
      setStatus(
        modelsStatus,
        "API: no tags (dry routing still works; live needs Ollama on that folder)",
        true
      );
    } else {
      setStatus(modelsStatus, `API: ${api.length} tag(s)`);
    }
    modelsList.innerHTML = api.length
      ? api.map((name) => `<li>${name}</li>`).join("")
      : `<li class="muted">—</li>`;

    if (data.note && !inventoryNote.textContent) {
      inventoryNote.textContent = data.note;
    }
  } catch (err) {
    setStatus(modelsStatus, String(err), true);
  }
}

async function checkServerVersion() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) {
      setStatus(
        guideNote,
        "Demo server is outdated (restart with examples/demo_ui/start.ps1). Loading stack-only guide…",
        true
      );
      return false;
    }
    const data = await response.json();
    if (!data.version || data.version < 3) {
      setStatus(
        guideNote,
        "Restart demo server for VRAM + quant stack bar (version 3+).",
        true
      );
      return false;
    }
    return true;
  } catch (_err) {
    setStatus(guideNote, "Cannot reach demo API.", true);
    return false;
  }
}

async function reloadAll() {
  await refreshStack();
  await loadGuide();
  await runCompare();
}

async function boot() {
  await loadHints();
  await loadModels();
  const serverOk = await checkServerVersion();
  await loadStackOptions();
  await reloadAll();
  if (!serverOk) {
    inventoryNote.textContent =
      "Restart: stop the old server, then run examples/demo_ui/start.ps1 from split-stack.";
  }
}

function onStackControlsChange() {
  reloadAll();
}

vramSelect.addEventListener("change", onStackControlsChange);
quantSelect.addEventListener("change", onStackControlsChange);
sourceSelect.addEventListener("change", () => {
  loadModels().then(reloadAll);
});
customStackToggle.addEventListener("change", () => {
  customStackField.classList.toggle("hidden", !customStackToggle.checked);
  if (!customStackToggle.checked) {
    modelsInput.value = (stackState.resolved_models.length >= 2
      ? stackState.resolved_models
      : stackState.models
    ).join(",");
  }
  reloadAll();
});
modelsInput.addEventListener("change", reloadAll);
modelsInput.addEventListener("blur", reloadAll);
runCompareBtn.addEventListener("click", runCompare);
runRouteBtn.addEventListener("click", runRoute);
liveToggle.addEventListener("change", () => {
  if (!liveToggle.checked) {
    setStatus(compareStatus, "Dry demo — shows routing only, no Ollama calls.");
  }
});

boot();
