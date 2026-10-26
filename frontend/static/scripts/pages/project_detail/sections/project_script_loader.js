// Keep evaluated compatibility scripts across UI retries; failed downloads retry.
export function createProjectScriptLoader(documentRoot = document) {
  const pending = new Map();
  return (src, manual = false) => {
    if (pending.has(src)) return pending.get(src);
    const script = documentRoot.createElement("script");
    script.src = src;
    if (manual) script.dataset.projectBootstrap = "manual";
    const promise = new Promise((resolve, reject) => {
      script.onload = () => resolve();
      script.onerror = () => {
        script.remove();
        pending.delete(src);
        reject(new Error("No se pudo cargar la interfaz del proyecto."));
      };
    });
    pending.set(src, promise);
    documentRoot.head.append(script);
    return promise;
  };
}
