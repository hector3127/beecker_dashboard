import { azureGroups, matchesPerson } from "./ixs_azure_groups_model.js";
import { groupViews, groupDrawer } from "./ixs_azure_groups_view.js";

export function createAzureGroupsController() {
  const escape = (event) => {
    if (event.key === "Escape") close();
  };
  function close() {
    document.getElementById("ixs-az84-drawer-wrap")?.remove();
    window.removeEventListener("keydown", escape);
  }
  return {
    close,
    render(state) {
      const people = document.getElementById("ixs-az84-person"),
        stages = document.getElementById("ixs-az84-stage");
      if (!people || !stages) return;
      const groups = azureGroups(state);
      function open(items, title, subtitle) {
        close();
        const drawer = groupDrawer(
          state.projectId,
          items,
          title,
          subtitle,
          close,
        );
        document.body.append(drawer);
        drawer.querySelector(".ixs-az84-close")?.focus();
        window.addEventListener("keydown", escape);
      }
      const views = groupViews(groups, state, {
        person: (i) =>
          open(
            groups.people[i].items,
            "Ítems por persona",
            groups.people[i].persona,
          ),
        stage: (i) =>
          open(
            groups.stages[i].items,
            "WIs abiertos por etapa",
            groups.stages[i].etapa,
          ),
        iteration: (i, j) => {
          const p = groups.people[i],
            row = p.iteraciones[j];
          open(
            row.items,
            "Ítems por persona / iteración",
            p.persona + " · " + row.etapa,
          );
        },
        filter: (query, cards) =>
          cards.forEach((card, i) => {
            card.hidden = !matchesPerson(groups.people[i], query);
            if (String(query || "").trim() && !card.hidden) card.open = true;
          }),
      });
      people.replaceChildren(...views.people);
      stages.replaceChildren(...views.stages);
    },
  };
}
