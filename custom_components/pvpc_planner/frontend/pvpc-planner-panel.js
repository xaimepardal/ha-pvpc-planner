const DOMAINS = ["switch", "light", "fan", "input_boolean", "humidifier"];
const TOP = 6;

const esc = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const pad = (n) => String(n).padStart(2, "0");
const nameOf = (hass, id) => hass.states[id]?.attributes.friendly_name || id;

// Atributos de pvpc_hourly_pricing: price_13h, price_next_day_13h; "_d" = hora repetida en cambio de horario.
function parsePrices(attrs, nextDay) {
  const re = nextDay ? /^price_next_day_(\d{2})h(_d)?$/ : /^price_(\d{2})h(_d)?$/;
  const out = [];
  for (const [k, v] of Object.entries(attrs)) {
    const m = k.match(re);
    if (m && typeof v === "number") out.push({ hour: +m[1], dup: !!m[2], price: v });
  }
  return out.sort((a, b) => a.hour - b.hour || a.dup - b.dup);
}

function classify(prices) {
  const cls = new Map();
  [...prices]
    .sort((a, b) => a.price - b.price)
    .forEach((p, i, arr) => {
      if (i < TOP) cls.set(p, "cheap");
      else if (i >= arr.length - TOP) cls.set(p, "expensive");
    });
  return cls;
}

// Fecha y hora en la zona horaria de HA, no la del navegador.
function nowIn(tz) {
  const p = Object.fromEntries(
    new Intl.DateTimeFormat("en-CA", {
      timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", hourCycle: "h23",
    }).formatToParts(new Date()).map((x) => [x.type, x.value])
  );
  return { date: `${p.year}-${p.month}-${p.day}`, hour: +p.hour };
}

function nextDate(iso) {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + 1);
  return d.toISOString().slice(0, 10);
}

const STYLE = `
:host { display: block; min-height: 100vh; background: var(--primary-background-color); color: var(--primary-text-color);
  font-family: var(--ha-font-family-body, Roboto, sans-serif); }
.toolbar { display: flex; align-items: center; gap: 8px; height: var(--header-height, 56px); padding: 0 12px;
  background: var(--app-header-background-color); color: var(--app-header-text-color, #fff); font-size: 20px; }
.content { max-width: 1100px; margin: 0 auto; padding: 12px; box-sizing: border-box; }
.bar { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; margin-bottom: 12px; }
.tabs { display: flex; gap: 8px; }
.tabs button { padding: 8px 18px; border-radius: 18px; border: 1px solid var(--divider-color); background: var(--card-background-color);
  color: inherit; font: inherit; cursor: pointer; }
.tabs button.on { background: var(--primary-color); border-color: var(--primary-color); color: var(--text-primary-color, #fff); }
.tabs button:disabled { opacity: .45; cursor: default; }
.legend { display: flex; flex-wrap: wrap; gap: 4px 16px; font-size: 14px; color: var(--secondary-text-color); }
.dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; }
.msg:empty { display: none; }
.msg { padding: 12px; border-radius: 8px; background: var(--card-background-color); margin-bottom: 12px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(104px, 1fr)); gap: 6px; }
.cell { background: var(--card-background-color); border: 1px solid var(--divider-color); border-radius: 10px;
  padding: 7px 9px 7px 12px; cursor: pointer; }
.cell.cheap, .cell.expensive { border-color: var(--c); border-left-width: 4px; padding-left: 9px;
  background: color-mix(in srgb, var(--c) 15%, var(--card-background-color, #fff)); }
.cell.cheap { --c: var(--success-color, #43a047); }
.cell.expensive { --c: var(--error-color, #db4437); }
.cell.past { opacity: .4; cursor: default; }
.cell.now { outline: 2px solid var(--primary-color); outline-offset: -1px; }
.cell:focus-visible { outline: 2px solid var(--primary-color); }
.h { font-size: 15px; font-weight: 500; }
.p { font-size: 12px; color: var(--secondary-text-color); font-variant-numeric: tabular-nums; }
.chips { display: flex; flex-wrap: wrap; gap: 3px; margin-top: 4px; }
.chip { max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11px; padding: 1px 6px;
  border-radius: 10px; background: var(--primary-color); color: var(--text-primary-color, #fff); }
.dialog { position: fixed; inset: 0; z-index: 10; display: flex; align-items: center; justify-content: center; padding: 16px;
  background: rgba(0, 0, 0, .45); }
.dialog[hidden] { display: none; }
.box { display: flex; flex-direction: column; width: min(480px, 100%); max-height: 85vh; padding: 20px; box-sizing: border-box;
  border-radius: 16px; background: var(--card-background-color); color: var(--primary-text-color); }
.box h2 { margin: 0; font-size: 20px; font-weight: 500; }
.sub { margin: 2px 0 12px; font-size: 14px; color: var(--secondary-text-color); }
.box input[type=search] { padding: 10px; border-radius: 8px; border: 1px solid var(--divider-color);
  background: var(--primary-background-color); color: inherit; font: inherit; }
.list { flex: 1; overflow: auto; margin: 8px 0; }
.list label[hidden] { display: none; }
.list label { display: flex; align-items: center; gap: 10px; padding: 8px 4px; border-bottom: 1px solid var(--divider-color); cursor: pointer; }
.list small { display: block; font-size: 12px; color: var(--secondary-text-color); }
.err { color: var(--error-color); font-size: 14px; }
.actions { display: flex; align-items: center; gap: 8px; }
.actions span { flex: 1; }
.actions button { padding: 8px 14px; border: none; border-radius: 8px; background: none; color: var(--primary-color); font: inherit; cursor: pointer; }
.actions .save { background: var(--primary-color); color: var(--text-primary-color, #fff); }
`;

