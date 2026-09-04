const API = "/api";
const state = {
  route: "dashboard",
  page: 1,
  filters: {},
  catalogs: { departments: [], users: [], categories: [] },
  currentUser: null,
};

const labels = {
  status: { new: "Nueva", assigned: "Asignada", in_progress: "En progreso", blocked: "Bloqueada", resolved: "Resuelta", closed: "Cerrada" },
  priority: { low: "Baja", medium: "Media", high: "Alta", critical: "Crítica" },
  action: { created: "creó la solicitud", assigned: "cambió la asignación", status_changed: "cambió el estado", priority_changed: "cambió la prioridad", updated: "actualizó la solicitud", commented: "agregó un comentario" },
  field: { title: "título", description: "descripción", category_id: "categoría", requesting_department_id: "departamento", assigned_user_id: "responsable", priority: "prioridad", status: "estado", due_at: "fecha límite" },
};

const icons = {
  dashboard: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  inbox: '<path d="M4 4h16v14H4z"/><path d="M4 13h4l2 3h4l2-3h4"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v6l4 2"/>',
  alert: '<path d="M12 3 2.7 20h18.6L12 3Z"/><path d="M12 9v4m0 3h.01"/>',
  code: '<path d="m8 9-4 3 4 3m8-6 4 3-4 3m-2-9-4 12"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4"/>',
  bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  send: '<path d="m3 4 18 8-18 8 4-8-4-8Z"/><path d="M7 12h14"/>',
  activity: '<path d="M3 12h4l2-7 4 14 2-7h6"/>',
  arrow: '<path d="m9 18 6-6-6-6"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  layers: '<path d="m12 2 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5M3 17l9 5 9-5"/>',
};

