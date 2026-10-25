// State and lifecycle of the three AER panels; callbacks remain injectable
// until shared saving/notices and the compatibility entry are extracted.
export function createProjectPanels(store) {
  const base = (tab) => {
    const snapshot = store.aer;
    return {
      id: snapshot.proyecto.id,
      dashboard: snapshot,
      current: () => store.aer === snapshot,
      active: () => store.aerTab === tab,
    };
  };
  return {
    effort(callbacks) {
      return {
        ...base("esfuerzo"),
        ...callbacks,
        state: () => store.aerRecords,
        setState: (value) => {
          store.aerRecords = value;
        },
      };
    },
    planning(callbacks) {
      return {
        ...base("planeacion"),
        ...callbacks,
        range: () => store.aerPlanningRange,
        filters: () => store.aerPlanningFilters,
        setRange: (value) => {
          store.aerPlanningRange = value;
        },
        setFilters: (value) => {
          store.aerPlanningFilters = value;
        },
      };
    },
    resources(callbacks) {
      return {
        ...base("recursos"),
        ...callbacks,
        selected: (...args) =>
          args.length
            ? (store.aerResourceSelection = args[0])
            : store.aerResourceSelection,
      };
    },
  };
}
