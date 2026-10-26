import { el } from "#app/lib/dom.js";

export function populate(data, load, clientChanged) {
  const project = document.getElementById("f-proyecto");
  const client = document.getElementById("f-cliente");
  if (!project || !client || !data) return;
  const previousProject = project.value || "Todos los proyectos";
  const previousClient = client.value || "Todos los clientes";
  project.replaceChildren(
    el("option", { value: "Todos los proyectos" }, "Todos los proyectos"),
    ...(data.proyectos || []).map((p) =>
      el("option", { value: p.id }, `${p.id} - ${p.nombre}`),
    ),
  );
  client.replaceChildren(
    ...(data.clientes || ["Todos los clientes"]).map((c) =>
      el("option", {}, c),
    ),
  );
  if ([...project.options].some((o) => o.value === previousProject))
    project.value = previousProject;
  if ([...client.options].some((o) => o.value === previousClient))
    client.value = previousClient;
  project.onchange = load;
  client.onchange = clientChanged;
}

export function selectProject(id) {
  const project = document.getElementById("f-proyecto");
  const client = document.getElementById("f-cliente");
  if (project) {
    const wanted = id.trim().toLocaleLowerCase("es");
    const match = [...project.options].find(
      (o) => o.value.trim().toLocaleLowerCase("es") === wanted,
    );
    if (!match) project.append(el("option", { value: id }, id));
    project.value = match?.value || id;
  }
  if (client?.options.length) client.selectedIndex = 0;
}

export function selectAccount(account) {
  const client = document.getElementById("f-cliente");
  const project = document.getElementById("f-proyecto");
  if (client) {
    const wanted = account.trim().toLocaleLowerCase("es");
    const match = [...client.options].find(
      (option) => option.value.trim().toLocaleLowerCase("es") === wanted,
    );
    if (!match) client.append(el("option", { value: account }, account));
    client.value = match?.value || account;
  }
  if (project) project.value = "Todos los proyectos";
}

export function loading(target, title) {
  target.style.display = "block";
  target.replaceChildren(
    el(
      "div",
      { class: "legacy-project-head" },
      el(
        "div",
        {},
        el("h2", {}, title),
        el("p", { role: "status" }, "Consultando horas y etapas del proyecto…"),
      ),
      el("span", {}, "Consultando…"),
    ),
  );
}

export function failure(target, error, retry) {
  target.replaceChildren(
    el(
      "div",
      { class: "card" },
      el(
        "div",
        { style: { color: "var(--rojo)", fontWeight: "700" } },
        "Error cargando proyecto",
      ),
      el(
        "div",
        { style: { fontSize: "12px", marginTop: "6px" } },
        String(error?.message || error),
      ),
      el(
        "button",
        {
          class: "btn project-entry-retry",
          style: { marginTop: "12px" },
          onclick: retry,
        },
        "Reintentar",
      ),
    ),
  );
}

export function serverError(error) {
  console.error("Error del servidor:", error);
  const target = document.getElementById("view-container");
  target?.replaceChildren(
    el(
      "div",
      { class: "loading" },
      "Error cargando datos: " + (error?.message || JSON.stringify(error)),
    ),
  );
}
