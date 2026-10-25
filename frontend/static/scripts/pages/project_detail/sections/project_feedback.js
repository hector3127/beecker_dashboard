export function toast(message, type = "success") {
  const notice = document.createElement("div");
  notice.className = `aer-toast ${type}`;
  notice.textContent = message;
  document.body.appendChild(notice);
  requestAnimationFrame(() => notice.classList.add("show"));
  setTimeout(() => {
    notice.classList.remove("show");
    setTimeout(() => notice.remove(), 220);
  }, 1800);
}

export function saving(button, text = "Guardando...") {
  if (!button) return { ok() {}, error() {} };
  // Keep the original nodes so icons/text can be restored without parsing HTML.
  const original = [...button.childNodes];
  button.disabled = true;
  button.classList.add("saving");
  button.textContent = text;
  return {
    ok(message = "Guardado correctamente") {
      toast(message, "success");
    },
    error(message) {
      button.disabled = false;
      button.classList.remove("saving");
      button.replaceChildren(...original);
      if (message) toast(message, "error");
    },
  };
}

export function primary() {
  return (
    document.querySelector("#aer-modal-back .aer-actions .aer-btn.primary") ||
    document.querySelector(
      "#aer-modal-back .aer-gov-actions .aer-btn.primary",
    ) ||
    document.querySelector("#aer-modal-back .aer-btn.primary")
  );
}

export function close(wide = false) {
  document
    .getElementById(wide ? "aer-modal-wide-back" : "aer-modal-back")
    ?.remove();
}
