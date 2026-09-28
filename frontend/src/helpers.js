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

/**
 * Dynamically evaluate cross-site trade-offs across 4R strategies
 * directly from loaded parcel/trial records (never hardcoded in JSX).
 */
export const evaluateStrategyTradeoffs = (rows = []) => {
  if (!rows || !rows.length) return [];
  const stratMap = {};

  rows.forEach((r) => {
    const s = r.strategy;
    if (!s) return;
    if (!stratMap[s]) {
      stratMap[s] = {
        strategy: s,
        label: STRATEGY_LABELS[s] || s,
        total: 0,
        yieldDiffs: [],
        testedNDiffs: [],
        nReductions: [],
        nIncreases: [],
        retains95Count: 0,
        stratNRates: [],
        aes: [],
      };
    }
    const entry = stratMap[s];
    entry.total += 1;

    const yd = number(r.predicted_yield_difference_from_GR_t_ha);
    if (yd !== null) entry.yieldDiffs.push(yd);

    const tn = number(r.tested_N_change_vs_GR_kg_ha);
    if (tn !== null) entry.testedNDiffs.push(tn);

    const nr = number(r.N_reduction_for_same_target_yield_kg_ha);
    if (nr !== null) entry.nReductions.push(nr);

    const ni = number(r.N_increase_for_same_target_yield_kg_ha);
    if (ni !== null) entry.nIncreases.push(ni);

    const sn = number(r.strategy_N_rate_kg_ha);
    if (sn !== null) entry.stratNRates.push(sn);

    const ae = number(r.predicted_AE_N_kg_grain_per_kg_N);
    if (ae !== null) entry.aes.push(ae);

    const ret = number(r.predicted_yield_retention_fraction);
    if (bool(r.retains_95pct_GR) || (ret !== null && ret >= 0.95)) {
      entry.retains95Count += 1;
    }
  });

  const avg = (arr) => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : null;

  const ORDER = ['N60', 'UDP_N78', 'PCU_N60', 'TIMING_V6_V10', 'FYM_N60', 'GR', 'N180', 'N210', 'PCU_N120'];

  return Object.values(stratMap).map((d) => {
    const negYieldCount = d.yieldDiffs.filter((v) => v < 0).length;
    const posYieldCount = d.yieldDiffs.filter((v) => v > 0).length;
    const meanYieldDiff = avg(d.yieldDiffs);
    const meanTestedN = avg(d.testedNDiffs);
    const meanNRed = avg(d.nReductions);
    const meanNInc = avg(d.nIncreases);

    return {
      strategy: d.strategy,
      label: d.label,
      totalParcels: d.total,
      meanYieldDiff,
      minYieldDiff: d.yieldDiffs.length ? Math.min(...d.yieldDiffs) : null,
      maxYieldDiff: d.yieldDiffs.length ? Math.max(...d.yieldDiffs) : null,
      negYieldCount,
      negYieldPct: d.total ? (negYieldCount / d.total) * 100 : 0,
      posYieldCount,
      posYieldPct: d.total ? (posYieldCount / d.total) * 100 : 0,
      retains95Count: d.retains95Count,
      retains95Pct: d.total ? (d.retains95Count / d.total) * 100 : 0,
      meanTestedN,
      meanNRed,
      meanNInc,
      meanNBal: meanTestedN !== null ? meanTestedN : (meanNRed ? -meanNRed : (meanNInc || 0)),
      meanStrategyNRate: avg(d.stratNRates),
      meanAE: avg(d.aes),
    };
  }).sort((a, b) => {
    const idxA = ORDER.indexOf(a.strategy);
    const idxB = ORDER.indexOf(b.strategy);
    return (idxA !== -1 ? idxA : 99) - (idxB !== -1 ? idxB : 99);
  });
};

/**
 * Dynamically evaluate district-level contrasts from loaded parcel records.
 */
