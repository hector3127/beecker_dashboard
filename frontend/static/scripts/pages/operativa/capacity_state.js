// @ts-check
/** Preserve a completed month while refreshing; never retain restricted data.
 * @param {any} previous
 * @param {any} incoming
 * @param {boolean} restricted
 */
export function capacityState(previous, incoming, restricted) {
  if (restricted || incoming === null) return null;
  const ready = previous && !previous.loading && !previous.error &&
    typeof previous.available === 'number' && Number.isFinite(previous.available);
  if (ready && previous.month === incoming?.month && (incoming?.loading || incoming?.error)) {
    return { ...previous, refresh_error: incoming.error || previous.refresh_error || '' };
  }
  return incoming;
}