class PvpcPlannerPanel extends HTMLElement {
  constructor() {
    super();
    this._schedule = {};
    this._priceEntity = null;
    this._day = null;
    this._last = {};
    const root = this.attachShadow({ mode: "open" });
    root.innerHTML = `<style>${STYLE}</style>
      <div class="toolbar"><ha-menu-button></ha-menu-button><div>PVPC Planner</div></div>
      <div class="content">
        <div class="bar"><div class="tabs"></div><div class="legend"></div></div>
        <div class="msg"></div>
        <div class="grid"></div>
      </div>
      <div class="dialog" hidden></div>`;
    this._$ = (s) => root.querySelector(s);

    this._$(".tabs").addEventListener("click", (e) => {
      const b = e.target.closest("button[data-day]");
      if (b && !b.disabled) {
        this._day = b.dataset.day;
        this._update(true);
      }
    });
    const open = (e) => {
      const c = e.target.closest(".cell");
      if (c && !c.classList.contains("past")) this._openDialog(+c.dataset.hour);
    };
    this._$(".grid").addEventListener("click", open);
    this._$(".grid").addEventListener("keydown", (e) => (e.key === "Enter" || e.key === " ") && open(e));
  }

  set hass(hass) {
    this._hass = hass;
    this._$("ha-menu-button").hass = hass;
    this._subscribe();
    this._update();
  }

  set narrow(narrow) {
    this._$("ha-menu-button").narrow = narrow;
  }

  connectedCallback() {
    this._subscribe();
    this._timer = setInterval(() => this._update(), 30000);
  }

  disconnectedCallback() {
    clearInterval(this._timer);
    this._unsub?.then((u) => u()).catch(() => {});
    this._unsub = null;
  }

  _subscribe() {
    if (this._unsub || !this._hass || !this.isConnected) return;
    this._error = null;
    this._unsub = this._hass.connection.subscribeMessage(
      (msg) => {
        this._schedule = msg.schedule;
        this._priceEntity = msg.price_entity;
        this._update(true);
      },
      { type: "pvpc_planner/subscribe" }
    );
    this._unsub.catch((err) => {
      this._error = err.message || String(err);
      this._update(true);
    });
  }