function svg(name) {
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] || icons.layers}</svg>`;
}
function injectIcons(root = document) { root.querySelectorAll("[data-icon]").forEach(node => { node.innerHTML = svg(node.dataset.icon); }); }
function escapeHTML(value = "") { const node = document.createElement("div"); node.textContent = String(value); return node.innerHTML; }
function initials(name = "") { return name.split(/\s+/).slice(0, 2).map(part => part[0]).join("").toUpperCase(); }
function avatarColor(user) {
  const palette = ["#2563eb", "#0f172a", "#3b82f6", "#64748b", "#1d4ed8", "#475569"];
  return palette[(Number(user?.id || 1) - 1) % palette.length];
}
function formatDate(value) { return value ? new Intl.DateTimeFormat("es-UY", { day: "2-digit", month: "short" }).format(new Date(value)) : "Sin fecha"; }
function formatDateTime(value) { return value ? new Intl.DateTimeFormat("es-UY", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }).format(new Date(value)) : "—"; }
function relativeTime(value) {
  const seconds = Math.round((new Date(value).getTime() - Date.now()) / 1000);
  const absolute = Math.abs(seconds);
  const [unit, size] = absolute < 3600 ? ["minute", 60] : absolute < 86400 ? ["hour", 3600] : ["day", 86400];
  return new Intl.RelativeTimeFormat("es", { numeric: "auto" }).format(Math.round(seconds / size), unit);
}
function formatHours(value) { return value >= 48 ? `${(value / 24).toFixed(1)} días` : `${value.toFixed(1)} h`; }
function progress(status) { return { new: 10, assigned: 28, in_progress: 64, blocked: 46, resolved: 100, closed: 100 }[status] || 0; }

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, { ...options, headers: { "Content-Type": "application/json", ...(options.headers || {}) } });
  if (!response.ok) {
    let payload = {};
    try { payload = await response.json(); } catch (_) { /* response without JSON */ }
    const detail = Array.isArray(payload.detail) ? payload.detail.map(item => item.msg).join(" · ") : payload.detail;
    throw new Error(detail || "No se pudo completar la operación.");
  }
  return response.json();
}
function notify(message, type = "success") {
  const toast = document.createElement("div");
  toast.className = `toast ${type}`; toast.textContent = message;
  document.querySelector("#toasts").append(toast);
  window.setTimeout(() => toast.remove(), 4000);
}
function loading() { document.querySelector("#content").innerHTML = '<div class="loading"><span></span><p>Cargando información...</p></div>'; }
function empty(title, message) { return `<div class="empty"><i>${svg("inbox")}</i><strong>${title}</strong><p>${message}</p></div>`; }

async function start() {
  injectIcons();
  try {
    const [departments, users, categories] = await Promise.all([
      api("/catalogs/departments"), api("/catalogs/users"), api("/catalogs/categories"),
    ]);
    state.catalogs = { departments, users, categories };
    state.currentUser = users.find(user => user.role.toLowerCase().includes("admin")) || users[0];
    populateCreateForm(); bindShell(); await showDashboard();
  } catch (error) { showFatal(error); }
}

function bindShell() {
  document.querySelectorAll("[data-route]").forEach(element => element.addEventListener("click", event => {
    event.preventDefault(); navigate(element.dataset.route);
  }));
  document.querySelectorAll("[data-new-request]").forEach(button => button.addEventListener("click", openModal));
  document.querySelectorAll("[data-close-modal]").forEach(button => button.addEventListener("click", closeModal));
  document.querySelector("#create-form").addEventListener("submit", submitCreate);
  document.querySelector("#menu-toggle").addEventListener("click", () => {
    document.querySelector("#sidebar").classList.add("open");
    document.querySelector("#scrim").classList.add("menu-open");
  });
  document.querySelector("#scrim").addEventListener("click", closeOverlays);
  let timer;
  document.querySelector("#global-search").addEventListener("input", event => {
    clearTimeout(timer);
    timer = setTimeout(() => { state.filters = { search: event.target.value }; navigate("requests", false); }, 350);
  });
  document.addEventListener("keydown", event => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") { event.preventDefault(); document.querySelector("#global-search").focus(); }
    if (event.key === "Escape") closeOverlays();
  });
}

function setRoute(route) {
  state.route = route;
  document.querySelectorAll(".nav-link").forEach(link => link.classList.toggle("active", link.dataset.route === route));
  document.querySelector("#sidebar").classList.remove("open");
  document.querySelector("#scrim").classList.remove("menu-open");
}
async function navigate(route, reset = true) {
  if (reset) state.filters = {};
  state.page = 1; setRoute(route); loading();
  if (route === "dashboard") return showDashboard();
  if (route === "mine") state.filters.user_id = state.currentUser?.id;
  if (route === "overdue") state.filters.overdue = true;
  if (route === "critical") state.filters.priority = "critical";
  return showRequests();
}

function weekDays() {
  const today = new Date(); const weekday = today.getDay(); const monday = weekday === 0 ? -6 : 1 - weekday;
  return Array.from({ length: 7 }, (_, index) => {
    const date = new Date(today); date.setDate(today.getDate() + monday + index);
    const active = date.toDateString() === today.toDateString();
    const day = new Intl.DateTimeFormat("es-UY", { weekday: "short" }).format(date).replace(".", "");
    return `<div class="calendar-day ${active ? "today" : ""}"><span>${day}</span><b>${date.getDate()}</b></div>`;
  }).join("");
}
function taskCard(item, index) {
  const owner = item.assigned_user;
  const variant = index === 1 ? "dark" : index === 2 ? "orange" : "";
  return `<article class="task-card ${variant}" data-request-id="${item.id}">
    <div class="task-head"><div><small>${escapeHTML(item.category.name).toUpperCase()}</small><h3>${escapeHTML(item.title)}</h3></div><span>•••</span></div>
    <p>${escapeHTML(item.description)}</p>
    <div class="task-meta"><div class="owner">${owner ? `<span class="avatar" style="background:${avatarColor(owner)}">${initials(owner.name)}</span><div><small>Responsable</small><strong>${escapeHTML(owner.name)}</strong></div>` : '<span class="avatar">?</span><div><small>Responsable</small><strong>Sin asignar</strong></div>'}</div><span class="badge priority-${item.priority}">${labels.priority[item.priority]}</span></div>
    <div class="task-progress-label"><span>Progreso</span><b>${progress(item.status)}%</b></div><div class="progress"><i style="width:${progress(item.status)}%"></i></div>
  </article>`;
}
function activityRow(item) {
  const actor = item.actor?.name || "Sistema";
  return `<article class="timeline-row" data-request-id="${item.request_id}"><time>${new Intl.DateTimeFormat("es-UY", { hour: "2-digit", minute: "2-digit" }).format(new Date(item.created_at))}</time><div class="timeline-card"><div><strong>${sentence(labels.action[item.action] || "actualizó la solicitud")}</strong><p>${escapeHTML(actor)} · Solicitud #${String(item.request_id).padStart(4, "0")}</p></div><i>${svg("arrow")}</i></div></article>`;
}
function metric(title, value, note, icon) { return `<article class="metric"><div class="metric-head"><span>${title}</span><i class="metric-icon">${svg(icon)}</i></div><strong>${value}</strong><p>${note}</p></article>`; }
function donut(groups) {
  const total = groups.reduce((sum, item) => sum + item.value, 0); let cursor = 0;
  const segments = groups.map(item => { const start = cursor; cursor += total ? item.value / total * 100 : 0; return `${item.color} ${start}% ${cursor}%`; }).join(", ") || "#eceae4 0 100%";
  return `<div class="chart-body"><div class="donut" style="--segments:${segments}"><div class="donut-label"><strong>${total}</strong><small>Total</small></div></div><div class="legend">${groups.map(item => `<div class="legend-row"><i style="background:${item.color}"></i><span>${item.label}</span><b>${item.value}</b></div>`).join("")}</div></div>`;
}
function barChart(groups) {
  const max = Math.max(...groups.map(item => item.value), 1);
  const palette = ["#2563eb", "#60a5fa", "#1d4ed8", "#93c5fd", "#3b82f6"];
  return `<div class="chart-body"><div class="bars">${groups.map((item, index) => `<div class="bar-item"><b>${item.value}</b><i style="height:${Math.max(item.value / max * 110, 3)}px;--color:${palette[index % palette.length]}"></i><span>${escapeHTML(item.name)}</span></div>`).join("")}</div></div>`;
}

