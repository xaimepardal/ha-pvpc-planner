const DOMAINS = ["switch", "light", "fan", "input_boolean", "humidifier"];
const TOP = 6;
const GROUP = "group:";

const ICONS = [
  "mdi:flash", "mdi:power-socket-eu", "mdi:water-boiler", "mdi:washing-machine", "mdi:tumble-dryer",
  "mdi:dishwasher", "mdi:radiator", "mdi:heat-pump", "mdi:air-conditioner", "mdi:fan", "mdi:air-humidifier",
  "mdi:lightbulb-group", "mdi:lamp", "mdi:ev-station", "mdi:car-electric", "mdi:battery-charging",
  "mdi:water-pump", "mdi:pool", "mdi:sprinkler", "mdi:fridge", "mdi:stove", "mdi:microwave",
  "mdi:coffee-maker", "mdi:kettle", "mdi:television", "mdi:desktop-tower", "mdi:router-wireless",
  "mdi:robot-vacuum", "mdi:home", "mdi:sofa", "mdi:bed", "mdi:garage", "mdi:tools", "mdi:solar-power",
];

// Claves que falten en un idioma caen a inglés.
const STRINGS = {
  en: {
    loading: "Loading…",
    missing_sensor: "{entity} not found. Check the PVPC integration.",
    today: "Today",
    tomorrow: "Tomorrow",
    tomorrow_pending: "Published around 20:30",
    cheapest: "{n} cheapest",
    priciest: "{n} most expensive",
    no_prices: "No prices for this day.",
    repeated: "(2nd)",
    turn_on: "Turn on {from}–{to}",
    search: "Search device",
    no_devices: "No on/off devices.",
    clear: "Clear all",
    cancel: "Cancel",
    save: "Save",
    err_unauthorized: "You are not allowed to control some of these devices.",
    err_invalid_slot: "That hour can no longer be scheduled.",
    err_not_loaded: "PVPC Planner is not loaded.",
    settings_title: "Settings",
    settings_devices: "Devices",
    settings_groups: "Groups",
    settings_close: "Close",
    hidden_help: "Choose which devices appear when scheduling an hour.",
    hidden_count: "{shown} of {total} visible",
    hidden_show_all: "Show all",
    hidden_hide_all: "Hide all",
    group_help: "A group turns several devices on and off together.",
    group_new: "New group",
    group_empty: "No groups yet.",
    group_count: "{n} devices",
    group_count_one: "1 device",
    group_name: "Name",
    group_icon: "Icon",
    group_edit: "Edit",
    group_delete: "Delete",
    group_confirm_delete: "Delete?",
    group_need_name: "Enter a name",
    group_need_devices: "Pick at least one device",
    err_not_found: "This group no longer exists.",
    err_invalid_group: "Too many groups.",
  },
  es: {
    loading: "Cargando…",
    missing_sensor: "No se encuentra {entity}. Revisa la integración PVPC.",
    today: "Hoy",
    tomorrow: "Mañana",
    tomorrow_pending: "Se publican hacia las 20:30",
    cheapest: "{n} más baratas",
    priciest: "{n} más caras",
    no_prices: "Sin precios para este día.",
    repeated: "(bis)",
    turn_on: "Encender {from}–{to}",
    search: "Buscar dispositivo",
    no_devices: "No hay dispositivos de encendido/apagado.",
    clear: "Quitar todos",
    cancel: "Cancelar",
    save: "Guardar",
    err_unauthorized: "No tienes permiso para controlar alguno de estos dispositivos.",
    err_invalid_slot: "Ya no se puede programar esa hora.",
    err_not_loaded: "PVPC Planner no está cargado.",
    settings_title: "Ajustes",
    settings_devices: "Dispositivos",
    settings_groups: "Grupos",
    settings_close: "Cerrar",
    hidden_help: "Elige qué dispositivos aparecen al programar una hora.",
    hidden_count: "{shown} de {total} visibles",
    hidden_show_all: "Mostrar todos",
    hidden_hide_all: "Ocultar todos",
    group_help: "Un grupo enciende y apaga varios dispositivos a la vez.",
    group_new: "Nuevo grupo",
    group_empty: "Aún no hay grupos.",
    group_count: "{n} dispositivos",
    group_count_one: "1 dispositivo",
    group_name: "Nombre",
    group_icon: "Icono",
    group_edit: "Editar",
    group_delete: "Borrar",
    group_confirm_delete: "¿Borrar?",
    group_need_name: "Escribe un nombre",
    group_need_devices: "Elige al menos un dispositivo",
    err_not_found: "Ese grupo ya no existe.",
    err_invalid_group: "Demasiados grupos.",
  },
  gl: {
    loading: "Cargando…",
    missing_sensor: "Non se atopa {entity}. Revisa a integración PVPC.",
    today: "Hoxe",
    tomorrow: "Mañá",
    tomorrow_pending: "Publícanse arredor das 20:30",
    cheapest: "{n} máis baratas",
    priciest: "{n} máis caras",
    no_prices: "Sen prezos para este día.",
    repeated: "(bis)",
    turn_on: "Acender {from}–{to}",
    search: "Buscar dispositivo",
    no_devices: "Non hai dispositivos de acendido/apagado.",
    clear: "Quitar todos",
    cancel: "Cancelar",
    save: "Gardar",
    err_unauthorized: "Non tes permiso para controlar algún destes dispositivos.",
    err_invalid_slot: "Xa non se pode programar esa hora.",
    err_not_loaded: "PVPC Planner non está cargado.",
    settings_title: "Axustes",
    settings_devices: "Dispositivos",
    settings_groups: "Grupos",
    settings_close: "Pechar",
    hidden_help: "Escolle que dispositivos aparecen ao programar unha hora.",
    hidden_count: "{shown} de {total} visibles",
    hidden_show_all: "Amosar todos",
    hidden_hide_all: "Ocultar todos",
    group_help: "Un grupo acende e apaga varios dispositivos á vez.",
    group_new: "Novo grupo",
    group_empty: "Aínda non hai grupos.",
    group_count: "{n} dispositivos",
    group_count_one: "1 dispositivo",
    group_name: "Nome",
    group_icon: "Icona",
    group_edit: "Editar",
    group_delete: "Borrar",
    group_confirm_delete: "Borrar?",
    group_need_name: "Escribe un nome",
    group_need_devices: "Escolle polo menos un dispositivo",
    err_not_found: "Ese grupo xa non existe.",
    err_invalid_group: "Demasiados grupos.",
  },
};

