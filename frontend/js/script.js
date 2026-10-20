"use strict";

const API = "/api";
const currency = new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 });
const number = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 3 });
const $ = (selector) => document.querySelector(selector);
const state = { projects: [], budgets: [], budget: null, user: null, catalog: [], toastTimer: null };
const roleViews = {
  arquitecto: {
    label: "Arquitecto · editor",
    eyebrow: "ESPACIO DEL ARQUITECTO",
    title: "Planifica la obra",
    accent: "partida por partida.",
    description: "Construye el presupuesto del proyecto y ajusta sus insumos desde el catálogo.",
    project: "OBRA EN DESARROLLO",
    total: "COSTO ESTIMADO",
    count: "PARTIDAS DEL PRESUPUESTO",
    countFoot: "Insumos presupuestados",
    detailEyebrow: "COMPOSICIÓN DEL COSTO",
    detail: "Partidas del presupuesto",
    empty: "Elige una obra para revisar su presupuesto."
  },
  ingeniero: {
    label: "Ingeniero · editor",
    eyebrow: "CONTROL TÉCNICO",
    title: "Controla cantidades",
    accent: "y costos unitarios.",
    description: "Revisa cantidades, costos unitarios y totales; recalcula cuando ajustes una partida.",
    project: "OBRA EN SEGUIMIENTO",
    total: "COSTO CALCULADO",
    count: "PARTIDAS DEL CÁLCULO",
    countFoot: "Insumos en el cálculo",
    detailEyebrow: "REVISIÓN DE INSUMOS",
    detail: "Detalle técnico del presupuesto",
    empty: "Selecciona una obra para revisar sus cantidades y costos."
  },
  cliente: {
    label: "Cliente · consulta",
    eyebrow: "SEGUIMIENTO DE TU OBRA",
    title: "Consulta tu inversión,",
    accent: "partida por partida.",
    description: "Consulta el valor registrado, las partidas incluidas y la fecha del último cálculo.",
    project: "PROYECTO COMPARTIDO",
    total: "VALOR REGISTRADO",
    count: "PARTIDAS INCLUIDAS",
    countFoot: "Detalle disponible para consulta",
    detailEyebrow: "RESUMEN DE COSTOS",
    detail: "Partidas incluidas en el presupuesto",
    empty: "Selecciona el proyecto compartido para consultar sus costos."
  }
};

function applyRoleView(user) {
  const view = roleViews[user.rol] || roleViews.arquitecto;
  document.title = `ObraPresupuesto · ${view.label}`;
  $("#user-role").textContent = view.label;
  $("#role-eyebrow").firstChild.textContent = `${view.eyebrow} `;
  $("#role-title").textContent = view.title;
  $("#role-title-accent").textContent = view.accent;
  $("#role-description").textContent = view.description;
  $("#project-label").textContent = view.project;
  $("#total-label").textContent = view.total;
  $("#detail-eyebrow").textContent = view.detailEyebrow;
  $("#detail-title").textContent = view.detail;
  $("#table-caption").textContent = view.empty;
  $("#add-line").hidden = user.rol === "cliente";
  $("#duplicate").hidden = user.rol === "cliente";
  $("#recalculate").hidden = user.rol === "cliente";
  $("#new-project").hidden = !["arquitecto", "ingeniero"].includes(user.rol);
  $("#delete-project").hidden = !["arquitecto", "ingeniero"].includes(user.rol);
  if (user.rol === "arquitecto") {
    $("#add-line").textContent = "+ Añadir partida";
    $("#duplicate").innerHTML = "↗ <span>Duplicar versión</span>";
    $("#recalculate").innerHTML = "<span>↻</span> Recalcular costos";
  } else if (user.rol === "ingeniero") {
    $("#add-line").textContent = "+ Registrar insumo";
    $("#duplicate").innerHTML = "↗ <span>Duplicar presupuesto</span>";
    $("#recalculate").innerHTML = "<span>↻</span> Validar costos";
  }
}

function toast(message, isError = false) {
  const el = $("#toast");
  el.textContent = message;
  el.classList.toggle("error", isError);
  el.classList.add("visible");
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => el.classList.remove("visible"), 3200);
}

