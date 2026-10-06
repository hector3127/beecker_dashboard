/*
 * BKD.006.004 - Adaptador google.script.run
 *
 * Imita la API de Apps Script para que js_main.html funcione sin
 * cambios: cada llamada google.script.run.miFuncion(a, b) se convierte
 * en POST /api/rpc/miFuncion/ con el cuerpo {"args": [a, b]}.
 * Si la funcion todavia no se migra, se llama al withFailureHandler.
 */
(function installAppsScriptShim(globalScope) {
  "use strict";

  const RPC_BASE_URL = "/api/rpc/";

  function readCsrfToken() {
    const cookie = document.cookie
      .split(";")
      .map((part) => part.trim())
      .find((part) => part.startsWith("csrftoken="));

    return cookie ? decodeURIComponent(cookie.split("=")[1]) : "";
  }

  function buildServerError(message, code) {
    const error = new Error(message || "Error desconocido del servidor.");
    error.code = code || "ERR_UNKNOWN";
    return error;
  }

  async function callServer(functionName, args) {
    const response = await fetch(
      RPC_BASE_URL + encodeURIComponent(functionName) + "/",
      {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": readCsrfToken(),
        },
        body: JSON.stringify({ args: args }),
      },
    );

    let payload = null;

    try {
      payload = await response.json();
    } catch (parseError) {
      throw buildServerError(
        "El servidor respondio " + response.status + " sin JSON.",
        "ERR_INVALID_RESPONSE",
      );
    }

    if (!response.ok || !payload || payload.ok !== true) {
      throw buildServerError(payload && payload.message, payload && payload.code);
    }

    return payload.result;
  }

  function createRunner(handlers) {
    return new Proxy(
      {},
      {
        get(target, propertyName) {
          if (propertyName === "withSuccessHandler") {
            return (callback) =>
              createRunner({ ...handlers, success: callback });
          }

          if (propertyName === "withFailureHandler") {
            return (callback) =>
              createRunner({ ...handlers, failure: callback });
          }

          if (propertyName === "withUserObject") {
            return (userObject) =>
              createRunner({ ...handlers, userObject: userObject });
          }

          if (typeof propertyName !== "string") {
            return undefined;
          }

          return (...args) => {
            callServer(propertyName, args)
              .then((result) => {
                if (handlers.success) {
                  handlers.success(result, handlers.userObject);
                }
              })
              .catch((error) => {
                if (handlers.failure) {
                  handlers.failure(error, handlers.userObject);
                  return;
                }

                console.error(
                  "[gas_shim] " + propertyName + " fallo:",
                  error,
                );
              });
          };
        },
      },
    );
  }

  globalScope.google = globalScope.google || {};
  globalScope.google.script = {
    run: createRunner({}),
    host: {
      close() {
        globalScope.close();
      },
    },
  };
})(window);