const langOf = (hass) => hass.locale?.language || hass.language || "en";

// Devuelve texto sin escapar: los parámetros externos se escapan al llamar.
function translator(lang) {
  const table = STRINGS[lang] || STRINGS[lang.split("-")[0]] || STRINGS.en;
  return (key, params = {}) =>
    (table[key] ?? STRINGS.en[key]).replace(/\{(\w+)\}/g, (_, k) => params[k]);
}

const esc = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const pad = (n) => String(n).padStart(2, "0");
const nameOf = (hass, id) => hass.states[id]?.attributes.friendly_name || id;

// Dispositivos de encendido/apagado que HA no oculta.
function devicesOf(hass) {
  return Object.keys(hass.states)
    .filter((id) => {
      const reg = hass.entities?.[id];
      return DOMAINS.includes(id.split(".")[0]) && !reg?.hidden && !reg?.entity_category;
    })
    .map((id) => ({ id, name: nameOf(hass, id) }))
    .sort((a, b) => a.name.localeCompare(b.name));
}

const deviceRow = (e, checked, cls = "") => `<label class="${cls}" data-q="${esc(`${e.name} ${e.id}`.toLowerCase())}">
  <input type="checkbox" class="${cls}" value="${esc(e.id)}" ${checked ? "checked" : ""}>
  <span>${esc(e.name)}<small>${esc(e.id)}</small></span></label>`;

