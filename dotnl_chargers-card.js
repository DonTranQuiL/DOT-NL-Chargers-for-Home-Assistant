/**
 * DOT-NL Chargers Lovelace card (vanilla JS, not Lit).
 * Custom element tag: dotnl_chargers-card
 */
class DotnlChargersCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._expanded = new Set();
    this._filter = "all";
    this._sort = "distance";
    this._oldDataStr = null;
    this._boundClick = this._onClick.bind(this);
  }

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("Please define an entity (DOT-NL overview sensor)");
    }
    this.config = config;
  }

  set hass(hass) {
    this._hass = hass;
    const entityId = this.config.entity;
    const stateObj = hass.states[entityId];

    if (!stateObj) {
      this.shadowRoot.innerHTML =
        `<ha-card style="padding:16px;color:var(--error-color);">Entity not found: ${this._esc(entityId)}</ha-card>`;
      return;
    }

    const attrs = stateObj.attributes || {};
    const items = attrs.items || [];
    const history = attrs.history || [];
    const counts = attrs.counts || {};
    const closest = attrs.closest || null;
    const cheapest = attrs.cheapest || null;
    const fingerprint = JSON.stringify({
      s: stateObj.state,
      items,
      counts,
      f: this._filter,
      o: this._sort,
      e: [...this._expanded],
      dm: this._isDark(hass),
    });
    if (this._oldDataStr === fingerprint) return;
    this._oldDataStr = fingerprint;

    this._render(stateObj, items, history, counts, closest, cheapest);
  }

  getCardSize() {
    return 6;
  }

  _isDark(hass) {
    try {
      return !!(hass && hass.themes && hass.themes.darkMode);
    } catch (_) {
      return false;
    }
  }

  _esc(str) {
    return String(str == null ? "" : str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  _statusColor(status) {
    switch (status) {
      case "available":
        return "var(--success-color, #4caf50)";
      case "partial":
        return "var(--warning-color, #ff9800)";
      case "occupied":
        return "var(--error-color, #f44336)";
      default:
        return "var(--disabled-text-color, #9e9e9e)";
    }
  }

  _filteredSorted(items) {
    let list = items.slice();
    if (this._filter === "available") {
      list = list.filter((i) => i.status === "available" || (i.available || 0) > 0);
    } else if (this._filter === "occupied") {
      list = list.filter((i) => i.status === "occupied");
    } else if (this._filter === "partial") {
      list = list.filter((i) => i.status === "partial");
    }
    if (this._sort === "distance") {
      list.sort((a, b) => (a.distance_km || 0) - (b.distance_km || 0));
    } else if (this._sort === "power") {
      list.sort((a, b) => (b.max_power_kw || 0) - (a.max_power_kw || 0));
    } else if (this._sort === "price") {
      list.sort((a, b) => {
        const pa = a.energy_price_eur_kwh;
        const pb = b.energy_price_eur_kwh;
        if (pa == null && pb == null) return 0;
        if (pa == null) return 1;
        if (pb == null) return -1;
        return pa - pb;
      });
    } else if (this._sort === "available") {
      list.sort((a, b) => (b.available || 0) - (a.available || 0));
    }
    return list;
  }

  _onClick(ev) {
    const t = ev.target.closest("[data-action]");
    if (!t) return;
    const action = t.getAttribute("data-action");
    if (action === "filter") {
      this._filter = t.getAttribute("data-value");
      this._oldDataStr = null;
      if (this._hass) this.hass = this._hass;
    } else if (action === "sort") {
      this._sort = t.getAttribute("data-value");
      this._oldDataStr = null;
      if (this._hass) this.hass = this._hass;
    } else if (action === "toggle") {
      const id = t.getAttribute("data-id");
      if (this._expanded.has(id)) this._expanded.delete(id);
      else this._expanded.add(id);
      this._oldDataStr = null;
      if (this._hass) this.hass = this._hass;
    }
  }

  _render(stateObj, items, history, counts, closest, cheapest) {
    const dark = this._isDark(this._hass);
    const title = this.config.title || "DOT-NL Chargers";
    const list = this._filteredSorted(items);
    const free = counts.connectors_free != null ? counts.connectors_free : stateObj.state;
    const totalConn = counts.connectors_total || 0;

    const chips = `
      <div class="chips">
        <span class="chip ok">Free ${this._esc(free)}/${this._esc(totalConn)}</span>
        <span class="chip">Avail ${this._esc(counts.available || 0)}</span>
        <span class="chip warn">Partial ${this._esc(counts.partial || 0)}</span>
        <span class="chip err">Occ ${this._esc(counts.occupied || 0)}</span>
      </div>`;

    const closestHtml = closest
      ? `<div class="spotlight"><strong>Closest</strong>: ${this._esc(closest.name)}
         · ${this._esc(closest.distance_km)} km · ${this._esc(closest.available)}/${this._esc(closest.total)}</div>`
      : "";
    const cheapestHtml = cheapest && cheapest.energy_price_eur_kwh != null
      ? `<div class="spotlight"><strong>Cheapest</strong>: €${this._esc(cheapest.energy_price_eur_kwh)}/kWh
         · ${this._esc(cheapest.name)}</div>`
      : "";

    const filters = ["all", "available", "partial", "occupied"]
      .map(
        (f) =>
          `<button class="btn ${this._filter === f ? "active" : ""}" data-action="filter" data-value="${f}">${f}</button>`
      )
      .join("");
    const sorts = [
      ["distance", "Distance"],
      ["available", "Free"],
      ["power", "Power"],
      ["price", "Price"],
    ]
      .map(
        ([v, l]) =>
          `<button class="btn ${this._sort === v ? "active" : ""}" data-action="sort" data-value="${v}">${l}</button>`
      )
      .join("");

    const rows = list
      .map((item) => {
        const id = item.id || "";
        const open = this._expanded.has(id);
        const color = this._statusColor(item.status);
        const price =
          item.energy_price_eur_kwh != null
            ? `€${item.energy_price_eur_kwh}/kWh`
            : "—";
        const detail = open
          ? `<div class="detail">
              <div>${this._esc(item.address)} · ${this._esc(item.operator)}</div>
              <div>Power max ${this._esc(item.max_power_kw)} kW · CPO ${this._esc(item.cpo_id)}</div>
              <div>Updated ${this._esc(item.last_updated || "—")} · Open: ${item.open ? "yes" : "no"}</div>
              <div>Tariffs: ${(item.tariff_ids || []).map((t) => this._esc(t)).join(", ") || "—"}</div>
            </div>`
          : "";
        return `<div class="row" data-action="toggle" data-id="${this._esc(id)}">
          <div class="row-main">
            <span class="dot" style="background:${color}"></span>
            <div class="meta">
              <div class="name">${this._esc(item.name)}</div>
              <div class="sub">${this._esc(item.distance_km)} km · ${this._esc(item.available)}/${this._esc(item.total)} · ${this._esc(price)}</div>
            </div>
            <span class="badge" style="color:${color}">${this._esc(item.status)}</span>
          </div>
          ${detail}
        </div>`;
      })
      .join("");

    const hist = (history || [])
      .slice(0, 8)
      .map(
        (h) =>
          `<li>${this._esc(h.name || h.id)} · ${this._esc(h.status)} · ${this._esc(h.last_updated || "")}</li>`
      )
      .join("");

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        ha-card {
          background: var(--ha-card-background, var(--card-background-color, ${dark ? "#1c1c1c" : "#fff"}));
          color: var(--primary-text-color);
          border-radius: var(--ha-card-border-radius, 12px);
          box-shadow: var(--ha-card-box-shadow, none);
          border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color));
          padding: 16px;
          font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
        }
        .header { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 12px; }
        .title { font-size: 1.15rem; font-weight: 700; }
        .subtitle { font-size: 0.75rem; color: var(--secondary-text-color); margin-top: 2px; }
        .chips { display: flex; flex-wrap: wrap; gap: 6px; }
        .chip { font-size: 0.72rem; padding: 4px 10px; border-radius: 999px; background: var(--secondary-background-color); border: 1px solid var(--divider-color); }
        .chip.ok { color: var(--success-color, #4caf50); }
        .chip.warn { color: var(--warning-color, #ff9800); }
        .chip.err { color: var(--error-color, #f44336); }
        .spotlight { font-size: 0.85rem; margin: 6px 0; color: var(--secondary-text-color); }
        .toolbar { display: flex; flex-wrap: wrap; gap: 6px; margin: 10px 0; }
        .btn { cursor: pointer; border: 1px solid var(--divider-color); background: var(--secondary-background-color); color: var(--primary-text-color); border-radius: 8px; padding: 4px 10px; font-size: 0.75rem; text-transform: capitalize; }
        .btn.active { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: transparent; }
        .list { display: flex; flex-direction: column; gap: 8px; max-height: 420px; overflow: auto; }
        .row { border: 1px solid var(--divider-color); border-radius: 10px; padding: 10px; cursor: pointer; background: var(--secondary-background-color); }
        .row-main { display: flex; align-items: center; gap: 10px; }
        .dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
        .meta { flex: 1; min-width: 0; }
        .name { font-weight: 600; font-size: 0.9rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .sub { font-size: 0.75rem; color: var(--secondary-text-color); }
        .badge { font-size: 0.7rem; font-weight: 700; text-transform: uppercase; }
        .detail { margin-top: 8px; padding-top: 8px; border-top: 1px dashed var(--divider-color); font-size: 0.78rem; color: var(--secondary-text-color); display: grid; gap: 2px; }
        .history { margin-top: 14px; }
        .history h3 { margin: 0 0 6px; font-size: 0.85rem; }
        .history ul { margin: 0; padding-left: 18px; color: var(--secondary-text-color); font-size: 0.75rem; }
        .empty { padding: 16px; text-align: center; color: var(--secondary-text-color); }
        .foot { margin-top: 10px; font-size: 0.65rem; color: var(--disabled-text-color); }
      </style>
      <ha-card>
        <div class="header">
          <div>
            <div class="title">${this._esc(title)}</div>
            <div class="subtitle">${this._esc(stateObj.attributes.friendly_name || stateObj.entity_id)}</div>
          </div>
          ${chips}
        </div>
        ${closestHtml}
        ${cheapestHtml}
        <div class="toolbar">${filters}</div>
        <div class="toolbar">${sorts}</div>
        <div class="list">
          ${rows || '<div class="empty">No charge points match the current filters.</div>'}
        </div>
        <div class="history">
          <h3>Recent history</h3>
          <ul>${hist || "<li>No history yet</li>"}</ul>
        </div>
        <div class="foot">Data © NDW / DOT-NL (AFIR open data) · Card v0.1.0</div>
      </ha-card>
    `;

    this.shadowRoot.removeEventListener("click", this._boundClick);
    this.shadowRoot.addEventListener("click", this._boundClick);
  }
}

if (!customElements.get("dotnl_chargers-card")) {
  customElements.define("dotnl_chargers-card", DotnlChargersCard);
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: "dotnl_chargers-card",
  name: "DOT-NL Chargers Card",
  description: "Overview card for DOT-NL / NDW EV charge points near you.",
  preview: true,
});
