// A project page is bound to its path ID. The previous dashboard's account
// navigation lives on its own page; it is not a fallback of this route.
export function createEntryRuntime(services) {
  let compatibility;
  const runtime = {
    connect(value) {
      compatibility = value;
      return runtime;
    },
    context() {
      const callbacks = compatibility || {
        previousStart: () =>
          services.entry.startCompatibility(runtime.context()),
        previousLoad: () => services.entry.restoreProject(runtime.context()),
        clientChanged: () => services.entry.restoreProject(runtime.context()),
      };
      return services.contexts.entry({
        previousStart: callbacks.previousStart,
        previousLoad: callbacks.previousLoad,
        clientChanged: callbacks.clientChanged,
        render: {
          aer: (data) => services.aer(data),
          ixs: (data) => services.ixs(data),
          executive: services.executive || callbacks.executive,
        },
      });
    },
    load() {
      return services.entry.load(runtime.context());
    },
  };
  return runtime;
}