function filterOnInput(input, root) {
  input.addEventListener("input", () => {
    const q = input.value.trim().toLowerCase();
    root.querySelectorAll("label[data-q]").forEach((l) => (l.hidden = !l.dataset.q.includes(q)));
  });
}

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
.toolbar .title { flex: 1; }
.settings-btn { display: inline-flex; align-items: center; gap: 8px; padding: 7px 16px 7px 12px; border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, .35); background: rgba(255, 255, 255, .16); color: inherit; font: inherit;
  font-size: 15px; font-weight: 500; cursor: pointer; transition: background .2s, transform .2s; }
.settings-btn:hover { background: rgba(255, 255, 255, .28); }
.settings-btn:hover ha-icon { transform: rotate(60deg); }
.settings-btn ha-icon { transition: transform .3s; --mdc-icon-size: 20px; }
.settings-btn:focus-visible { outline: 2px solid currentColor; outline-offset: 2px; }
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
.chip ha-icon { --mdc-icon-size: 12px; vertical-align: -1px; margin-right: 2px; }
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
.list label.group ha-icon { color: var(--primary-color); }
.section { margin: 10px 0 2px; font-size: 12px; font-weight: 500; letter-spacing: .05em; text-transform: uppercase;
  color: var(--secondary-text-color); }
.err { color: var(--error-color); font-size: 14px; }
.err:empty { display: none; }
.box.wide { width: min(560px, 100%); }
.box .tabs { margin: 12px 0; }
.help { margin: 0 0 10px; font-size: 14px; color: var(--secondary-text-color); }
.row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.row input[type=search], .row input[type=text] { flex: 1; min-width: 0; }
.box input[type=text] { padding: 10px; border-radius: 8px; border: 1px solid var(--divider-color);
  background: var(--primary-background-color); color: inherit; font: inherit; }
