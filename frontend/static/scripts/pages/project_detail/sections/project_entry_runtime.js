// Direct project loads use modular renderers. Account/no-project fallbacks
// still come from compatibility until those branches are migrated.
export function createEntryRuntime(services) {
  let compatibility;
  const runtime = {
    connect(value) {
      compatibility = value;
      return runtime;
    },
    context() {
      return services.contexts.entry({
        previousStart: compatibility.previousStart,
        previousLoad: compatibility.previousLoad,
        clientChanged: compatibility.clientChanged,
        render: {
          aer: (data) => services.aer(data),
          ixs: (data) => services.ixs(data),
          executive: services.executive || compatibility.executive,
        },
      });
    },
    load() {
      return services.entry.load(runtime.context());
    },
  };
  return runtime;
}