export const evaluateDistrictTradeoffs = (rows = []) => {
  if (!rows || !rows.length) return [];
  const distMap = {};

  rows.forEach((r) => {
    const d = r.district || r.District;
    if (!d) return;
    if (!distMap[d]) {
      distMap[d] = {
        district: d,
        total: 0,
        yieldDiffs: [],
        strategies: {},
      };
    }
    const entry = distMap[d];
    entry.total += 1;

    const yd = number(r.predicted_yield_difference_from_GR_t_ha);
    if (yd !== null) entry.yieldDiffs.push(yd);

    const s = r.strategy;
    if (s) {
      if (!entry.strategies[s]) entry.strategies[s] = [];
      if (yd !== null) entry.strategies[s].push(yd);
    }
  });

  const avg = (arr) => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : null;

  return Object.values(distMap).map((item) => {
    const negCount = item.yieldDiffs.filter((v) => v < 0).length;
    const stratBreakdown = {};
    Object.entries(item.strategies).forEach(([strat, yds]) => {
      stratBreakdown[strat] = {
        count: yds.length,
        meanYieldDiff: avg(yds),
        negPct: yds.length ? (yds.filter((v) => v < 0).length / yds.length) * 100 : 0,
      };
    });

    return {
      district: item.district,
      totalParcels: item.total,
      meanYieldDiff: avg(item.yieldDiffs),
      negYieldPct: item.total ? (negCount / item.total) * 100 : 0,
      strategies: stratBreakdown,
    };
  }).sort((a, b) => a.district.localeCompare(b.district));
};

/**
 * Dynamically evaluate site-year-treatment trial plot estimates from
 * raw multi-year trial observation files (nsaf_site_year_treatment_trials.csv).
 */
export const evaluateSiteYearTreatmentTrials = (rows = [], filters = {}) => {
  if (!rows || !rows.length) return { estimates: [], grMean: null, ctrlMean: null, omissionMean: null, totalPlots: 0 };

  const { year, district, site } = filters;
  const filtered = rows.filter((r) => {
    if (year && String(r.year) !== String(year)) return false;
    if (district && (r.district || r.District) !== district) return false;
    if (site && (r.site || r.VDC) !== site) return false;
    return true;
  });

  const getYield = (r) => number(r.grain_yield_t_ha ?? r.Yield_t_ha ?? (r.yield_14pct_kg_ha ? r.yield_14pct_kg_ha / 1000 : null));
  const getNRate = (r) => number(r.n_rate_kg_ha ?? r.N_rate_kg_ha ?? r.N_kg_ha ?? 0);

  const grPlots = filtered.filter((r) => r.strategy === 'GR' || String(r.treatment_role).includes('government'));
  const ctrlPlots = filtered.filter((r) => r.strategy === '0-0-0' || String(r.treatment_role).includes('background') || String(r.treatment_role).includes('control'));
  const omissPlots = filtered.filter((r) => r.strategy === '0-PK' || String(r.treatment_role).includes('n_omission'));

  const grYields = grPlots.map(getYield).filter((y) => y !== null);
  const ctrlYields = ctrlPlots.map(getYield).filter((y) => y !== null);
  const omissYields = omissPlots.map(getYield).filter((y) => y !== null);

  const avg = (arr) => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : null;
  const grMean = avg(grYields);
  const ctrlMean = avg(ctrlYields);
  const omissionMean = avg(omissYields);

  // Group by strategy
  const stratMap = {};
  filtered.forEach((r) => {
    const s = r.strategy || r.treatment_role || r.treatment;
    if (!s) return;
    if (!stratMap[s]) {
      stratMap[s] = {
        strategy: s,
        label: STRATEGY_LABELS[s] || s,
        yields: [],
        nRates: [],
        plots: [],
      };
    }
    const y = getYield(r);
    const n = getNRate(r);
    if (y !== null) stratMap[s].yields.push(y);
    if (n !== null) stratMap[s].nRates.push(n);
    stratMap[s].plots.push(r);
  });

  const estimates = Object.values(stratMap).map((d) => {
    const meanYield = avg(d.yields);
    const meanNRate = avg(d.nRates) || 0;
    const diffFromGR = (meanYield !== null && grMean !== null) ? (meanYield - grMean) : null;
    const gainOver000 = (meanYield !== null && ctrlMean !== null) ? (meanYield - ctrlMean) : null;
    const aeN = (gainOver000 !== null && gainOver000 > 0 && meanNRate > 0) ? (gainOver000 * 1000) / meanNRate : 0;
    const pfpN = (meanYield !== null && meanNRate > 0) ? (meanYield * 1000) / meanNRate : 0;
    const negCount = grMean !== null ? d.yields.filter((y) => y < grMean).length : 0;
    const negPct = d.yields.length ? (negCount / d.yields.length) * 100 : 0;

    return {
      strategy: d.strategy,
      label: d.label,
      plotCount: d.plots.length,
      meanYield,
      meanNRate,
      diffFromGR,
      gainOver000,
      aeN,
      pfpN,
      negCount,
      negPct,
      nSavingsVsGR: meanNRate > 0 ? (120 - meanNRate) : 120,
    };
  }).sort((a, b) => (b.meanYield ?? 0) - (a.meanYield ?? 0));

  return {
    estimates,
    grMean,
    ctrlMean,
    omissionMean,
    totalPlots: filtered.length,
  };
};