async function showDashboard() {
  setRoute("dashboard");
  try {
    const data = await api("/dashboard");
    document.querySelector("#open-badge").textContent = data.open_requests;
    const today = new Intl.DateTimeFormat("es-UY", { day: "numeric", month: "long", year: "numeric" }).format(new Date());
    document.querySelector("#content").innerHTML = `
      <section class="dashboard-frame">
        <div class="dashboard-main">
          <div class="greeting"><small>Hola, ${escapeHTML(state.currentUser?.name.split(" ")[0] || "equipo")}.</small><h1>Tenés<br><em>${data.open_requests} solicitudes abiertas</em></h1></div>
          <label class="dashboard-search">${svg("search")}<input type="search" placeholder="Buscar una solicitud..."></label>
          <div class="section-title"><div><h2>Trabajo reciente</h2><div class="tabs"><button class="active" data-quick="recent">Recientes</button><button data-quick="in_progress">En progreso</button><button data-quick="overdue">Vencidas</button><button data-quick="closed">Cerradas</button></div></div><button class="text-link" data-all>Ver todas →</button></div>
          <div class="task-stack">${data.recent_requests.slice(0, 4).map(taskCard).join("") || empty("Sin solicitudes", "Creá la primera solicitud para comenzar.")}</div>
        </div>
        <aside class="dashboard-side">
          <div class="today-head"><div><small>${today}</small><h2>Hoy</h2></div><button class="button button-black" data-new-inline>${svg("plus")} Crear</button></div>
          <div class="calendar">${weekDays()}</div>
          <div class="activity-head"><span>Actividad del equipo</span><button data-refresh aria-label="Actualizar">${svg("activity")}</button></div>
          <div class="timeline">${data.recent_activity.slice(0, 7).map(activityRow).join("") || empty("Sin actividad", "Los cambios aparecerán aquí.")}</div>
        </aside>
      </section>
      <section class="metric-strip">
        ${metric("Solicitudes abiertas", data.open_requests, "En atención ahora", "layers")}
        ${metric("Solicitudes vencidas", data.overdue_requests, "Requieren seguimiento", "alert")}
        ${metric("Resueltas este mes", data.resolved_this_month, "Cierre del período", "check")}
        ${metric("Tiempo abierto promedio", formatHours(data.average_open_hours), "Desde su creación", "clock")}
      </section>
      <section class="charts">
        <article class="panel"><header class="panel-head"><h3>Solicitudes por estado</h3><p>Distribución del flujo completo</p></header>${donut(data.by_status)}</article>
        <article class="panel"><header class="panel-head"><h3>Abiertas por prioridad</h3><p>Nivel de atención requerido</p></header>${donut(data.by_priority)}</article>
        <article class="panel"><header class="panel-head"><h3>Carga por departamento</h3><p>Solicitudes abiertas por área</p></header>${barChart(data.by_department)}</article>
      </section>`;
    bindOpenDetail(document.querySelector("#content"));
    document.querySelector("[data-all]").addEventListener("click", () => navigate("requests"));
    document.querySelector("[data-new-inline]").addEventListener("click", openModal);
    document.querySelector("[data-refresh]").addEventListener("click", showDashboard);
    document.querySelector(".dashboard-search input").addEventListener("keydown", event => {
      if (event.key === "Enter") { state.filters = { search: event.target.value }; navigate("requests", false); }
    });
    document.querySelectorAll("[data-quick]").forEach(button => button.addEventListener("click", () => {
      const quick = button.dataset.quick; state.filters = {};
      if (quick === "in_progress" || quick === "closed") state.filters.status = quick;
      if (quick === "overdue") state.filters.overdue = true;
      navigate("requests", false);
    }));
  } catch (error) { showFatal(error); }
}

