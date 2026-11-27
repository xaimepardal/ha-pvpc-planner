const DOMAINS = ["switch", "light", "fan", "input_boolean", "humidifier"];
const TOP = 6;
const GROUP = "group:";

const DOMAIN_ICONS = {
  switch: "mdi:toggle-switch-variant", light: "mdi:lightbulb", fan: "mdi:fan",
  input_boolean: "mdi:toggle-switch-outline", humidifier: "mdi:air-humidifier",
};
const THEMES = { light: "mdi:white-balance-sunny", dark: "mdi:weather-night" };

// Preferencias de este navegador: { theme }. Descarta claves antiguas (lang).
const PREFS_KEY = "pvpc_planner_prefs";
function loadPrefs() {
  try {
    const { theme } = JSON.parse(localStorage.getItem(PREFS_KEY)) || {};
    return theme ? { theme } : {};
  } catch {
    return {};
  }
}
function savePrefs(prefs) {
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
  } catch {
    // Sin almacenamiento (modo privado): vale para esta sesión.
  }
}

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
    tomorrow_none: "PVPC prices for tomorrow have not been published yet.",
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
    hidden_help: "Choose which devices appear when scheduling an hour, and how they look.",
    device_edit: "Rename and change icon",
    device_name: "Name in this panel",
    device_icon: "Icon",
    device_default_icon: "Home Assistant icon",
    device_reset: "Reset",
    theme_light: "Theme: light",
    theme_dark: "Theme: dark",
    err_invalid_device: "Too many customized devices.",
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
    err_not_found: "It no longer exists.",
    err_invalid_group: "Too many groups.",
    settings_templates: "Templates",
    tpl_help: "A template marks hours by itself when prices are published. A device is on if any of its rules matches.",
    tpl_new: "New template",
    tpl_empty: "No templates yet.",
    tpl_rules: "Rules",
    tpl_or: "or",
    tpl_add_rule: "Add rule",
    tpl_remove_rule: "Remove rule",
    tpl_targets: "Turn on",
    tpl_need_targets: "Pick at least one device or group",
    tpl_auto: "By template",
    tpl_auto_note: "By template: {names}",
    rule_cheapest_name: "Cheapest hours of the day",
    rule_cheapest: "{hours} cheapest hours",
    rule_window_name: "Cheapest in a time range",
    rule_window: "{hours} cheapest between {from} and {to}",
    rule_negative_name: "Negative price",
    rule_negative: "Hours with negative price",
    param_hours: "Hours",
    param_from: "From",
    param_to: "To",
    param_after_cheapest: "Only from the cheapest hour onwards",
    param_second_if_alone: "If only one is left, start at the second cheapest",
    err_invalid_template: "Too many templates.",
    err_invalid_format: "Some values are not valid.",
  },
  es: {
    loading: "Cargando…",
    missing_sensor: "No se encuentra {entity}. Revisa la integración PVPC.",
    today: "Hoy",
    tomorrow: "Mañana",
    tomorrow_pending: "Se publican hacia las 20:30",
    tomorrow_none: "Todavía no hay precios PVPC publicados para mañana.",
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
    hidden_help: "Elige qué dispositivos aparecen al programar una hora y cómo se ven.",
    device_edit: "Cambiar nombre e icono",
    device_name: "Nombre en este panel",
    device_icon: "Icono",
    device_default_icon: "Icono de Home Assistant",
    device_reset: "Restablecer",
    err_invalid_device: "Demasiados dispositivos personalizados.",
    theme_light: "Tema: claro",
    theme_dark: "Tema: oscuro",
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
    err_not_found: "Ya no existe.",
    err_invalid_group: "Demasiados grupos.",
    settings_templates: "Plantillas",
    tpl_help: "Una plantilla marca las horas sola cuando se publican los precios. Un dispositivo se enciende si se cumple cualquiera de sus reglas.",
    tpl_new: "Nueva plantilla",
    tpl_empty: "Aún no hay plantillas.",
    tpl_rules: "Reglas",
    tpl_or: "o",
    tpl_add_rule: "Añadir regla",
    tpl_remove_rule: "Quitar regla",
    tpl_targets: "Encender",
    tpl_need_targets: "Elige al menos un dispositivo o grupo",
    tpl_auto: "Por plantilla",
    tpl_auto_note: "Por plantilla: {names}",
    rule_cheapest_name: "Horas más baratas del día",
    rule_cheapest: "{hours} horas más baratas",
    rule_window_name: "Más barata en una franja",
    rule_window: "{hours} más barata(s) entre {from} y {to}",
    rule_negative_name: "Precio negativo",
    rule_negative: "Horas con precio negativo",
    param_hours: "Horas",
    param_from: "Desde",
    param_to: "Hasta",
    param_after_cheapest: "Solo desde la hora más barata en adelante",
    param_second_if_alone: "Si queda una sola, empezar en la segunda más barata",
    err_invalid_template: "Demasiadas plantillas.",
    err_invalid_format: "Hay valores no válidos.",
  },
  gl: {
    loading: "Cargando…",
    missing_sensor: "Non se atopa {entity}. Revisa a integración PVPC.",
    today: "Hoxe",
    tomorrow: "Mañá",
    tomorrow_pending: "Publícanse arredor das 20:30",
    tomorrow_none: "Aínda non hai prezos PVPC publicados para mañá.",
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
    hidden_help: "Escolle que dispositivos aparecen ao programar unha hora e como se ven.",
    device_edit: "Cambiar nome e icona",
    device_name: "Nome neste panel",
    device_icon: "Icona",
    device_default_icon: "Icona de Home Assistant",
    device_reset: "Restablecer",
    err_invalid_device: "Demasiados dispositivos personalizados.",
    theme_light: "Tema: claro",
    theme_dark: "Tema: escuro",
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
    err_not_found: "Xa non existe.",
    err_invalid_group: "Demasiados grupos.",
    settings_templates: "Modelos",
    tpl_help: "Un modelo marca as horas só cando se publican os prezos. Un dispositivo acéndese se se cumpre calquera das súas regras.",
    tpl_new: "Novo modelo",
    tpl_empty: "Aínda non hai modelos.",
    tpl_rules: "Regras",
    tpl_or: "ou",
    tpl_add_rule: "Engadir regra",
    tpl_remove_rule: "Quitar regra",
    tpl_targets: "Acender",
    tpl_need_targets: "Escolle polo menos un dispositivo ou grupo",
    tpl_auto: "Por modelo",
    tpl_auto_note: "Por modelo: {names}",
    rule_cheapest_name: "Horas máis baratas do día",
    rule_cheapest: "{hours} horas máis baratas",
    rule_window_name: "Máis barata nunha franxa",
    rule_window: "{hours} máis barata(s) entre {from} e {to}",
    rule_negative_name: "Prezo negativo",
    rule_negative: "Horas con prezo negativo",
    param_hours: "Horas",
    param_from: "Desde",
    param_to: "Ata",
    param_after_cheapest: "Só desde a hora máis barata en diante",
    param_second_if_alone: "Se queda unha soa, comezar na segunda máis barata",
    err_invalid_template: "Demasiados modelos.",
    err_invalid_format: "Hai valores non válidos.",
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

// Nombre e icono con lo personalizado en el panel por delante del de HA.
const deviceOf = (hass, custom, id) => ({
  id,
  name: custom[id]?.name || nameOf(hass, id),
  icon: custom[id]?.icon || hass.states[id]?.attributes.icon || DOMAIN_ICONS[id.split(".")[0]],
});

// Dispositivos de encendido/apagado que HA no oculta.
function devicesOf(hass, custom) {
  return Object.keys(hass.states)
    .filter((id) => {
      const reg = hass.entities?.[id];
      return DOMAINS.includes(id.split(".")[0]) && !reg?.hidden && !reg?.entity_category;
    })
    .map((id) => deviceOf(hass, custom, id))
    .sort((a, b) => a.name.localeCompare(b.name));
}

const iconTag = (icon) => (icon ? `<ha-icon icon="${esc(icon)}"></ha-icon>` : "");

const deviceRow = (e, checked, cls = "", extra = "") => `<label class="${cls}" data-q="${esc(`${e.name} ${e.id}`.toLowerCase())}">
  <input type="checkbox" class="${cls}" value="${esc(e.id)}" ${checked ? "checked" : ""}>${extra}
  <span class="dev">${iconTag(e.icon)}<span>${esc(e.name)}<small>${esc(e.id)}</small></span></span></label>`;

const pickerHtml = (title, withDefault) => `<div class="picker">
  <button type="button" title="${esc(title)}"><ha-icon></ha-icon><ha-icon icon="mdi:menu-down"></ha-icon></button>
  <div class="icons" hidden>${(withDefault ? [""] : []).concat(ICONS).map((i) =>
    `<button type="button" data-icon="${i}" title="${esc(i ? i.slice(4) : withDefault)}"><ha-icon icon="${i || "mdi:restore"}"></ha-icon></button>`).join("")}</div></div>`;

// Desplegable de iconos dentro de `root`; "" = icono de HA (se muestra `fallback`).
function bindPicker(root, initial, fallback = "mdi:restore") {
  const grid = root.querySelector(".icons");
  let icon = initial;
  const set = (i) => {
    icon = i;
    root.querySelector(".picker > button ha-icon").setAttribute("icon", i || fallback);
    grid.querySelectorAll("button").forEach((b) => b.classList.toggle("on", b.dataset.icon === i));
  };
  set(icon);
  root.querySelector(".picker > button").onclick = () => (grid.hidden = !grid.hidden);
  grid.onclick = (e) => {
    const b = e.target.closest("button[data-icon]");
    if (!b) return;
    set(b.dataset.icon);
    grid.hidden = true;
  };
  return () => icon;
}

function filterOnInput(input, root) {
  input.addEventListener("input", () => {
    const q = input.value.trim().toLowerCase();
    root.querySelectorAll("label[data-q]").forEach((l) => (l.hidden = !l.dataset.q.includes(q)));
  });
}

// Destinos (grupos y dispositivos) para marcar; los ocultos solo si ya están elegidos.
function targetsHtml(t, groups, devices, selected) {
  const groupRow = (g) => `<label class="group" data-q="${esc(g.name.toLowerCase())}">
    <input type="checkbox" value="${esc(g.id)}" ${selected.has(g.id) ? "checked" : ""}>
    <ha-icon icon="${esc(g.icon)}"></ha-icon><span>${esc(g.name)}<small>${g.entity_ids.length === 1 ? t("group_count_one") : t("group_count", { n: g.entity_ids.length })}</small></span></label>`;
  return (groups.length ? `<div class="section">${t("settings_groups")}</div>${groups.map(groupRow).join("")}
      <div class="section">${t("settings_devices")}</div>` : "")
    + (devices.map((e) => deviceRow(e, selected.has(e.id))).join("") || `<p>${t("no_devices")}</p>`);
}

// Reglas de plantilla: los controles salen del esquema que manda el backend
// ({id, params: [{key, type: "int"|"bool", ...}]}); una regla nueva solo necesita textos.
const paramText = (p, v) => (p.unit === "hour" ? `${pad(v)}:00` : String(v));

function ruleSummary(t, rules, item) {
  const rule = rules.find((r) => r.id === item.rule);
  if (!rule) return item.rule;
  const vals = Object.fromEntries(rule.params.filter((p) => p.type === "int")
    .map((p) => [p.key, paramText(p, item.params[p.key] ?? p.default)]));
  const flags = rule.params.filter((p) => p.type === "bool" && item.params[p.key]
    && (!p.requires || item.params[p.requires])).map((p) => t(`param_${p.key}`).toLowerCase());
  return t(`rule_${rule.id}`, vals) + (flags.length ? ` (${flags.join("; ")})` : "");
}

function ruleHtml(t, rules, item, removable) {
  const rule = rules.find((r) => r.id === item.rule) || rules[0];
  const val = (p) => item.params?.[p.key] ?? p.default;
  const field = (p) => {
    if (p.type === "bool") {
      return `<label class="param check"><input type="checkbox" data-key="${p.key}" ${val(p) ? "checked" : ""}
        ${p.requires ? `data-requires="${p.requires}"` : ""}><span>${esc(t(`param_${p.key}`))}</span></label>`;
    }
    const opts = [];
    for (let v = p.min; v <= p.max; v++) {
      opts.push(`<option value="${v}" ${v === val(p) ? "selected" : ""}>${paramText(p, v)}</option>`);
    }
    return `<label class="param"><span>${esc(t(`param_${p.key}`))}</span><select data-key="${p.key}">${opts.join("")}</select></label>`;
  };
  return `<div class="rule">
    <div class="row"><select class="rule-id">${rules.map((r) =>
      `<option value="${r.id}" ${r.id === rule.id ? "selected" : ""}>${esc(t(`rule_${r.id}_name`))}</option>`).join("")}</select>
      ${removable ? `<button type="button" class="icon-btn remove" title="${esc(t("tpl_remove_rule"))}"><ha-icon icon="mdi:close"></ha-icon></button>` : ""}</div>
    <div class="params">${rule.params.map(field).join("")}</div></div>`;
}

// Lee un bloque .rule del editor; "requires" sin marcar desactiva la casilla dependiente.
function readRule(el, rules) {
  const rule = rules.find((r) => r.id === el.querySelector(".rule-id").value);
  const params = {};
  el.querySelectorAll("[data-key]").forEach((f) => {
    params[f.dataset.key] = f.type === "checkbox" ? f.checked : +f.value;
  });
  el.querySelectorAll("[data-requires]").forEach((f) => {
    f.disabled = !params[f.dataset.requires];
    f.closest("label").classList.toggle("off", f.disabled);
  });
  return { rule: rule.id, params };
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

const TREND = { cheap: ["mdi:trending-down", "cheapest"], expensive: ["mdi:trending-up", "priciest"] };

function trendHtml(t, level) {
  if (!TREND[level]) return "";
  const [icon, key] = TREND[level];
  return `<ha-icon class="trend" icon="${icon}" title="${esc(t(key, { n: TOP }))}"></ha-icon>`;
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

const MAX_ICONS = 3;

const STYLE = `
:host([theme=light]) { color-scheme: light; --primary-background-color: #fafafa; --secondary-background-color: #e5e5e5;
  --card-background-color: #fff; --primary-text-color: #212121; --secondary-text-color: #727272;
  --divider-color: rgba(0, 0, 0, .12); --disabled-color: #bdbdbd; --app-header-background-color: #fff;
  --app-header-text-color: #212121; }
:host([theme=dark]) { color-scheme: dark; --primary-background-color: #111; --secondary-background-color: #282828;
  --card-background-color: #1c1c1c; --primary-text-color: #e1e1e1; --secondary-text-color: #9b9b9b;
  --divider-color: rgba(225, 225, 225, .12); --disabled-color: #6f6f6f; --app-header-background-color: #101e24;
  --app-header-text-color: #e1e1e1; }
:host { display: block; min-height: 100vh; background: var(--primary-background-color); color: var(--primary-text-color);
  font-family: var(--ha-font-family-body, Roboto, sans-serif); }
.toolbar { display: flex; align-items: center; gap: 8px; height: var(--header-height, 56px); padding: 0 12px;
  background: var(--app-header-background-color); color: var(--app-header-text-color, #fff); font-size: 20px; }
.toolbar .title { flex: 1; }
.settings-btn { display: inline-flex; align-items: center; gap: 8px; padding: 7px 16px 7px 12px; border-radius: 20px;
  border: 1px solid color-mix(in srgb, currentColor 30%, transparent); background: color-mix(in srgb, currentColor 10%, transparent);
  color: inherit; font: inherit;
  font-size: 15px; font-weight: 500; cursor: pointer; transition: background .2s, transform .2s; }
.settings-btn:hover, .pill:hover { background: color-mix(in srgb, currentColor 20%, transparent); }
.settings-btn:hover ha-icon { transform: rotate(60deg); }
.settings-btn ha-icon { transition: transform .3s; --mdc-icon-size: 20px; }
.settings-btn:focus-visible, .pill:focus-visible { outline: 2px solid currentColor; outline-offset: 2px; }
.pill { display: inline-flex; align-items: center; height: 36px; padding: 0 10px; border-radius: 18px; box-sizing: border-box;
  border: 1px solid color-mix(in srgb, currentColor 30%, transparent); background: color-mix(in srgb, currentColor 10%, transparent);
  color: inherit; font: inherit;
  font-size: 14px; cursor: pointer; --mdc-icon-size: 20px; }
.content { max-width: 1100px; margin: 0 auto; padding: 12px; box-sizing: border-box; container-type: inline-size; }
.bar { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; margin-bottom: 12px; }
.tabs { display: flex; gap: 8px; }
.tabs button { padding: 8px 18px; border-radius: 18px; border: 1px solid var(--divider-color); background: var(--card-background-color);
  color: inherit; font: inherit; cursor: pointer; }
.tabs button.on { background: var(--primary-color); border-color: var(--primary-color); color: var(--text-primary-color, #fff); }
.tabs button[aria-disabled="true"] { opacity: .45; }
.msg:empty { display: none; }
.msg { padding: 12px; border-radius: 8px; background: var(--card-background-color); margin-bottom: 12px; }
/* Columnas divisoras de 24 para filas completas; celdas cuadradas. */
.grid { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 8px; }
@container (max-width: 760px) { .grid { grid-template-columns: repeat(4, minmax(0, 1fr)); } }
@container (max-width: 440px) { .grid { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; } }
.cell { aspect-ratio: 1; min-width: 0; overflow: hidden; box-sizing: border-box; display: grid; grid-template-rows: 1fr 1fr;
  container-type: inline-size; background: var(--card-background-color); border: 1px solid var(--divider-color); border-radius: 12px;
  padding: 7%; cursor: pointer; }
/* Como la imagen para pantallas: precio y flecha en verde (barata) o rojo (cara). */
.cheap { --c: var(--success-color, #43a047); }
.expensive { --c: var(--error-color, #db4437); }
.cell:is(.cheap, .expensive) .p { color: var(--c); }
.trend { --mdc-icon-size: 1em; margin-left: 2cqw; vertical-align: -.1em; }
.cell.past { opacity: .4; cursor: default; }
.cell.now { outline: 2px solid var(--primary-color); outline-offset: -1px; }
.cell:focus-visible { outline: 2px solid var(--primary-color); }
/* Medidas en cqw: escalan con la celda. Mitad superior hora y precio; inferior, dispositivos. */
.h, .p { font-size: 21cqw; font-weight: 700; line-height: 1.15; white-space: nowrap; font-variant-numeric: tabular-nums; }
.p { font-size: 20cqw; font-weight: 800; letter-spacing: -.02em; }
.h small { font-size: .5em; font-weight: 500; }
.devs { display: flex; align-items: center; align-self: end; gap: 4cqw; min-width: 0; color: var(--primary-color);
  --mdc-icon-size: 25cqw; }
.devs ha-icon { flex: none; }
.devs .name { display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden; overflow-wrap: anywhere;
  font-size: 11cqw; font-weight: 500; line-height: 1.1; color: var(--primary-text-color); }
.devs .more { font-size: 14cqw; font-weight: 700; }
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
.list label.group ha-icon, .dev ha-icon { color: var(--primary-color); }
.dev { display: flex; align-items: center; gap: 10px; min-width: 0; }
label.switch .dev { flex: 1; }
label.switch .icon-btn { color: var(--secondary-text-color); }
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
.cell { position: relative; }
.badge { position: absolute; top: 6%; right: 6%; --mdc-icon-size: 15cqw; color: var(--secondary-text-color); }
.auto-note { display: flex; align-items: center; gap: 6px; margin: 0 0 8px; font-size: 14px; color: var(--secondary-text-color);
  --mdc-icon-size: 18px; }
.rule { padding: 10px; margin-bottom: 4px; border: 1px solid var(--divider-color); border-radius: 12px; }
.or { margin: 4px 0; text-align: center; font-size: 12px; text-transform: uppercase; color: var(--secondary-text-color); }
.box select { flex: 1; min-width: 0; padding: 8px; border-radius: 8px; border: 1px solid var(--divider-color);
  background: var(--primary-background-color); color: inherit; font: inherit; }
.rule .row { margin: 0; }
.params { display: flex; flex-wrap: wrap; gap: 8px 12px; }
.params:not(:empty) { margin-top: 8px; }
.param { display: flex; align-items: center; gap: 6px; font-size: 14px; }
.param select { flex: none; }
.param.check { flex-basis: 100%; cursor: pointer; }
.param.off { opacity: .5; }
.add-rule { align-self: flex-start; }
.tpl-scroll { flex: 1; overflow: auto; min-height: 0; }
.tpl-scroll .list { overflow: visible; }
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
    this._devices = {};
    this._templates = {};
    this._auto = {};
    this._rules = [];
    this._t = translator("en");
    this._prefs = loadPrefs();
    this._priceEntity = null;
    this._day = null;
    this._last = {};
    const root = this.attachShadow({ mode: "open" });
    root.innerHTML = `<style>${STYLE}</style>
      <div class="toolbar"><ha-menu-button></ha-menu-button><div class="title">PVPC Planner</div>
        <button class="pill theme"><ha-icon></ha-icon></button>
        <button class="settings-btn"><ha-icon icon="mdi:tune-variant"></ha-icon><span></span></button></div>
      <div class="content">
        <div class="bar"><div class="tabs"></div></div>
        <div class="msg"></div>
        <div class="grid"></div>
      </div>
      <div class="dialog" hidden></div>`;
    this._$ = (s) => root.querySelector(s);

    this._$(".tabs").addEventListener("click", (e) => {
      const b = e.target.closest("button[data-day]");
      if (!b) return;
      if (b.getAttribute("aria-disabled") === "true") return this._openNoTomorrow();
      this._day = b.dataset.day;
      this._update(true);
    });
    const open = (e) => {
      const c = e.target.closest(".cell");
      if (c && !c.classList.contains("past")) this._openDialog(+c.dataset.hour);
    };
    this._$(".grid").addEventListener("click", open);
    this._$(".grid").addEventListener("keydown", (e) => (e.key === "Enter" || e.key === " ") && open(e));
    this._$(".settings-btn").addEventListener("click", () => this._openSettings());
    // Volver al modo de HA borra la preferencia: así sigue a HA si cambia.
    this._$(".theme").addEventListener("click", () => {
      const next = this._theme === "dark" ? "light" : "dark";
      this._setPref("theme", next === this._haTheme() ? "auto" : next);
    });
  }

  set hass(hass) {
    this._hass = hass;
    this._applyPrefs();
    this._$("ha-menu-button").hass = hass;
    this._subscribe();
    this._update();
  }

  _setPref(key, value) {
    this._prefs = { ...this._prefs, [key]: value };
    if (value === "auto") delete this._prefs[key];
    savePrefs(this._prefs);
    this._closeDialog?.();
    this._applyPrefs();
    this._update(true);
  }

  _haTheme() {
    return this._hass.themes?.darkMode ? "dark" : "light";
  }

  // Idioma de HA. Tema de HA salvo que se elija el contrario en este navegador; solo entonces se fuerzan colores.
  _applyPrefs() {
    const lang = langOf(this._hass);
    const ha = this._haTheme();
    const theme = this._prefs.theme || ha;
    if (lang === this._lang && theme === this._theme && ha === this._ha) return;
    if (theme === ha) this.removeAttribute("theme");
    else this.setAttribute("theme", theme);
    this._theme = theme;
    this._ha = ha;
    this._lang = lang;
    const t = (this._t = translator(lang));
    this._last = {};
    this._$(".settings-btn span").textContent = t("settings_title");
    const themeBtn = this._$(".theme");
    themeBtn.title = t(`theme_${theme}`);
    themeBtn.querySelector("ha-icon").setAttribute("icon", THEMES[theme]);
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
        this._devices = msg.devices || {};
        this._templates = msg.templates || {};
        this._auto = msg.auto || {};
        this._rules = msg.rules || [];
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
      <button data-day="tomorrow" class="${isToday ? "" : "on"}" ${tomorrow.length ? "" : `aria-disabled="true" title="${t("tomorrow_pending")}"`}>${t("tomorrow")}</button>`;
    if (!prices.length) return fail(t("no_prices"));
    msg.textContent = "";

    const cls = classify(prices);
    const slots = this._schedule[this._date] || {};
    const auto = this._auto[this._date] || {};
    const fmt = new Intl.NumberFormat(this._lang, {
      minimumFractionDigits: 4,
      maximumFractionDigits: 4,
    });
    grid.innerHTML = prices
      .map((p) => {
        const past = isToday && p.hour < now.hour;
        const current = isToday && p.hour === now.hour;
        const auto_ = auto[p.hour] || [];
        const ents = [...new Set([...(slots[p.hour] || []), ...auto_])];
        return `<div class="cell ${cls.get(p) || ""} ${past ? "past" : ""} ${current ? "now" : ""}"
            data-hour="${p.hour}" role="button" tabindex="${past ? -1 : 0}">
          ${auto_.length ? `<ha-icon class="badge" icon="mdi:robot" title="${esc(t("tpl_auto"))}"></ha-icon>` : ""}
          <div><div class="h">${pad(p.hour)}:00${p.dup ? ` <small>${t("repeated")}</small>` : ""}</div>
          <div class="p">${fmt.format(p.price)}${trendHtml(t, cls.get(p))}</div></div>
          ${this._devs(ents)}
        </div>`;
      })
      .join("");
  }

  // Uno: icono y nombre. Varios: solo iconos, y a partir de MAX_ICONS el resto como "+N".
  _devs(targets) {
    if (!targets.length) return "";
    const items = targets.map((id) => this._target(id));
    const title = esc(items.map((d) => d.name).join(", "));
    if (items.length === 1) {
      return `<div class="devs" title="${title}">${iconTag(items[0].icon)}<span class="name">${esc(items[0].name)}</span></div>`;
    }
    const shown = items.length > MAX_ICONS ? items.slice(0, MAX_ICONS - 1) : items;
    const rest = items.length - shown.length;
    return `<div class="devs" title="${title}">${shown.map((d) => iconTag(d.icon)).join("")}${
      rest ? `<span class="more">+${rest}</span>` : ""}</div>`;
  }

  _target(id) {
    const g = id.startsWith(GROUP) && this._groups[id.slice(GROUP.length)];
    const { name, icon } = g || deviceOf(this._hass, this._devices, id);
    return { name, icon: icon || "mdi:devices" };
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

  _openNoTomorrow() {
    const t = this._t;
    const [dlg, close] = this._showDialog(`
      <h2>${t("tomorrow")}</h2>
      <p>${t("tomorrow_none")} ${t("tomorrow_pending")}.</p>
      <div class="actions"><span></span><button class="cancel">${t("settings_close")}</button></div>`);
    dlg.querySelector(".cancel").onclick = close;
  }

  _openDialog(hour) {
    const hass = this._hass;
    const t = this._t;
    const date = this._date;
    const selected = new Set(this._schedule[date]?.[hour] || []);
    const hidden = new Set(this._hidden);
    // Un oculto ya marcado se muestra para poder quitarlo.
    const ents = devicesOf(hass, this._devices).filter((e) => !hidden.has(e.id) || selected.has(e.id));
    const groups = this._groupList();
    const auto = this._auto[date]?.[hour] || [];
    const dayLabel = new Date(`${date}T12:00:00Z`).toLocaleDateString(this._lang, {
      weekday: "long", day: "numeric", month: "long", timeZone: "UTC",
    });
    const [dlg, close] = this._showDialog(`
      <h2>${t("turn_on", { from: `${pad(hour)}:00`, to: `${pad((hour + 1) % 24)}:00` })}</h2>
      <div class="sub">${esc(dayLabel)}</div>
      ${auto.length ? `<p class="auto-note"><ha-icon icon="mdi:robot"></ha-icon>${esc(t("tpl_auto_note", {
        names: auto.map((id) => this._target(id).name).join(", ") }))}</p>` : ""}
      <input type="search" placeholder="${esc(t("search"))}">
      <div class="list">${targetsHtml(t, groups, ents, selected)}</div>
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

  _groupList() {
    return Object.entries(this._groups)
      .map(([id, g]) => ({ id: GROUP + id, ...g }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }

  _openSettings(tab = "devices") {
    const t = this._t;
    const [dlg, close] = this._showDialog(`
      <h2>${t("settings_title")}</h2>
      <div class="tabs">
        <button data-tab="devices" class="${tab === "devices" ? "on" : ""}">${t("settings_devices")}</button>
        <button data-tab="groups" class="${tab === "groups" ? "on" : ""}">${t("settings_groups")}</button>
        <button data-tab="templates" class="${tab === "templates" ? "on" : ""}">${t("settings_templates")}</button>
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
    else if (tab === "groups") this._renderGroups(ui);
    else this._renderTemplates(ui);
  }

  _renderHidden(ui) {
    const { dlg, closeFoot } = ui;
    const t = this._t;
    const ents = devicesOf(this._hass, this._devices);
    const body = dlg.querySelector(".body");
    closeFoot();
    body.innerHTML = `<p class="help">${t("hidden_help")}</p>
      <input type="search" placeholder="${esc(t("search"))}">
      <div class="tools"><span></span><button class="show">${t("hidden_show_all")}</button>
        <button class="hide">${t("hidden_hide_all")}</button></div>
      <div class="list">${ents.map((e) => deviceRow(e, false, "switch",
        `<button type="button" class="icon-btn edit" title="${esc(t("device_edit"))}"><ha-icon icon="mdi:pencil"></ha-icon></button>`)).join("")}</div>`;
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
    body.querySelector(".list").onclick = (e) => {
      const b = e.target.closest(".edit");
      if (b) this._renderDeviceEditor(ui, b.closest("label").querySelector("input").value);
    };
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
          <div>${esc(g.name)}<small>${esc(g.entity_ids.map((e) => deviceOf(this._hass, this._devices, e).name).join(", "))}</small></div>
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
    const body = dlg.querySelector(".body");
    this._onData = null;
    body.onclick = null;
    body.innerHTML = `<div class="row">
        <input type="text" maxlength="40" placeholder="${esc(t("group_name"))}" value="${esc(g.name)}">
        ${pickerHtml(t("group_icon"), "")}
      </div>
      <input type="search" placeholder="${esc(t("search"))}">
      <div class="list">${devicesOf(this._hass, this._devices).map((e) => deviceRow(e, selected.has(e.id))).join("")}</div>`;
    const foot = ui.foot(`<button class="back">${t("cancel")}</button>
      <button class="save">${t("save")}</button>`);
    const icon = bindPicker(body, g.icon);
    filterOnInput(body.querySelector("input[type=search]"), body);
    const back = () => this._renderGroups(ui);
    foot.querySelector(".back").onclick = back;
    foot.querySelector(".save").onclick = () => {
      const name = body.querySelector("input[type=text]").value.trim();
      const entity_ids = [...body.querySelectorAll(".list input:checked")].map((b) => b.value);
      const err = dlg.querySelector(".err");
      if (!name) return (err.textContent = t("group_need_name"));
      if (!entity_ids.length) return (err.textContent = t("group_need_devices"));
      const msg = { type: "pvpc_planner/group/save", name, icon: icon(), entity_ids };
      if (id) msg.group_id = id;
      this._call(dlg, msg).then(back, () => {});
    };
  }

  _renderTemplates(ui) {
    const { dlg } = ui;
    const t = this._t;
    const body = dlg.querySelector(".body");
    ui.closeFoot();
    const render = () => {
      const list = Object.entries(this._templates);
      body.innerHTML = `<p class="help">${t("tpl_help")}</p>
        <div class="list groups">${list.map(([id, tpl]) => `<div class="g" data-id="${esc(id)}">
          <ha-icon icon="mdi:robot"></ha-icon>
          <div>${tpl.rules.map((r, i) => `<div>${i ? `${t("tpl_or")} ` : ""}${esc(ruleSummary(t, this._rules, r))}</div>`).join("")}
            <small>${esc(tpl.targets.map((id) => this._target(id).name).join(", "))}</small></div>
          <button class="icon-btn edit" title="${esc(t("group_edit"))}"><ha-icon icon="mdi:pencil"></ha-icon></button>
          <button class="icon-btn del" title="${esc(t("group_delete"))}"><ha-icon icon="mdi:delete-outline"></ha-icon></button>
        </div>`).join("") || `<p>${t("tpl_empty")}</p>`}</div>
        <button class="new"><ha-icon icon="mdi:plus"></ha-icon>${t("tpl_new")}</button>`;
      body.querySelector(".new").onclick = () => this._renderTemplateEditor(ui);
    };
    body.onclick = (e) => {
      const b = e.target.closest(".edit, .del");
      const id = b?.closest(".g")?.dataset.id;
      if (!id) return;
      if (b.classList.contains("edit")) return this._renderTemplateEditor(ui, id);
      if (!b.classList.contains("confirm")) {
        b.classList.add("confirm");
        b.textContent = t("group_confirm_delete");
        return;
      }
      this._call(dlg, { type: "pvpc_planner/template/delete", template_id: id }).catch(render);
    };
    this._onData = render;
    render();
  }

  _renderTemplateEditor(ui, id = null) {
    const { dlg } = ui;
    const t = this._t;
    const rules = this._rules;
    const tpl = (id && this._templates[id]) || { rules: [{ rule: rules[0].id, params: {} }], targets: [] };
    const selected = new Set(tpl.targets);
    const hidden = new Set(this._hidden);
    const devices = devicesOf(this._hass, this._devices).filter((e) => !hidden.has(e.id) || selected.has(e.id));
    const body = dlg.querySelector(".body");
    this._onData = null;
    body.onclick = null;
    body.innerHTML = `<div class="tpl-scroll">
        <div class="section">${t("tpl_rules")}</div><div class="rules"></div>
        <button type="button" class="link add-rule">+ ${t("tpl_add_rule")}</button>
        <div class="section">${t("tpl_targets")}</div>
        <input type="search" placeholder="${esc(t("search"))}">
        <div class="list">${targetsHtml(t, this._groupList(), devices, selected)}</div></div>`;
    const box = body.querySelector(".rules");
    let items = tpl.rules.map((r) => ({ ...r, params: { ...r.params } }));
    const draw = () => {
      box.innerHTML = items.map((r) => ruleHtml(t, rules, r, items.length > 1))
        .join(`<div class="or">${t("tpl_or")}</div>`);
      box.querySelectorAll(".rule").forEach((el) => readRule(el, rules));
    };
    const read = () => [...box.querySelectorAll(".rule")].map((el) => readRule(el, rules));
    // Cambiar la regla reinicia sus parámetros a los de por defecto.
    box.onchange = (e) => {
      items = read();
      if (e.target.classList.contains("rule-id")) {
        items[[...box.querySelectorAll(".rule-id")].indexOf(e.target)].params = {};
        draw();
      }
    };
    box.onclick = (e) => {
      const b = e.target.closest(".remove");
      if (!b) return;
      items = read();
      items.splice([...box.querySelectorAll(".rule")].indexOf(b.closest(".rule")), 1);
      draw();
    };
    body.querySelector(".add-rule").onclick = () => {
      items = [...read(), { rule: rules[0].id, params: {} }];
      draw();
    };
    draw();
    filterOnInput(body.querySelector("input[type=search]"), body);
    const foot = ui.foot(`<button class="back">${t("cancel")}</button><button class="save">${t("save")}</button>`);
    const back = () => this._renderTemplates(ui);
    foot.querySelector(".back").onclick = back;
    foot.querySelector(".save").onclick = () => {
      const targets = [...body.querySelectorAll(".list input:checked")].map((b) => b.value);
      if (!targets.length) return (dlg.querySelector(".err").textContent = t("tpl_need_targets"));
      const msg = { type: "pvpc_planner/template/save", rules: read(), targets };
      if (id) msg.template_id = id;
      this._call(dlg, msg).then(back, () => {});
    };
  }

  _renderDeviceEditor(ui, id) {
    const { dlg } = ui;
    const t = this._t;
    const hass = this._hass;
    const custom = this._devices[id] || {};
    const haIcon = deviceOf(hass, {}, id).icon;
    const body = dlg.querySelector(".body");
    this._onData = null;
    body.querySelector(".list").onclick = null;
    body.innerHTML = `<p class="help">${t("device_edit")}: ${esc(nameOf(hass, id))} · ${esc(id)}</p>
      <div class="row">
        <input type="text" maxlength="40" placeholder="${esc(nameOf(hass, id))}" value="${esc(custom.name || "")}"
          aria-label="${esc(t("device_name"))}">
        ${pickerHtml(t("device_icon"), t("device_default_icon"))}
      </div>`;
    const icon = bindPicker(body, custom.icon || "", haIcon);
    const foot = ui.foot(`<button class="reset">${t("device_reset")}</button>
      <button class="back">${t("cancel")}</button><button class="save">${t("save")}</button>`);
    const back = () => this._renderHidden(ui);
    const send = (name, icn) =>
      this._call(dlg, { type: "pvpc_planner/device/set", entity_id: id, name, icon: icn }).then(() => {
        // El evento de la suscripción puede llegar después: se refleja ya.
        const { [id]: _, ...rest } = this._devices;
        this._devices = name || icn ? { ...rest, [id]: { ...(name && { name }), ...(icn && { icon: icn }) } } : rest;
        back();
      }, () => {});
    foot.querySelector(".back").onclick = back;
    foot.querySelector(".reset").onclick = () => send(null, null);
    foot.querySelector(".save").onclick = () => send(body.querySelector("input[type=text]").value.trim() || null, icon() || null);
  }
}

customElements.define("pvpc-planner-panel", PvpcPlannerPanel);
