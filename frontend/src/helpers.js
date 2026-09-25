// ---------------------------------------------------------------------------
// helpers.js – shared pure utilities, no React imports
// ---------------------------------------------------------------------------

/**
 * Safely coerce a value to a finite number, returning null on failure.
 */
export const number = (value) => {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
};

/**
 * Format a numeric value to `digits` decimal places, or return '—'.
 */
export const fmt = (value, digits = 1) => {
  const n = number(value);
  return n === null ? '—' : n.toFixed(digits);
};

/**
 * Coerce a value to a boolean, handling string representations.
 */
export const bool = (v) => v === true || String(v).toLowerCase() === 'true';

/**
 * Squared Euclidean distance between a pixel row and a lat/lon point.
 * Used for nearest-pixel picking on map click.
 */
export const distance2 = (row, lat, lon) => {
  const x = number(row.lon) - lon;
  const y = number(row.lat) - lat;
  return x * x + y * y;
};

/**
 * Human-readable strategy labels keyed by strategy code.
 */
export const STRATEGY_LABELS = {
  GR:           'Government N120',
  N60:          'N60',
  N180:         'N180',
  N210:         'N210',
  TIMING_V6_V10:'V6/V10 timing',
  FYM_N60:      'FYM + N60',
  PCU_N120:     'PCU N120',
  PCU_N60:      'PCU N60',
  UDP_N78:      'UDP N78',
};

/**
 * Parse a GeoJSON FeatureCollection and return a flat array of row objects
 * with lat/lon extracted from geometry and all properties merged.
 * Only features with finite lat and lon are included.
 */
export const parseGeoJSON = (geo) => {
  return (geo.features || [])
    .map((f) => ({
      ...(f.properties || {}),
      lon: f.geometry?.coordinates?.[0],
      lat: f.geometry?.coordinates?.[1],
    }))
    .filter((r) => number(r.lat) !== null && number(r.lon) !== null);
};

/**
 * Find the row in `pool` closest to the given lat/lon (by squared distance).
 */
export const nearestRow = (pool, lat, lon) => {
  if (!pool.length) return null;
  let best = pool[0];
  let bestD = distance2(best, lat, lon);
  for (const row of pool.slice(1)) {
    const d = distance2(row, lat, lon);
    if (d < bestD) { best = row; bestD = d; }
  }
  return best;
};
