// Static SVG paths from the existing project icon set.
export function iconSource(name) {
  const paths = {
    project:
      '<rect x="3" y="7" width="18" height="14" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
    calendar:
      '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/>',
    people:
      '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M16 3a4 4 0 0 1 0 8M22 21v-2a4 4 0 0 0-3-3.87"/><circle cx="9" cy="7" r="4"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
    chart: '<path d="M4 20v-7M10 20V9M16 20V4M22 20v-12"/>',
    layers:
      '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 7h10M7 12h10M7 17h7"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v6l4 2"/>',
    warning:
      '<path d="M10.3 3.9 2.3 18a2 2 0 0 0 1.7 3h16a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/>',
    flag: '<path d="M5 21V4m0 1c6-4 8 4 15 0v11c-7 4-9-4-15 0"/>',
    cash: '<circle cx="12" cy="12" r="9"/><path d="M15 8H11a2 2 0 0 0 0 4h2a2 2 0 0 1 0 4H9M12 6v12"/>',
    arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    refresh:
      '<path d="M20 7v5h-5M4 17v-5h5"/><path d="M5 9a8 8 0 0 1 14-2l1 5M4 12l1 5a8 8 0 0 0 14-2"/>',
    list: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
    sparkles:
      '<path d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3ZM20 17l.7 1.3L22 19l-1.3.7L20 21l-.7-1.3L18 19l1.3-.7L20 17Z"/>',
    megaphone:
      '<path d="M3 11v2l11 4V7L3 11Z"/><path d="M14 8c3-1 5-3 7-4v16c-2-1-4-3-7-4M5 16l2 5h3l-2-6"/>',
    target:
      '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    check: '<path d="M4 12l5 5L20 6"/>',
    link: '<path d="M10 13a5 5 0 0 0 7 .3l3-3a5 5 0 0 0-7-7l-2 2M14 11a5 5 0 0 0-7-.3l-3 3a5 5 0 0 0 7 7l2-2"/>',
    donut: '<path d="M12 2v10h10"/><path d="M20 15a9 9 0 1 1-11-11"/>',
    folder: '<path d="M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v10H3z"/>',
    dots: '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
  };
  return `<svg class="ixs-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.project}</svg>`;
}
export function icon(name) {
  // iconSource only interpolates a path from a fixed dictionary, never data.
  const document = new DOMParser().parseFromString(
    iconSource(name).replace(
      "<svg ",
      '<svg xmlns="http://www.w3.org/2000/svg" ',
    ),
    "image/svg+xml",
  );
  return document.documentElement;
}
