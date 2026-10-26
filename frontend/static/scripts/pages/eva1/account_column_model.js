// @ts-check
/** @param {string} name @returns {string} */
export function accountInitials(name) {
  return (
    name
      .trim()
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((word) => word[0])
      .join("")
      .toUpperCase() || "—"
  );
}
