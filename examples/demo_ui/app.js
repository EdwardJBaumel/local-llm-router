const sourceSelect = document.getElementById("source-select");
const presetSelect = document.getElementById("preset-select");
const modelsInput = document.getElementById("models-input");
const presetNote = document.getElementById("preset-note");
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
const hintsLegend = document.getElementById("hints-legend");
const runRouteBtn = document.getElementById("run-route");
const routeResult = document.getElementById("route-result");

const inventoryNote = document.getElementById("inventory-note");
const modelsDirLabel = document.getElementById("models-dir-label");
const diskModelsList = document.getElementById("disk-models-list");
const modelsStatus = document.getElementById("models-status");
const modelsList = document.getElementById("models-list");

const tierStrip = document.getElementById("tier-strip");
const hintMatrix = document.getElementById("hint-matrix");
const guideNote = document.getElementById("guide-note");
const modelCards = document.getElementById("model-cards");
const communityTierLabel = document.getElementById("community-tier-label");
const communitySource = document.getElementById("community-source");
const inventoryAudit = document.getElementById("inventory-audit");

const HINT_EXAMPLES = {
  lookup: "what is JWT in one sentence?",
  explain: "compare session cookies vs JWT for a small SaaS API",
  design: "design a webhook retry strategy with idempotency keys",
  code: "refactor this auth module for unit tests",
  reason: "prove this token expiry policy step by step",
};

let presets = [];
let hintsCatalog = [];

function tierBadge(tier) {
  return `<span class="badge ${tier}">${tier}</span>`;
}

function setStatus(el, text, isError = false) {
  el.textContent = text;
  el.classList.toggle("error", isError);
}

function parseStack(raw) {
  return raw
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);
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
  const community = data.community || {};
  communityTierLabel.textContent = data.vram_tier
    ? `(M tier · ${community.vram_tier_label || data.vram_tier})`
    : "";
  communitySource.textContent = community.source
    ? `${community.source} — installed models merged with community notes below.`
    : "";

  const audit = data.audit || {};
  if (audit.duplicate_tags && audit.duplicate_tags.length) {
    setStatus(
      inventoryAudit,
      `Duplicate copies: ${audit.duplicate_tags.join(", ")} — keep one Ollama folder (${audit.primary_root || "pick one"}).`,
      true
    );
  } else if (audit.primary_root) {
    setStatus(inventoryAudit, `Single library at ${audit.primary_root} — no duplicate tags found.`);
  } else {
    inventoryAudit.textContent = "";
  }

  if (data.missing_recommended && data.missing_recommended.length) {
    inventoryAudit.textContent = [
      inventoryAudit.textContent,
      `Not installed yet: ${data.missing_recommended.join(", ")}.`,
    ]
      .filter(Boolean)
      .join(" ");
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
    : `<p class="placeholder">Set a stack above (at least 2 models, comma-separated).</p>`;

  const routes = data.hint_routes || [];
  hintMatrix.innerHTML = routes.length
    ? routes
        .map(
          (item) => `
      <article class="hint-card">
        <header>
          ${tierBadge(item.tier)}
          <h3>${item.label}</h3>
          <span class="hint-id">${item.hint_id}</span>
        </header>
        <p class="summary">${item.summary}</p>
        <p class="routes-to">Routes to <strong>${item.model}</strong></p>
        <p class="example">"${item.example_prompt}"</p>
      </article>
    `
        )
        .join("")
    : `<p class="placeholder">Could not load hint routes.</p>`;

  const models = data.models || [];
  modelCards.innerHTML = models.length
    ? models
        .map((item) => {
          let stackClass = "dim";
          if (item.status === "recommended") stackClass = "missing";
          else if (item.in_stack) stackClass = "in-stack";
          else if (item.status === "duplicate") stackClass = "duplicate";

          let badge = "";
          if (item.in_stack) badge = `<span class="stack-badge">in stack</span>`;
          else if (item.status === "recommended") badge = `<span class="stack-badge missing-badge">pull me</span>`;
          else if (item.status === "duplicate") badge = `<span class="stack-badge dup-badge">duplicate</span>`;

          const routeHints =
            item.hints && item.hints.length
              ? item.hints.map((h) => `<span class="slot-tag active">${h}</span>`).join("")
              : "";
          const commHints =
            item.community_hints && item.community_hints.length
              ? item.community_hints.map((h) => `<span class="slot-tag community">${h}</span>`).join("")
              : "";
          const slots = (item.tier_slots || [])
            .map((s) => `<span class="slot-tag${item.in_stack ? " active" : ""}">${s}</span>`)
            .join("");
          const vram = item.vram_gb != null ? `${item.vram_gb} GB` : "? GB";
          const family = item.family || "unknown";
          const dupNote =
            item.duplicate_locations && item.duplicate_locations.length > 1
              ? `<span class="community-note">Copied in ${item.duplicate_locations.length} folders — delete extras</span>`
              : "";
          const pullHint =
            item.status === "recommended"
              ? `<span class="community-note">ollama pull ${item.name}</span>`
              : "";
          return `
      <article class="model-card ${stackClass}">
        <h4>${item.name}${badge}</h4>
        <p class="meta">${family}${item.installed ? ` · weight ${item.weight} · ~${vram}` : " · not installed"}${item.vram_ok === false ? " · over VRAM preset" : ""}</p>
        <p class="best-for">${item.best_for}</p>
        ${dupNote}
        ${pullHint}
        <div class="slot-tags">${routeHints}${commHints || slots || `<span class="slot-tag">—</span>`}</div>
      </article>
    `;
        })
        .join("")
    : `<p class="placeholder">No models found. Start server with --models-dir pointing at your Ollama folder.</p>`;

  const parts = [];
  if (data.note) {
    parts.push(data.note);
  } else {
    parts.push(`${data.pool_size || models.length} model(s) scanned · stack has ${(data.stack || []).length}`);
  }
  if (data.fallback) {
    parts.push("Restart demo server for full inventory (old server detected).");
  }
  setStatus(guideNote, parts.join(" "), Boolean(data.fallback || (data.note && data.note.includes("unreachable"))));
}