function optionList(items, selected, placeholder, valueKey = "id", labelKey = "name") {
  return `${placeholder !== null ? `<option value="">${placeholder}</option>` : ""}${items.map(item => `<option value="${item[valueKey]}" ${String(item[valueKey]) === String(selected) ? "selected" : ""}>${escapeHTML(item[labelKey])}</option>`).join("")}`;
}
function queryString() {
  const params = new URLSearchParams({ page: state.page, page_size: 12 });
  Object.entries(state.filters).forEach(([key, value]) => { if (value !== "" && value !== null && value !== undefined) params.set(key, value); });
  return params.toString();
}
function requestRow(item) {
  const owner = item.assigned_user;
  return `<div class="request-row" data-request-id="${item.id}">
    <div class="request-name"><strong>#${String(item.id).padStart(4, "0")} · ${escapeHTML(item.title)}</strong><small>${escapeHTML(item.requesting_department.name)} · ${escapeHTML(item.category.name)}</small></div>
    <span class="badge status-${item.status}">${labels.status[item.status]}</span>
    <span class="badge priority-${item.priority}">${labels.priority[item.priority]}</span>
    <div class="assignee">${owner ? `<span class="avatar" style="background:${avatarColor(owner)}">${initials(owner.name)}</span><span>${escapeHTML(owner.name)}</span>` : '<span class="avatar">?</span><span>Sin asignar</span>'}</div>
    <span class="due ${item.is_overdue ? "overdue" : ""}">${item.is_overdue ? "Venció " : ""}${formatDate(item.due_at)}</span>
  </div>`;
}

async function showRequests() {
  try {
    const data = await api(`/requests?${queryString()}`);
    document.querySelector("#content").innerHTML = `
      <header class="page-head"><div><span class="kicker">CENTRO DE SOLICITUDES</span><h1>Solicitudes internas</h1><p>${data.total} resultados · seguimiento centralizado y auditable</p></div><button class="button button-orange" data-new-inline>${svg("plus")} Nueva solicitud</button></header>
      <section class="filters">
        <label class="filter-search">${svg("search")}<input data-filter="search" value="${escapeHTML(state.filters.search || "")}" placeholder="Buscar por título o descripción..."></label>
        <select data-filter="department_id">${optionList(state.catalogs.departments, state.filters.department_id, "Todos los departamentos")}</select>
        <select data-filter="status"><option value="">Todos los estados</option>${Object.entries(labels.status).map(([key, label]) => `<option value="${key}" ${state.filters.status === key ? "selected" : ""}>${label}</option>`).join("")}</select>
        <select data-filter="priority"><option value="">Todas las prioridades</option>${Object.entries(labels.priority).map(([key, label]) => `<option value="${key}" ${state.filters.priority === key ? "selected" : ""}>${label}</option>`).join("")}</select>
        <select data-filter="user_id">${optionList(state.catalogs.users, state.filters.user_id, "Todos los responsables")}</select>
      </section>
      <section class="request-table">
        <div class="table-head"><span>Solicitud</span><span>Estado</span><span>Prioridad</span><span>Responsable</span><span>Fecha límite</span></div>
        <div>${data.items.map(requestRow).join("") || empty("No hay coincidencias", "Probá cambiando o limpiando los filtros.")}</div>
        <footer class="pagination"><span>Página ${data.page} de ${data.pages}</span><div class="pages">${Array.from({ length: data.pages }, (_, i) => i + 1).slice(Math.max(0, data.page - 3), data.page + 2).map(page => `<button class="${page === data.page ? "active" : ""}" data-page="${page}">${page}</button>`).join("")}</div></footer>
      </section>`;
    bindOpenDetail(document.querySelector("#content"));
    document.querySelector("[data-new-inline]").addEventListener("click", openModal);
    document.querySelectorAll("[data-filter]").forEach(control => {
      const eventName = control.tagName === "INPUT" ? "input" : "change";
      let timer;
      control.addEventListener(eventName, () => {
        clearTimeout(timer); timer = setTimeout(() => { state.filters[control.dataset.filter] = control.value; state.page = 1; showRequests(); }, control.tagName === "INPUT" ? 300 : 0);
      });
    });
    document.querySelectorAll("[data-page]").forEach(button => button.addEventListener("click", () => { state.page = Number(button.dataset.page); showRequests(); }));
  } catch (error) { showFatal(error); }
}