.tools { display: flex; align-items: center; gap: 8px; margin-top: 8px; font-size: 14px; color: var(--secondary-text-color); }
.tools span { flex: 1; }
.tools button, .link { padding: 4px 8px; border: none; background: none; color: var(--primary-color); font: inherit; cursor: pointer; }
label.switch { flex-direction: row-reverse; justify-content: space-between; }
input.switch { appearance: none; position: relative; flex: none; width: 36px; height: 20px; margin: 0; border-radius: 10px;
  background: var(--disabled-color, #bdbdbd); cursor: pointer; transition: background .2s; }
input.switch::after { content: ""; position: absolute; top: 2px; left: 2px; width: 16px; height: 16px; border-radius: 50%;
  background: #fff; transition: transform .2s; }
input.switch:checked { background: var(--primary-color); }
input.switch:checked::after { transform: translateX(16px); }
.groups .g { display: flex; align-items: center; gap: 12px; padding: 10px 4px; border-bottom: 1px solid var(--divider-color); }
.groups .g > ha-icon { color: var(--primary-color); }
.groups .g div { flex: 1; min-width: 0; }
.groups small { display: block; font-size: 12px; color: var(--secondary-text-color); }
.icon-btn { display: inline-flex; padding: 6px; border: none; border-radius: 50%; background: none; color: inherit; cursor: pointer; }
.icon-btn:hover { background: var(--secondary-background-color, rgba(127, 127, 127, .15)); }
.icon-btn.confirm { border-radius: 8px; padding: 6px 10px; background: var(--error-color); color: #fff; font: inherit; font-size: 14px; }
.new { align-self: flex-start; display: inline-flex; align-items: center; gap: 6px; margin-top: 10px; padding: 8px 14px;
  border: none; border-radius: 18px; background: var(--primary-color); color: var(--text-primary-color, #fff); font: inherit; cursor: pointer; }
.picker { position: relative; }
.picker > button { display: flex; align-items: center; gap: 4px; padding: 8px; border-radius: 8px; border: 1px solid var(--divider-color);
  background: var(--primary-background-color); color: var(--primary-color); cursor: pointer; }
.icons { position: absolute; right: 0; top: calc(100% + 4px); z-index: 1; display: grid; grid-template-columns: repeat(6, 40px);
  gap: 4px; padding: 8px; border-radius: 12px; background: var(--card-background-color); box-shadow: 0 4px 16px rgba(0, 0, 0, .3); }
.icons[hidden] { display: none; }
.icons button { padding: 8px; border: none; border-radius: 8px; background: none; color: inherit; cursor: pointer; }
.icons button:hover, .icons button.on { background: color-mix(in srgb, var(--primary-color) 20%, transparent); color: var(--primary-color); }
.actions { display: flex; align-items: center; gap: 8px; }
.actions span { flex: 1; }
.actions button { padding: 8px 14px; border: none; border-radius: 8px; background: none; color: var(--primary-color); font: inherit; cursor: pointer; }
.actions .save { background: var(--primary-color); color: var(--text-primary-color, #fff); }
`;

class PvpcPlannerPanel extends HTMLElement {
  constructor() {
    super();
    this._schedule = {};
    this._groups = {};
    this._hidden = [];
    this._t = translator("en");
    this._priceEntity = null;
    this._day = null;
    this._last = {};
    const root = this.attachShadow({ mode: "open" });
    root.innerHTML = `<style>${STYLE}</style>
      <div class="toolbar"><ha-menu-button></ha-menu-button><div class="title">PVPC Planner</div>
        <button class="settings-btn"><ha-icon icon="mdi:tune-variant"></ha-icon><span></span></button></div>
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
    this._$(".settings-btn").addEventListener("click", () => this._openSettings());
  }

  set hass(hass) {
    this._hass = hass;
    const lang = langOf(hass);
    if (lang !== this._lang) {
      this._lang = lang;
      this._t = translator(lang);
      this._last = {};
      this._$(".settings-btn span").textContent = this._t("settings_title");
    }
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
        this._groups = msg.groups;
        this._hidden = msg.hidden;
        this._priceEntity = msg.price_entity;
        this._update(true);
        this._onData?.();
      },
      { type: "pvpc_planner/subscribe" }
    );
    this._unsub.catch((err) => {
      this._error = this._errText(err);
      this._update(true);
    });
  }

  // Traduce los códigos de error del websocket; el resto se muestra tal cual.
  _errText(err) {
    return err.code && STRINGS.en[`err_${err.code}`] ? this._t(`err_${err.code}`) : err.message || String(err);
  }

  // Solo repinta si cambian precios, horario o la hora actual: hass cambia con cualquier estado.
  _update(force = false) {
    const hass = this._hass;
    if (!hass) return;
    const stateObj = this._priceEntity && hass.states[this._priceEntity];
    const now = nowIn(hass.config.time_zone);
    const t = this._t;
    const l = this._last;
    if (!force && l.state === stateObj && l.date === now.date && l.hour === now.hour) return;
    this._last = { state: stateObj, date: now.date, hour: now.hour };

    const msg = this._$(".msg");
    const grid = this._$(".grid");
    const fail = (text) => {
      msg.textContent = text;
      grid.innerHTML = "";
    };
    if (this._error) return fail(this._error);
    if (!this._priceEntity) return fail(t("loading"));
    if (!stateObj) return fail(t("missing_sensor", { entity: this._priceEntity }));

    const today = parsePrices(stateObj.attributes, false);
    const tomorrow = parsePrices(stateObj.attributes, true);
    if (this._day === null || (this._day === "tomorrow" && !tomorrow.length)) {
      this._day = tomorrow.length ? "tomorrow" : "today";
    }
    const isToday = this._day === "today";
    const prices = isToday ? today : tomorrow;
    this._date = isToday ? now.date : nextDate(now.date);

    this._$(".tabs").innerHTML = `
      <button data-day="today" class="${isToday ? "on" : ""}">${t("today")}</button>
      <button data-day="tomorrow" class="${isToday ? "" : "on"}" ${tomorrow.length ? "" : `disabled title="${t("tomorrow_pending")}"`}>${t("tomorrow")}</button>`;
    const unit = stateObj.attributes.unit_of_measurement || "€/kWh";
    this._$(".legend").innerHTML = `
      <span><i class="dot" style="background:var(--success-color,#43a047)"></i>${t("cheapest", { n: TOP })}</span>
      <span><i class="dot" style="background:var(--error-color,#db4437)"></i>${t("priciest", { n: TOP })}</span>
      <span>${esc(unit)}</span>`;

    if (!prices.length) return fail(t("no_prices"));
    msg.textContent = "";

    const cls = classify(prices);
    const slots = this._schedule[this._date] || {};
    const fmt = new Intl.NumberFormat(this._lang, {
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
          <div class="h">${pad(p.hour)}:00${p.dup ? ` ${t("repeated")}` : ""}</div>
          <div class="p">${fmt.format(p.price)}</div>
          <div class="chips">${ents.map((e) => this._chip(e)).join("")}</div>
        </div>`;
      })
      .join("");
  }

  _chip(target) {
    const g = target.startsWith(GROUP) && this._groups[target.slice(GROUP.length)];
    if (!g) return `<span class="chip">${esc(nameOf(this._hass, target))}</span>`;
    return `<span class="chip"><ha-icon icon="${esc(g.icon)}"></ha-icon>${esc(g.name)}</span>`;
  }

  // Abre el diálogo con `html`; devuelve [contenedor, cerrar].
  _showDialog(html, wide = false) {
    this._closeDialog?.();
    const dlg = this._$(".dialog");
    dlg.innerHTML = `<div class="box ${wide ? "wide" : ""}" role="dialog" aria-modal="true">${html}</div>`;
    dlg.hidden = false;
    const onKey = (e) => e.key === "Escape" && close();
    const close = () => {
      dlg.hidden = true;
      dlg.innerHTML = "";
      document.removeEventListener("keydown", onKey);
      this._onData = null;
      this._closeDialog = null;
    };
    document.addEventListener("keydown", onKey);
    dlg.onclick = (e) => {
      if (e.target === dlg) close();
    };
    this._closeDialog = close;
    return [dlg, close];
  }

  async _call(dlg, msg) {
    const err = dlg.querySelector(".err");
    err.textContent = "";
    try {
      return await this._hass.callWS(msg);
    } catch (e) {
      err.textContent = this._errText(e);
      throw e;
    }
  }

  _openDialog(hour) {
    const hass = this._hass;
    const t = this._t;
    const date = this._date;
    const selected = new Set(this._schedule[date]?.[hour] || []);
    const hidden = new Set(this._hidden);
    // Un oculto ya marcado se muestra para poder quitarlo.
    const ents = devicesOf(hass).filter((e) => !hidden.has(e.id) || selected.has(e.id));
    const groups = Object.entries(this._groups)
      .map(([id, g]) => ({ id: GROUP + id, ...g }))
      .sort((a, b) => a.name.localeCompare(b.name));
    const dayLabel = new Date(`${date}T12:00:00Z`).toLocaleDateString(this._lang, {
      weekday: "long", day: "numeric", month: "long", timeZone: "UTC",
    });
    const groupRow = (g) => `<label class="group" data-q="${esc(g.name.toLowerCase())}">
      <input type="checkbox" value="${esc(g.id)}" ${selected.has(g.id) ? "checked" : ""}>
      <ha-icon icon="${esc(g.icon)}"></ha-icon><span>${esc(g.name)}<small>${g.entity_ids.length === 1 ? t("group_count_one") : t("group_count", { n: g.entity_ids.length })}</small></span></label>`;

    const [dlg, close] = this._showDialog(`
      <h2>${t("turn_on", { from: `${pad(hour)}:00`, to: `${pad((hour + 1) % 24)}:00` })}</h2>
      <div class="sub">${esc(dayLabel)}</div>
      <input type="search" placeholder="${esc(t("search"))}">
      <div class="list">${
        (groups.length ? `<div class="section">${t("settings_groups")}</div>${groups.map(groupRow).join("")}
          <div class="section">${t("settings_devices")}</div>` : "")
        + (ents.map((e) => deviceRow(e, selected.has(e.id))).join("")
          || `<p>${t("no_devices")}</p>`)
      }</div>
      <div class="err"></div>
      <div class="actions"><button class="clear">${t("clear")}</button><span></span>
        <button class="cancel">${t("cancel")}</button><button class="save">${t("save")}</button></div>`);

    const boxes = () => [...dlg.querySelectorAll("input[type=checkbox]")];
    filterOnInput(dlg.querySelector("input[type=search]"), dlg);
    dlg.querySelector(".clear").onclick = () => boxes().forEach((b) => (b.checked = false));
    dlg.querySelector(".cancel").onclick = close;
    dlg.querySelector(".save").onclick = async () => {
      const entity_ids = boxes().filter((b) => b.checked).map((b) => b.value);
      await this._call(dlg, { type: "pvpc_planner/set", date, hour, entity_ids }).then(close, () => {});
    };
  }

  _openSettings(tab = "devices") {
    const t = this._t;
    const [dlg, close] = this._showDialog(`
      <h2>${t("settings_title")}</h2>
      <div class="tabs">
        <button data-tab="devices" class="${tab === "devices" ? "on" : ""}">${t("settings_devices")}</button>
        <button data-tab="groups" class="${tab === "groups" ? "on" : ""}">${t("settings_groups")}</button>
      </div>
      <div class="body"></div>
      <div class="err"></div>
      <div class="actions"></div>`, true);
    dlg.querySelector(".body").style.display = "contents";
    // Cada vista pone sus botones en el pie común.
    const foot = (html) => {
      const el = dlg.querySelector(".box > .actions");
      el.innerHTML = `<span></span>${html}`;
      dlg.querySelector(".err").textContent = "";
      return el;
    };
    const closeFoot = () => {
      foot(`<button class="cancel">${t("settings_close")}</button>`).querySelector(".cancel").onclick = close;
    };
    const ui = { dlg, foot, closeFoot };
    dlg.querySelector(".tabs").onclick = (e) => {
      const b = e.target.closest("button[data-tab]");
      if (b) this._openSettings(b.dataset.tab);
    };
    if (tab === "devices") this._renderHidden(ui);
    else this._renderGroups(ui);
  }

  _renderHidden({ dlg, closeFoot }) {
    const t = this._t;
    const ents = devicesOf(this._hass);
    const body = dlg.querySelector(".body");
    closeFoot();
    body.innerHTML = `<p class="help">${t("hidden_help")}</p>
      <input type="search" placeholder="${esc(t("search"))}">
      <div class="tools"><span></span><button class="show">${t("hidden_show_all")}</button>
        <button class="hide">${t("hidden_hide_all")}</button></div>
      <div class="list">${ents.map((e) => deviceRow(e, false, "switch")).join("")}</div>`;
    const boxes = [...body.querySelectorAll("input[type=checkbox]")];
    const sync = () => {
      const hidden = new Set(this._hidden);
      boxes.forEach((b) => (b.checked = !hidden.has(b.value)));
      const shown = boxes.filter((b) => b.checked).length;
      body.querySelector(".tools span").textContent = t("hidden_count", { shown, total: boxes.length });
    };
    // Conserva los ocultos que ya no están en la lista (p. ej., entidades no disponibles).
    const save = (ids) => {
      const listed = new Set(ents.map((e) => e.id));
      const hidden = [...this._hidden.filter((id) => !listed.has(id)), ...ids];
      this._call(dlg, { type: "pvpc_planner/hidden/set", entity_ids: hidden }).catch(sync);
    };
    const visible = () => boxes.filter((b) => !b.closest("label").hidden);
    const setAll = (on) => {
      visible().forEach((b) => (b.checked = on));
      save(boxes.filter((b) => !b.checked).map((b) => b.value));
    };
    filterOnInput(body.querySelector("input[type=search]"), body);
    body.querySelector(".list").onchange = () => save(boxes.filter((b) => !b.checked).map((b) => b.value));
    body.querySelector(".show").onclick = () => setAll(true);
    body.querySelector(".hide").onclick = () => setAll(false);
    this._onData = sync;
    sync();
  }

  _renderGroups(ui) {
    const { dlg } = ui;
    const t = this._t;
    const body = dlg.querySelector(".body");
    ui.closeFoot();
    const render = () => {
      const groups = Object.entries(this._groups).sort((a, b) => a[1].name.localeCompare(b[1].name));
      body.innerHTML = `<p class="help">${t("group_help")}</p>
        <div class="list groups">${groups.map(([id, g]) => `<div class="g" data-id="${esc(id)}">
          <ha-icon icon="${esc(g.icon)}"></ha-icon>
          <div>${esc(g.name)}<small>${esc(g.entity_ids.map((e) => nameOf(this._hass, e)).join(", "))}</small></div>
          <button class="icon-btn edit" title="${esc(t("group_edit"))}"><ha-icon icon="mdi:pencil"></ha-icon></button>
          <button class="icon-btn del" title="${esc(t("group_delete"))}"><ha-icon icon="mdi:delete-outline"></ha-icon></button>
        </div>`).join("") || `<p>${t("group_empty")}</p>`}</div>
        <button class="new"><ha-icon icon="mdi:plus"></ha-icon>${t("group_new")}</button>`;
      body.querySelector(".new").onclick = () => this._renderGroupEditor(ui);
    };
    body.onclick = (e) => {
      const b = e.target.closest(".edit, .del");
      const id = b?.closest(".g")?.dataset.id;
      if (!id) return;
      if (b.classList.contains("edit")) return this._renderGroupEditor(ui, id);
      // Doble pulsación para borrar: sin confirm(), que bloquea la página.
      if (!b.classList.contains("confirm")) {
        b.classList.add("confirm");
        b.textContent = t("group_confirm_delete");
        return;
      }
      this._call(dlg, { type: "pvpc_planner/group/delete", group_id: id }).catch(render);
    };
    this._onData = render;
    render();
  }

  _renderGroupEditor(ui, id = null) {
    const { dlg } = ui;
    const t = this._t;
    const g = (id && this._groups[id]) || { name: "", icon: ICONS[0], entity_ids: [] };
    const selected = new Set(g.entity_ids);
    let icon = g.icon;
    const body = dlg.querySelector(".body");
    this._onData = null;
    body.onclick = null;
    body.innerHTML = `<div class="row">
        <input type="text" maxlength="40" placeholder="${esc(t("group_name"))}" value="${esc(g.name)}">
        <div class="picker"><button title="${esc(t("group_icon"))}"><ha-icon></ha-icon><ha-icon icon="mdi:menu-down"></ha-icon></button>
          <div class="icons" hidden>${ICONS.map((i) => `<button data-icon="${i}" title="${i.slice(4)}"><ha-icon icon="${i}"></ha-icon></button>`).join("")}</div></div>
      </div>
      <input type="search" placeholder="${esc(t("search"))}">
      <div class="list">${devicesOf(this._hass).map((e) => deviceRow(e, selected.has(e.id))).join("")}</div>`;
    const foot = ui.foot(`<button class="back">${t("cancel")}</button>
      <button class="save">${t("save")}</button>`);
    const grid = body.querySelector(".icons");
    const setIcon = (i) => {
      icon = i;
      body.querySelector(".picker > button ha-icon").setAttribute("icon", i);
      grid.querySelectorAll("button").forEach((b) => b.classList.toggle("on", b.dataset.icon === i));
    };
    setIcon(icon);
    body.querySelector(".picker > button").onclick = () => (grid.hidden = !grid.hidden);
    grid.onclick = (e) => {
      const b = e.target.closest("button[data-icon]");
      if (!b) return;
      setIcon(b.dataset.icon);
      grid.hidden = true;
    };
    filterOnInput(body.querySelector("input[type=search]"), body);
    const back = () => this._renderGroups(ui);
    foot.querySelector(".back").onclick = back;
    foot.querySelector(".save").onclick = () => {
      const name = body.querySelector("input[type=text]").value.trim();
      const entity_ids = [...body.querySelectorAll(".list input:checked")].map((b) => b.value);
      const err = dlg.querySelector(".err");
      if (!name) return (err.textContent = t("group_need_name"));
      if (!entity_ids.length) return (err.textContent = t("group_need_devices"));
      const msg = { type: "pvpc_planner/group/save", name, icon, entity_ids };
      if (id) msg.group_id = id;
      this._call(dlg, msg).then(back, () => {});
    };
  }
}

customElements.define("pvpc-planner-panel", PvpcPlannerPanel);