async function loadGuideFallback() {
  const models = modelsInput.value.trim();
  const stack = parseStack(models);
  if (!stack.length) {
    throw new Error("Enter at least one model in your stack.");
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
        models,
        hint: hint.id,
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

  const cards = stack.map((name) => ({
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
    stack,
    tiers,
    hint_routes: hintRoutes,
    models: cards,
    pool_size: cards.length,
    fallback: true,
  });
}

async function loadGuide() {
  setStatus(guideNote, "Loading guide…");
  const models = encodeURIComponent(modelsInput.value.trim());
  const source = sourceSelect.value;

  try {
    const response = await fetch(`/api/guide?models=${models}&source=${encodeURIComponent(source)}`);
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
  const models = encodeURIComponent(modelsInput.value.trim());
  const live = liveToggle.checked ? "1" : "0";
  const preset = presetSelect.value;
  runCompareBtn.disabled = true;
  setStatus(
    compareStatus,
    liveToggle.checked ? "Running live demo (Ollama)…" : "Running dry demo…"
  );

  try {
    const url = `/api/compare?models=${models}&live=${live}&preset=${encodeURIComponent(preset)}`;
    const response = await fetch(url);
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
      models: modelsInput.value.trim(),
      hint: hintSelect.value || null,
    };
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

function applyPreset(presetId) {
  const preset = presets.find((item) => item.id === presetId);
  if (!preset) {
    return;
  }
  const models =
    preset.resolved_models && preset.resolved_models.length >= 2
      ? preset.resolved_models
      : preset.models;
  modelsInput.value = models.join(",");
  const parts = [preset.description];
  if (preset.warning) {
    parts.push(preset.warning);
  }
  presetNote.textContent = parts.join(" — ");
  loadGuide();
}

async function loadPresets() {
  const source = sourceSelect.value;
  const response = await fetch(`/api/presets?source=${encodeURIComponent(source)}`);
  const data = await response.json();
  presets = data.presets || [];
  if (data.inventory_note) {
    inventoryNote.textContent = data.inventory_note;
    inventoryNote.classList.toggle("error", data.inventory_note.includes("unreachable"));
  }
  presetSelect.innerHTML = presets
    .map((item) => `<option value="${item.id}">${item.label}</option>`)
    .join("");
  const preferred = presets.find((p) => p.id === "mixed_12gb") || presets[0];
  if (preferred) {
    presetSelect.value = preferred.id;
    applyPreset(preferred.id);
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
    option.textContent = `${item.label} → ${item.tier}`;
    hintSelect.appendChild(option);
  });

  hintsLegend.innerHTML = hintsCatalog
    .map(
      (item) => `
      <li>
        ${tierBadge(item.tier)}
        <strong>${item.label}</strong>
        <span class="hint-id">${item.id}</span>
        <p>${item.summary}</p>
      </li>
    `
    )
    .join("");
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
    return true;
  } catch (_err) {
    setStatus(guideNote, "Cannot reach demo API.", true);
    return false;
  }
}

async function boot() {
  await loadHints();
  await loadModels();
  const serverOk = await checkServerVersion();
  await loadPresets();
  await loadGuide();
  await runCompare();
  if (!serverOk) {
    inventoryNote.textContent =
      "Restart: stop the old server, then run examples/demo_ui/start.ps1 from split-stack.";
  }
}

sourceSelect.addEventListener("change", () => {
  loadModels().then(() => loadPresets().then(() => {
    loadGuide();
    runCompare();
  }));
});
presetSelect.addEventListener("change", () => applyPreset(presetSelect.value));
modelsInput.addEventListener("change", () => {
  loadGuide();
  runCompare();
});
modelsInput.addEventListener("blur", () => {
  loadGuide();
  runCompare();
});
runCompareBtn.addEventListener("click", runCompare);
runRouteBtn.addEventListener("click", runRoute);
liveToggle.addEventListener("change", () => {
  if (!liveToggle.checked) {
    setStatus(compareStatus, "Dry demo — shows routing only, no Ollama calls.");
  }
});

boot();