function bindOpenDetail(root) { root.querySelectorAll("[data-request-id]").forEach(node => node.addEventListener("click", () => openDetail(node.dataset.requestId))); }
function statusOptions(current) {
  const allowed = {
    new: ["new", "assigned", "closed"], assigned: ["assigned", "new", "in_progress", "blocked", "resolved"],
    in_progress: ["in_progress", "assigned", "blocked", "resolved"], blocked: ["blocked", "assigned", "in_progress", "resolved"],
    resolved: ["resolved", "in_progress", "closed"], closed: ["closed", "in_progress"],
  }[current];
  return allowed.map(key => `<option value="${key}" ${key === current ? "selected" : ""}>${labels.status[key]}</option>`).join("");
}
function historyText(item) {
  const actor = item.actor?.name || "Sistema";
  const action = labels.action[item.action] || "actualizó la solicitud";
  const field = item.field ? ` · ${labels.field[item.field] || item.field}` : "";
  return `<strong>${escapeHTML(actor)}</strong> ${action}${field}`;
}
async function openDetail(id) {
  const drawer = document.querySelector("#drawer");
  drawer.innerHTML = '<div class="loading"><span></span><p>Cargando detalle...</p></div>';
  drawer.classList.add("open"); document.querySelector("#scrim").classList.add("open");
  try {
    const item = await api(`/requests/${id}`); const owner = item.assigned_user;
    drawer.innerHTML = `
      <header class="drawer-head"><span>SOLICITUD #${String(item.id).padStart(4, "0")}</span><button class="icon-btn" data-close-drawer aria-label="Cerrar">×</button></header>
      <div class="drawer-body">
        <span class="kicker">${escapeHTML(item.category.name).toUpperCase()}</span><h2>${escapeHTML(item.title)}</h2><p class="drawer-description">${escapeHTML(item.description)}</p>
        <div class="meta-row"><span class="badge status-${item.status}">${labels.status[item.status]}</span><span class="badge priority-${item.priority}">${labels.priority[item.priority]}</span><span class="badge ${item.is_overdue ? "priority-critical" : "priority-low"}">${item.is_overdue ? "Vencida" : formatDate(item.due_at)}</span></div>
        <div class="edit-grid">
          <label>Estado<select data-edit="status">${statusOptions(item.status)}</select></label>
          <label>Prioridad<select data-edit="priority">${Object.entries(labels.priority).map(([key, label]) => `<option value="${key}" ${key === item.priority ? "selected" : ""}>${label}</option>`).join("")}</select></label>
          <label>Responsable<select data-edit="assigned_user_id">${optionList(state.catalogs.users, owner?.id, "Sin asignar")}</select></label>
          <label>Departamento<select data-edit="requesting_department_id">${optionList(state.catalogs.departments, item.requesting_department.id, null)}</select></label>
        </div>
        <section class="drawer-section"><h3>Comentarios (${item.comments_count})</h3><form class="comment-form"><textarea rows="2" minlength="2" required placeholder="Escribí una actualización..."></textarea><button class="button button-orange" type="submit">Enviar</button></form>
          <div>${item.comments.map(comment => `<article class="comment"><span class="avatar" style="background:${avatarColor(comment.author)}">${initials(comment.author.name)}</span><div class="comment-body"><header><strong>${escapeHTML(comment.author.name)}</strong><time>${relativeTime(comment.created_at)}</time></header><p>${escapeHTML(comment.body)}</p></div></article>`).join("") || '<div class="empty"><p>Todavía no hay comentarios.</p></div>'}</div>
        </section>
        <section class="drawer-section"><h3>Historial completo</h3><div class="history">${item.history.map(entry => `<article class="history-row"><p>${historyText(entry)}</p><time>${formatDateTime(entry.created_at)}</time></article>`).join("")}</div></section>
      </div>`;
    drawer.querySelector("[data-close-drawer]").addEventListener("click", closeOverlays);
    drawer.querySelectorAll("[data-edit]").forEach(select => select.addEventListener("change", async () => {
      let value = select.value; if (select.dataset.edit === "assigned_user_id" || select.dataset.edit === "requesting_department_id") value = value ? Number(value) : null;
      select.disabled = true;
      try { await api(`/requests/${id}`, { method: "PATCH", body: JSON.stringify({ [select.dataset.edit]: value, actor_id: state.currentUser.id }) }); notify("Solicitud actualizada."); await openDetail(id); if (state.route === "dashboard") showDashboard(); }
      catch (error) { notify(error.message, "error"); select.disabled = false; await openDetail(id); }
    }));
    drawer.querySelector(".comment-form").addEventListener("submit", async event => {
      event.preventDefault(); const textarea = event.currentTarget.querySelector("textarea"); const button = event.currentTarget.querySelector("button"); button.disabled = true;
      try { await api(`/requests/${id}/comments`, { method: "POST", body: JSON.stringify({ author_id: state.currentUser.id, body: textarea.value }) }); notify("Comentario agregado."); await openDetail(id); }
      catch (error) { notify(error.message, "error"); button.disabled = false; }
    });
  } catch (error) { drawer.innerHTML = `<div class="empty"><strong>No pudimos abrir la solicitud</strong><p>${escapeHTML(error.message)}</p></div>`; }
}