async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API}${path}`, { ...options, headers: { "Content-Type": "application/json", ...(options.headers || {}) } });
  } catch {
    $("#connection-label").textContent = "API sin conexión";
    $(".topbar-right").classList.add("connection-error");
    throw new Error("No se pudo conectar con la API. Inicia el servidor Flask en 127.0.0.1:5000 y vuelve a intentar.");
  }
  const payload = response.status === 204 ? null : await response.json().catch(() => ({}));
  if (response.status === 401) window.location.assign("/login");
  if (!response.ok) throw new Error(payload?.error || `Error ${response.status} al consultar la API.`);
  return payload;
}

function setBusy(button, busy, label) {
  if (busy) {
    button.dataset.label = button.innerHTML;
    button.disabled = true;
    button.innerHTML = label;
  } else {
    button.innerHTML = button.dataset.label || label;
    button.disabled = false;
  }
}

async function loadProjects(preferredId) {
  const select = $("#project-select");
  state.projects = await api("/proyectos");
  select.replaceChildren();
  if (!state.projects.length) {
    state.budgets = [];
    state.budget = null;
    select.add(new Option("Aún no hay proyectos", ""));
    $("#client-label").textContent = "Crea un proyecto para empezar a presupuestar.";
    renderEmpty("Todavía no hay proyectos registrados.");
    $("#total").textContent = currency.format(0);
    $("#table-total").textContent = currency.format(0);
    $("#line-count").textContent = "00";
    $("#budget-date").textContent = "—";
    $("#budget-title").textContent = "Sin proyectos";
    $("#current-project-name").textContent = "Aún no hay proyectos";
    $("#current-project-city").textContent = "Crea una obra para elegir ciudad";
    $("#current-project-client").textContent = "Cliente no indicado";
    $("#current-project-owner").textContent = state.user?.nombre_completo || "—";
    renderCostSummary([]);
    setActions(false);
    $("#project-select").disabled = true;
    return;
  }
  select.disabled = false;
  state.projects.forEach((project) => select.add(new Option(`${project.nombre_obra} \u00b7 ${project.ciudad || "Bogot\u00e1"}`, project.id_proyecto)));
  select.value = String(preferredId || state.projects[0].id_proyecto);
  await loadBudgets(select.value);
}

async function loadBudgets(projectId, preferredBudgetId) {
  const project = state.projects.find((item) => String(item.id_proyecto) === String(projectId));
  $("#invite-collaborator").hidden = !(["arquitecto", "ingeniero"].includes(state.user?.rol) && project?.es_propietario);
  $("#delete-project").hidden = !( ["arquitecto", "ingeniero"].includes(state.user?.rol) && project?.es_propietario);
  $("#client-label").textContent = [project?.ciudad, project?.cliente, project?.responsable].filter(Boolean).join(" · ") || "Responsable de proyecto";
  $("#current-project-name").textContent = project?.nombre_obra || "Selecciona un proyecto";
  $("#current-project-city").textContent = project?.ciudad || "Ciudad no registrada";
  $("#current-project-client").textContent = project?.cliente || "Cliente no indicado";
  $("#current-project-owner").textContent = project?.responsable || state.user?.nombre_completo || "—";
  const select = $("#budget-select");
  select.disabled = true;
  select.replaceChildren();
  state.budgets = await api(`/presupuestos?id_proyecto=${encodeURIComponent(projectId)}`);
  if (!state.budgets.length && ["arquitecto", "ingeniero"].includes(state.user?.rol)) {
    const initialBudget = await api("/presupuestos", {
      method: "POST",
      body: JSON.stringify({ id_proyecto: Number(projectId) }),
    });
    state.budgets = [initialBudget];
  }
  if (!state.budgets.length) {
    select.add(new Option("Sin presupuestos", ""));
    state.budget = null;
    $("#budget-title").textContent = "Sin presupuestos registrados";
    $("#total").textContent = currency.format(0);
    $("#table-total").textContent = currency.format(0);
    $("#line-count").textContent = "0";
    $("#budget-date").textContent = "—";
    renderCostSummary([]);
    $("#table-caption").textContent = "Crea un presupuesto desde la API para este proyecto.";
    renderEmpty("Este proyecto todavía no tiene presupuestos.");
    setActions(false);
    return;
  }
  state.budgets.forEach((budget, index) => select.add(new Option(`Presupuesto ${state.budgets.length - index} · ${formatDate(budget.fecha_calculo)} · ${currency.format(budget.costo_total)}`, budget.id_presupuesto)));
  select.disabled = false;
  select.value = String(preferredBudgetId || state.budgets[0].id_presupuesto);
  await loadBudget(select.value);
}

async function loadBudget(id) {
  if (!id) return;
  const budget = await api(`/presupuestos/${id}`);
  state.budget = budget;
  renderBudget(budget);
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(`${String(value).slice(0, 10)}T12:00:00`);
  return Number.isNaN(date.getTime()) ? String(value) : new Intl.DateTimeFormat("es-CO", { day: "numeric", month: "short", year: "numeric" }).format(date);
}

function renderEmpty(message) {
  $("#lines").replaceChildren();
  const row = document.createElement("tr");
  const cell = document.createElement("td");
  cell.colSpan = 6;
  cell.className = "empty";
  cell.textContent = message;
  row.append(cell);
  $("#lines").append(row);
}

function renderBudget(budget) {
  const lines = Array.isArray(budget.detalle) ? budget.detalle : [];
  renderCostSummary(lines);
  $("#total").textContent = currency.format(Number(budget.costo_total) || 0);
  $("#table-total").textContent = currency.format(Number(budget.costo_total) || 0);
  $("#line-count").textContent = String(lines.length).padStart(2, "0");
  $("#budget-date").textContent = formatDate(budget.fecha_calculo);
  $("#budget-title").textContent = budget.nombre_obra || "Presupuesto seleccionado";
  $("#table-caption").textContent = `${lines.length} ${lines.length === 1 ? "partida" : "partidas"} · ${budget.nombre_obra || "Proyecto"}`;
  const tbody = $("#lines");
  tbody.replaceChildren();
  setActions(true);
  if (!lines.length) return renderEmpty("Este presupuesto todavía no tiene partidas.");
  lines.forEach((line) => {
    const row = document.createElement("tr");
    const name = document.createElement("td"); name.textContent = line.nombre_insumo;
    const unit = document.createElement("td"); unit.textContent = line.unidad_medida;
    const quantity = document.createElement("td"); quantity.className = "numeric"; quantity.textContent = number.format(Number(line.cantidad));
    const price = document.createElement("td"); price.className = "numeric"; price.textContent = currency.format(Number(line.costo_unitario_aplicado));
    const subtotal = document.createElement("td"); subtotal.className = "numeric"; subtotal.textContent = currency.format(Number(line.subtotal));
    const actions = document.createElement("td");
    if (state.user?.rol !== "cliente") {
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "remove-line";
      remove.textContent = "×";
      remove.setAttribute("aria-label", `Quitar ${line.nombre_insumo} del presupuesto`);
      remove.addEventListener("click", () => removeLine(line.id_detalle));
      actions.append(remove);
    }
    row.append(name, unit, quantity, price, subtotal, actions);
    tbody.append(row);
  });
}

function renderCostSummary(lines) {
  let labor = 0;
  let materials = 0;
  lines.forEach((line) => {
    const name = String(line.nombre_insumo || "").toLocaleLowerCase("es-CO");
    const unit = String(line.unidad_medida || "").toLocaleLowerCase("es-CO").trim();
    const subtotal = Number(line.subtotal) || (Number(line.cantidad) * Number(line.costo_unitario_aplicado)) || 0;
    const isLabor = /mano de obra|oficial|ayudante|operario|trabajador|salario|maestro/.test(name)
      || /^(jornal|hora|horas|d\u00eda|dia|d\u00edas|dias)$/.test(unit);
    if (isLabor) labor += subtotal;
    else materials += subtotal;
  });
  const total = materials + labor;
  const laborPercent = total ? Math.round((labor / total) * 100) : 0;
  const materialPercent = total ? 100 - laborPercent : 0;
  $("#materials-total").textContent = currency.format(materials);
  $("#labor-total").textContent = currency.format(labor);
  $("#materials-chart-total").textContent = currency.format(materials);
  $("#labor-chart-total").textContent = currency.format(labor);
  $("#materials-share").textContent = `${materialPercent}% del total`;
  $("#labor-share").textContent = `${laborPercent}% del total`;
  $("#chart-count").textContent = String(lines.length).padStart(2, "0");
  $("#cost-donut").style.setProperty("--labor-share", `${laborPercent}%`);
  $("#cost-donut").setAttribute("aria-label", `Materiales y otros: ${materialPercent} por ciento. Mano de obra: ${laborPercent} por ciento.`);
}

function setActions(enabled) {
  const canEdit = enabled && state.user?.rol !== "cliente";
  $("#add-line").disabled = !canEdit;
  $("#add-line").hidden = state.user?.rol === "cliente";
  $("#duplicate").disabled = !canEdit;
  $("#duplicate").hidden = state.user?.rol === "cliente";
  $("#recalculate").disabled = !canEdit;
  $("#recalculate").hidden = state.user?.rol === "cliente";
}

async function openAddDialog() {
  try {
    const project = state.projects.find((item) => String(item.id_proyecto) === String($("#project-select").value));
    const city = project?.ciudad || "Bogot\u00e1";
    const catalog = await api(`/insumos?ciudad=${encodeURIComponent(city)}`);
    state.catalog = catalog;
    const select = $("#insumo-select");
    select.replaceChildren(new Option("Selecciona un insumo", ""));
    catalog.forEach((item) => {
      const hasPrice = Number(item.costo_unitario) > 0;
      const source = item.origen_precio === "precio_ciudad" ? `precio para ${city}` : "referencia general; validar valor local";
      const option = new Option(
        `${item.nombre_insumo} \u00b7 ${item.unidad_medida} \u00b7 ${hasPrice ? currency.format(Number(item.costo_unitario)) : "sin precio"} \u00b7 ${source}`,
        item.id_insumo);
      option.disabled = !hasPrice;
      select.add(option);
    });
    $("#item-city-label").textContent = city;
    $("#price-city-note").textContent = `Se aplican los precios registrados para ${city}. Las referencias generales no tienen verificacion local; confirma su vigencia.`;
    if (!catalog.length) select.add(new Option("No hay insumos con precio cargado", ""));
    $("#add-form").reset();
    resetNewItemMode();
    $("#add-dialog").showModal();
    select.focus();
  } catch (error) { toast(error.message, true); }
}

async function removeLine(idDetalle) {
  if (!state.budget || !window.confirm("¿Quitar esta partida del presupuesto?")) return;
  try {
    const budget = await api(`/presupuestos/${state.budget.id_presupuesto}/detalle/${idDetalle}`, { method: "DELETE" });
    renderBudget(budget);
    toast("Partida eliminada del presupuesto.");
  } catch (error) { toast(error.message, true); }
}

async function refresh() {
  const projectId = $("#project-select").value;
  const budgetId = $("#budget-select").value;
  const button = $("#refresh"); button.disabled = true;
  try {
    $("#connection-label").textContent = "Sincronizando…";
    await loadProjects(projectId || undefined);
    if (projectId && $("#project-select").value === projectId && budgetId) {
      const selected = state.budgets.find((budget) => String(budget.id_presupuesto) === budgetId);
      if (selected) await loadBudget(budgetId);
    }
    $("#connection-label").textContent = "Datos sincronizados";
    $(".topbar-right").classList.remove("connection-error");
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; }
}

$("#project-select").addEventListener("change", async (event) => {
  try { await loadBudgets(event.target.value); } catch (error) { toast(error.message, true); }
});
$("#delete-project").addEventListener("click", async () => {
  const project = state.projects.find((item) => String(item.id_proyecto) === String($("#project-select").value));
  if (!project) return;
  const confirmed = window.confirm(`\u00bfEliminar el proyecto "${project.nombre_obra}" y todos sus presupuestos y partidas? Esta acci\u00f3n no se puede deshacer.`);
  if (!confirmed) return;
  const button = $("#delete-project");
  button.disabled = true;
  try {
    await api(`/proyectos/${project.id_proyecto}`, { method: "DELETE" });
    await loadProjects();
    toast("Proyecto y presupuestos eliminados.");
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; }
});
$("#new-project").addEventListener("click", () => {
  $("#project-form").reset();
  $("#project-dialog").showModal();
  $("#project-name").focus();
});
$("#invite-collaborator").addEventListener("click", async () => {
  const projectId = $("#project-select").value;
  const email = window.prompt("Correo de la cuenta registrada del arquitecto o ingeniero:");
  if (!projectId || !email?.trim()) return;
  const button = $("#invite-collaborator");
  button.disabled = true;
  try {
    const result = await api(`/proyectos/${projectId}/colaboradores`, {
      method: "POST", body: JSON.stringify({ email: email.trim() }),
    });
    toast(result.mensaje || "Colaborador agregado al proyecto.");
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; }
});
$("#close-project").addEventListener("click", () => $("#project-dialog").close());
$("#cancel-project").addEventListener("click", () => $("#project-dialog").close());
$("#project-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.currentTarget.querySelector('button[type="submit"]');
  button.disabled = true;
  try {
    const project = await api("/proyectos", {
      method: "POST",
      body: JSON.stringify({ nombre_obra: $("#project-name").value.trim(), ciudad: $("#project-city").value, cliente: $("#project-client").value.trim() || null }),
    });
    $("#project-dialog").close();
    await loadProjects(project.id_proyecto);
    toast("Proyecto iniciado. Ya puedes agregar partidas al presupuesto.");
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; }
});
$("#budget-select").addEventListener("change", async (event) => {
  try { await loadBudget(event.target.value); } catch (error) { toast(error.message, true); }
});
$("#add-line").addEventListener("click", openAddDialog);
$("#close-add").addEventListener("click", () => $("#add-dialog").close());
$("#cancel-add").addEventListener("click", () => $("#add-dialog").close());
function resetNewItemMode() {
  $("#new-item-fields").hidden = true;
  $("#insumo-select").hidden = false;
  $("#new-item-toggle").hidden = false;
  $("#new-item-toggle").textContent = "+ Crear un insumo para esta ciudad";
  $("#insumo-select").required = true;
  $("#new-item-name").required = false;
  $("#new-item-unit").required = false;
  $("#new-item-price").required = false;
}
$("#new-item-toggle").addEventListener("click", () => {
  const selected = state.catalog.find((item) => String(item.id_insumo) === $("#insumo-select").value);
  if (selected) {
    $("#new-item-name").value = selected.nombre_insumo;
    $("#new-item-unit").value = selected.unidad_medida;
    $("#new-item-price").value = Number(selected.costo_unitario) > 0 ? selected.costo_unitario : "";
  }
  $("#new-item-fields").hidden = false;
  $("#insumo-select").hidden = true;
  $("#new-item-toggle").hidden = true;
  $("#insumo-select").required = false;
  $("#new-item-name").required = true;
  $("#new-item-unit").required = true;
  $("#new-item-price").required = true;
  $("#new-item-name").focus();
});
$("#add-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.budget) return;
  const button = $("#save-line");
  button.disabled = true;
  try {
    let idInsumo = Number($("#insumo-select").value);
    if (!$("#new-item-fields").hidden) {
      const project = state.projects.find((item) => String(item.id_proyecto) === String($("#project-select").value));
      const created = await api("/insumos", { method: "POST", body: JSON.stringify({
        nombre_insumo: $("#new-item-name").value.trim(),
        unidad_medida: $("#new-item-unit").value.trim(),
        costo_unitario: Number($("#new-item-price").value), ciudad: project?.ciudad || "Bogot\u00e1"
      }) });
      idInsumo = created.id_insumo;
    }
    const budget = await api(`/presupuestos/${state.budget.id_presupuesto}/detalle`, {
      method: "POST",
      body: JSON.stringify({ id_insumo: idInsumo, cantidad: Number($("#quantity-input").value) }),
    });
    renderBudget(budget);
    $("#add-dialog").close();
    $("#add-form").reset();
    resetNewItemMode();
    toast("Insumo agregado al presupuesto.");
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; }
});

$("#refresh").addEventListener("click", refresh);
$("#print").addEventListener("click", () => window.print());

$("#recalculate").addEventListener("click", async (event) => {
  if (!state.budget) return;
  const button = event.currentTarget;
  setBusy(button, true, "Recalculando…");
  try {
    await api(`/presupuestos/${state.budget.id_presupuesto}/calcular`, { method: "POST" });
    await loadBudget(state.budget.id_presupuesto);
    toast("Presupuesto recalculado correctamente.");
  } catch (error) { toast(error.message, true); }
  finally { setBusy(button, false); }
});

$("#duplicate").addEventListener("click", async (event) => {
  if (!state.budget) return;
  const button = event.currentTarget;
  setBusy(button, true, "Duplicando…");
  try {
    const copy = await api(`/presupuestos/${state.budget.id_presupuesto}/duplicar`, { method: "POST", body: JSON.stringify({}) });
    await loadBudgets($("#project-select").value, copy.id_presupuesto);
    toast("Copia creada con los precios vigentes del catálogo.");
  } catch (error) { toast(error.message, true); }
  finally { setBusy(button, false); }
});

$("#today").textContent = new Intl.DateTimeFormat("es-CO", { weekday: "long", day: "numeric", month: "long" }).format(new Date()).toUpperCase();
$("#logout").addEventListener("click", async () => {
  try { await api("/auth/logout", { method: "POST" }); } finally { window.location.assign("/login"); }
});
api("/auth/sesion").then((user) => {
  state.user = user;
  $("#user-name").textContent = user.nombre_completo;
  applyRoleView(user);
  $("#user-avatar").textContent = user.nombre_completo.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
  $("#connection-label").textContent = "API conectada";
  $(".topbar-right").classList.remove("connection-error");
  return loadProjects();
}).catch((error) => {
  if (/Inicia sesión|sesión ya no es válida/i.test(error.message)) return window.location.assign("/login");
  $("#connection-label").textContent = "API sin conexión";
  $(".topbar-right").classList.add("connection-error");
  renderEmpty("No hay conexión con la API. Inicia Flask y pulsa actualizar.");
  $("#api-hint").textContent = "API local · 127.0.0.1:5000";
  toast(error.message, true);
});
