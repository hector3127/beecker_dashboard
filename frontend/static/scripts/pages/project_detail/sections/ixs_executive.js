import {
  renderExecutive,
  renderRaid,
  renderTasks,
  timeline,
  resourceTable,
} from "./ixs_executive_view.js";

export { resourceTable };

export function updateTimeline(target, data) {
  target.replaceChildren(timeline(data));
}

/** Mount deferred reads only for the project and pane that requested them. */
export function mountIxsExecutive(target, data, api, lifecycle) {
  renderExecutive(target, data);
  const current = () =>
    target.isConnected && lifecycle.current(data) && lifecycle.active();
  const risks = target.querySelector("#ixs-risks-content");
  const tasks = target.querySelector("#ixs-tasks-content");
  api
    .raid(data.proyecto.id)
    .then((result) => {
      if (current()) renderRaid(risks, result);
    })
    .catch((error) => {
      if (current())
        risks.textContent = "Error Azure: " + (error?.message || error);
    });
  api
    .tasks(data.proyecto.id)
    .then((result) => {
      if (current()) renderTasks(tasks, result);
    })
    .catch((error) => {
      if (current())
        tasks.textContent = "Error Clockify: " + (error?.message || error);
    });
}