function populateCreateForm() {
  const form = document.querySelector("#create-form");
  form.elements.category_id.innerHTML = optionList(state.catalogs.categories, null, "Seleccioná una categoría");
  form.elements.requesting_department_id.innerHTML = optionList(state.catalogs.departments, null, "Seleccioná un departamento");
  form.elements.assigned_user_id.innerHTML = optionList(state.catalogs.users, null, "Sin asignar");
}
function openModal() { document.querySelector("#create-modal").showModal(); }
function closeModal() { document.querySelector("#create-modal").close(); }
async function submitCreate(event) {
  event.preventDefault(); const form = event.currentTarget; const button = form.querySelector('[type="submit"]'); const data = Object.fromEntries(new FormData(form));
  data.category_id = Number(data.category_id); data.requesting_department_id = Number(data.requesting_department_id); data.assigned_user_id = data.assigned_user_id ? Number(data.assigned_user_id) : null; data.actor_id = state.currentUser.id;
  if (!data.due_at) data.due_at = null;
  button.disabled = true;
  try { const created = await api("/requests", { method: "POST", body: JSON.stringify(data) }); form.reset(); populateCreateForm(); closeModal(); notify("Solicitud creada correctamente."); await navigate("requests"); await openDetail(created.id); }
  catch (error) { notify(error.message, "error"); }
  finally { button.disabled = false; }
}
function closeOverlays() {
  document.querySelector("#drawer").classList.remove("open"); document.querySelector("#scrim").classList.remove("open", "menu-open"); document.querySelector("#sidebar").classList.remove("open");
}
function sentence(text) { return text.charAt(0).toUpperCase() + text.slice(1); }
function showFatal(error) { document.querySelector("#content").innerHTML = `<div class="empty"><i>${svg("alert")}</i><strong>No pudimos cargar OrangeFlow</strong><p>${escapeHTML(error.message)} Verificá la conexión con la base de datos.</p></div>`; }

document.addEventListener("DOMContentLoaded", start);