  // Solo repinta si cambian precios, horario o la hora actual: hass cambia con cualquier estado.
  _update(force = false) {
    const hass = this._hass;
    if (!hass) return;
    const stateObj = this._priceEntity && hass.states[this._priceEntity];
    const now = nowIn(hass.config.time_zone);
    const l = this._last;
    if (!force && l.state === stateObj && l.date === now.date && l.hour === now.hour) return;
    this._last = { state: stateObj, date: now.date, hour: now.hour };

    const msg = this._$(".msg");
    const grid = this._$(".grid");
    const fail = (text) => {
      msg.textContent = text;
      grid.innerHTML = "";
    };
    if (this._error) return fail(`Error: ${this._error}`);
    if (!this._priceEntity) return fail("Cargando…");
    if (!stateObj) return fail(`No se encuentra ${this._priceEntity}. Revisa la integración PVPC.`);

    const today = parsePrices(stateObj.attributes, false);
    const tomorrow = parsePrices(stateObj.attributes, true);
    if (this._day === null || (this._day === "tomorrow" && !tomorrow.length)) {
      this._day = tomorrow.length ? "tomorrow" : "today";
    }
    const isToday = this._day === "today";
    const prices = isToday ? today : tomorrow;
    this._date = isToday ? now.date : nextDate(now.date);

    this._$(".tabs").innerHTML = `
      <button data-day="today" class="${isToday ? "on" : ""}">Hoy</button>
      <button data-day="tomorrow" class="${isToday ? "" : "on"}" ${tomorrow.length ? "" : 'disabled title="Se publican hacia las 20:30"'}>Mañana</button>`;
    const unit = stateObj.attributes.unit_of_measurement || "€/kWh";
    this._$(".legend").innerHTML = `
      <span><i class="dot" style="background:var(--success-color,#43a047)"></i>${TOP} más baratas</span>
      <span><i class="dot" style="background:var(--error-color,#db4437)"></i>${TOP} más caras</span>
      <span>${esc(unit)}</span>`;

    if (!prices.length) return fail("Sin precios para este día.");
    msg.textContent = "";

    const cls = classify(prices);
    const slots = this._schedule[this._date] || {};
    const fmt = new Intl.NumberFormat(hass.locale?.language || hass.language, {
      minimumFractionDigits: 4,
      maximumFractionDigits: 4,
    });
    grid.innerHTML = prices
      .map((p) => {
        const past = isToday && p.hour < now.hour;
        const current = isToday && p.hour === now.hour;
        const ents = slots[p.hour] || [];
        return `<div class="cell ${cls.get(p) || ""} ${past ? "past" : ""} ${current ? "now" : ""}"
            data-hour="${p.hour}" role="button" tabindex="${past ? -1 : 0}">
          <div class="h">${pad(p.hour)}:00${p.dup ? " (bis)" : ""}</div>
          <div class="p">${fmt.format(p.price)}</div>
          <div class="chips">${ents.map((e) => `<span class="chip">${esc(nameOf(hass, e))}</span>`).join("")}</div>
        </div>`;
      })
      .join("");
  }

  _openDialog(hour) {
    const hass = this._hass;
    const date = this._date;
    const selected = new Set(this._schedule[date]?.[hour] || []);
    const ents = Object.keys(hass.states)
      .filter((id) => {
        const reg = hass.entities?.[id];
        return DOMAINS.includes(id.split(".")[0]) && !reg?.hidden && !reg?.entity_category;
      })
      .map((id) => ({ id, name: nameOf(hass, id) }))
      .sort((a, b) => a.name.localeCompare(b.name));
    const dayLabel = new Date(`${date}T12:00:00Z`).toLocaleDateString(hass.language, {
      weekday: "long", day: "numeric", month: "long", timeZone: "UTC",
    });

    const dlg = this._$(".dialog");
    dlg.innerHTML = `<div class="box" role="dialog" aria-modal="true">
      <h2>Encender ${pad(hour)}:00–${pad((hour + 1) % 24)}:00</h2>
      <div class="sub">${esc(dayLabel)}</div>
      <input type="search" placeholder="Buscar dispositivo">
      <div class="list">${
        ents.map((e) => `<label data-q="${esc(`${e.name} ${e.id}`.toLowerCase())}">
          <input type="checkbox" value="${esc(e.id)}" ${selected.has(e.id) ? "checked" : ""}>
          <span>${esc(e.name)}<small>${esc(e.id)}</small></span></label>`).join("")
        || "<p>No hay dispositivos de encendido/apagado.</p>"
      }</div>
      <div class="err"></div>
      <div class="actions"><button class="clear">Quitar todos</button><span></span>
        <button class="cancel">Cancelar</button><button class="save">Guardar</button></div>
    </div>`;
    dlg.hidden = false;

    const close = () => {
      dlg.hidden = true;
      dlg.innerHTML = "";
      document.removeEventListener("keydown", onKey);
    };
    const onKey = (e) => e.key === "Escape" && close();
    document.addEventListener("keydown", onKey);
    dlg.onclick = (e) => {
      if (e.target === dlg) close();
    };

    const boxes = () => [...dlg.querySelectorAll("input[type=checkbox]")];
    dlg.querySelector("input[type=search]").addEventListener("input", (e) => {
      const q = e.target.value.trim().toLowerCase();
      dlg.querySelectorAll("label").forEach((l) => (l.hidden = !l.dataset.q.includes(q)));
    });
    dlg.querySelector(".clear").onclick = () => boxes().forEach((b) => (b.checked = false));
    dlg.querySelector(".cancel").onclick = close;
    dlg.querySelector(".save").onclick = async () => {
      try {
        await hass.callWS({
          type: "pvpc_planner/set",
          date,
          hour,
          entity_ids: boxes().filter((b) => b.checked).map((b) => b.value),
        });
        close();
      } catch (err) {
        dlg.querySelector(".err").textContent = err.message || String(err);
      }
    };
  }
}

customElements.define("pvpc-planner-panel", PvpcPlannerPanel);
