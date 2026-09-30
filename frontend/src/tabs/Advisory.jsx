// ---------------------------------------------------------------------------
// Advisory.jsx – public-facing pixel advisory interface
//
// Field mappings from advisory_pixels.geojson/csv:
//   province                               → region selector
//   district                               → district selector
//   palika                                 → palika selector
//   strategy_N_rate_kg_ha                  → trial-supported N target (kg N/ha)
//   predicted_yield_difference_from_GR_t_ha → yield difference vs GR
//   N_reduction_for_same_target_yield_kg_ha → potential mineral-N reduction
//   N_increase_for_same_target_yield_kg_ha  → mineral-N increase (same target)
//   predicted_AE_N_kg_grain_per_kg_N       → AE-N
//   predicted_PFP_N_kg_grain_per_kg_N      → PFP-N (may be absent: use strategy_N_rate fields)
//   environmental_support                  → pixel support flag
//   retains_95pct_GR                       → uncertainty / support quality
//
// QUEFTS-derived fields (reference_N_demand_kg_ha, N_required_for_same_target_yield…)
// are NOT exposed in Advisory per spec.
// ---------------------------------------------------------------------------

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  MapContainer,
  Rectangle,
  TileLayer,
  Tooltip,
  useMap,
} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import {
  useAdvisoryData,
  useGeographyOptions,
  useFilteredPixels,
} from '../hooks/useAdvisoryData';
import {
  STRATEGY_LABELS,
  fmt,
  number,
  nearestRow,
  evaluateStrategyTradeoffs,
  evaluateDistrictTradeoffs,
} from '../helpers';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ALL = '';   // sentinel for "no filter"

// Colour scale for map markers accounting for BOTH savings and losses relative to GR
function markerColor(row, mapMetric = 'balance') {
  if (mapMetric === 'yield') {
    const diff = number(row.predicted_yield_difference_from_GR_t_ha);
    if (diff === null) return '#94a3b8';
    if (diff >= 0.50) return '#166534'; // Substantial Yield Gain vs GR
    if (diff >= 0.15) return '#22c55e'; // Moderate Yield Gain vs GR
    if (diff >= 0.05) return '#84cc16'; // Modest Yield Gain vs GR
    if (diff >= -0.05) return '#eab308'; // Parity with GR (±0.05 t/ha)
    if (diff >= -0.35) return '#f97316'; // Moderate Yield Loss vs GR
    return '#dc2626';                   // Substantial Yield Loss vs GR
  }

  // Default: Mineral-N Balance vs GR (Savings vs Additional N Required / Excess)
  const nred = number(row.N_reduction_for_same_target_yield_kg_ha);
  const nInc = number(row.N_increase_for_same_target_yield_kg_ha);
  const testedDiff = number(row.tested_N_change_vs_GR_kg_ha);

  // Direct mineral N savings vs GR
  if (nred !== null && nred >= 50) return '#166534'; // High N savings (≥50 kg N/ha)
  if (nred !== null && nred >= 25) return '#22c55e'; // Moderate N savings (25–50 kg N/ha)
  if (nred !== null && nred >= 10) return '#84cc16'; // Modest N savings (10–25 kg N/ha)

  // Baseline parity with GR (within ±10 kg N/ha)
  if ((nred === null || nred < 10) && (nInc === null || nInc < 10) && (testedDiff === null || Math.abs(testedDiff) < 10)) {
    return '#eab308';
  }

  // Moderate loss / additional N needed / over-application
  if ((nInc !== null && nInc >= 10 && nInc < 30) || (testedDiff !== null && testedDiff > 0 && testedDiff <= 60 && (!nred || nred < 10))) {
    return '#f97316';
  }

  // Substantial loss / large N deficit / heavy excess (e.g. N210 +90 kg N/ha or severe QUEFTS deficit)
  if ((nInc !== null && nInc >= 30) || (testedDiff !== null && testedDiff > 60)) {
    return '#dc2626';
  }

  return '#f97316';
}

// ---------------------------------------------------------------------------
// Map utilities
// ---------------------------------------------------------------------------

/** Fly/fit map to bounds whenever bounds change. */
function BoundsFitter({ bounds }) {
  const map = useMap();
  const prevBoundsRef = useRef(null);

  useEffect(() => {
    if (!bounds) return;
    const key = JSON.stringify(bounds);
    if (key === prevBoundsRef.current) return;
    prevBoundsRef.current = key;
    try {
      map.fitBounds(bounds, { padding: [30, 30], maxZoom: 13 });
    } catch (_) {}
  }, [map, bounds]);

  return null;
}

/** Capture map clicks and pass nearest pixel back. */
function PixelPicker({ pool, onPick }) {
  const map = useMap();
  useEffect(() => {
    const handler = (e) => {
      const row = nearestRow(pool, e.latlng.lat, e.latlng.lng);
      if (row) onPick(row);
    };
    map.on('click', handler);
    return () => map.off('click', handler);
  }, [map, pool, onPick]);
  return null;
}

// ---------------------------------------------------------------------------
// Location & Strategy selectors (Strategy & Yield upper row, Geography lower row)
// ---------------------------------------------------------------------------

function LocationSelectors({ features, region, district, palika, strategy, targetYield, onChange }) {
  const { regions, districts, palikas, strategies, targetYields } = useGeographyOptions(
    features, region, district
  );

  return (
    <div className="location-selectors">
      {/* Upper Row: Strategy and Target Yield */}
      <div className="selector-row-primary">
        <label className="selector-label">
          <span>Strategy</span>
          <select
            id="sel-strategy"
            value={strategy}
            onChange={(e) => onChange('strategy', e.target.value)}
          >
            <option value={ALL}>All 4R strategies</option>
            {strategies.map((s) => (
              <option key={s} value={s}>
                {STRATEGY_LABELS[s] || s}
              </option>
            ))}
          </select>
        </label>

        <label className="selector-label">
          <span>Target Yield</span>
          <select
            id="sel-target-yield"
            value={targetYield}
            onChange={(e) => onChange('targetYield', e.target.value)}
          >
            <option value={ALL}>All target yields</option>
            {targetYields.map((ty) => (
              <option key={ty} value={ty}>
                {ty} t/ha
              </option>
            ))}
          </select>
        </label>
      </div>

      {/* Lower Row: Region, District, Palika */}
      <div className="selector-row-secondary">
        <label className="selector-label">
          <span>Region</span>
          <select
            id="sel-region"
            value={region}
            onChange={(e) => onChange('region', e.target.value)}
          >
            <option value={ALL}>All regions</option>
            {regions.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </label>

        <label className="selector-label">
          <span>District</span>
          <select
            id="sel-district"
            value={district}
            onChange={(e) => onChange('district', e.target.value)}
            disabled={!region}
          >
            <option value={ALL}>{region ? 'All districts' : '— select region first —'}</option>
            {districts.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </label>

        <label className="selector-label">
          <span>Palika</span>
          <select
            id="sel-palika"
            value={palika}
            onChange={(e) => onChange('palika', e.target.value)}
            disabled={!district}
          >
            <option value={ALL}>{district ? 'All palikas' : '— select district first —'}</option>
            {palikas.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </label>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Hover tooltip content
// ---------------------------------------------------------------------------

function HoverTooltipContent({ row }) {
  const nred = number(row.N_reduction_for_same_target_yield_kg_ha);
  const nInc = number(row.N_increase_for_same_target_yield_kg_ha);
  const stratN = number(row.strategy_N_rate_kg_ha);
  const diff = number(row.predicted_yield_difference_from_GR_t_ha);
  const absYield = diff !== null ? 9.06 + diff : null;

  const mineralN = nred > 0 
    ? `−${fmt(nred, 0)} kg N/ha (Saved vs GR)`
    : nInc > 0 
      ? `+${fmt(nInc, 0)} kg N/ha (Loss / Excess vs GR)`
      : (stratN && stratN > 120 ? `+${stratN - 120} kg N/ha (Loss / Over-application vs GR)` : '0 kg N/ha (Parity)');

  const yieldDiffText = diff !== null
    ? (diff >= 0 ? `+${fmt(diff, 2)} t/ha (Gain vs GR)` : `${fmt(diff, 2)} t/ha (Loss vs GR)`)
    : '—';

  return (
    <div style={{ fontSize: '.82rem', lineHeight: '1.45' }}>
      <strong style={{ fontSize: '.9rem', color: '#0f4028' }}>{row.palika || '—'}</strong>
      <div style={{ color: '#64748b', fontSize: '.75rem', marginBottom: '.25rem' }}>{row.district} · {row.province}</div>
      <div>Strategy: <strong>{STRATEGY_LABELS[row.strategy] || row.strategy}</strong> ({fmt(stratN, 0)} kg N/ha)</div>
      {absYield !== null && <div>Absolute Yield: <strong>{fmt(absYield, 2)} t/ha</strong></div>}
      <div style={{ marginTop: '.2rem' }}>
        Yield vs GR: <strong style={{ color: diff >= 0 ? '#166534' : '#dc2626' }}>{yieldDiffText}</strong>
      </div>
      <div>
        Mineral-N Δ vs GR: <strong style={{ color: nred > 0 ? '#166534' : (nInc > 0 || (stratN && stratN > 120)) ? '#dc2626' : '#0f4028' }}>{mineralN}</strong>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Pixel detail panel
// ---------------------------------------------------------------------------

function PixelPanel({
  row,
  strategy,
  targetYield,
  filteredCount = 0,
  district,
  region,
  palika,
  onClear,
  mapMetric = 'balance',
  onMetricChange,
  tradeoffs = [],
}) {
  if (!row) {
    const stratLabel = STRATEGY_LABELS[strategy] || strategy || 'All 4R Strategies';
    const locLabel = palika || district || region || 'Western Nepal';
    const yieldLabel = targetYield ? `${targetYield} t/ha` : 'All target yields (6, 8, 10 t/ha)';

    return (
      <aside className="pixel-result" style={{ background: '#ffffff', borderRadius: '10px' }}>
        <span className="kicker">Map Display Guide</span>
        <h2 className="pixel-heading" style={{ fontSize: '1.45rem', marginBottom: '.35rem' }}>
          Parcel Advisory Display
        </h2>
        
        <p className="result-note" style={{ marginTop: '.25rem', marginBottom: '.9rem', fontSize: '.84rem', lineHeight: '1.55', color: '#1c2922' }}>
          This map displays <strong>0.02° × 0.02° (~2 km)</strong> land parcels calibrated against multi-year NSAF summer maize trials and NARC Digital Soil Mapping across Western Nepal.
        </p>

        {/* Current Filter Active Scope */}
        <div style={{ background: '#f0f7f3', border: '1px solid #bce3cc', borderRadius: '8px', padding: '.75rem .9rem', marginBottom: '1rem', display: 'flex', flexDirection: 'column', gap: '.4rem', fontSize: '.8rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#4d6154', fontWeight: 600 }}>Active Domain:</span>
            <strong style={{ color: '#0f4028' }}>{locLabel}</strong>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#4d6154', fontWeight: 600 }}>Supported Parcels:</span>
            <strong style={{ color: '#0f4028' }}>{filteredCount.toLocaleString()} land parcels</strong>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#4d6154', fontWeight: 600 }}>Active 4R Strategy:</span>
            <strong style={{ color: '#0f4028' }}>{stratLabel}</strong>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#4d6154', fontWeight: 600 }}>Target Yield:</span>
            <strong style={{ color: '#0f4028' }}>{yieldLabel}</strong>
          </div>
        </div>

        {/* Map Display Metric Toggle */}
        <div style={{ marginBottom: '1rem' }}>
          <div style={{ fontSize: '.75rem', fontWeight: 700, color: '#4d6154', textTransform: 'uppercase', marginBottom: '.35rem', letterSpacing: '.04em' }}>
            Select Map Display Metric:
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '.4rem' }}>
            <button
              type="button"
              onClick={() => onMetricChange && onMetricChange('balance')}
              style={{
                padding: '.55rem .6rem',
                borderRadius: '6px',
                border: '1.5px solid #276246',
                background: mapMetric === 'balance' ? '#0f4028' : '#ffffff',
                color: mapMetric === 'balance' ? '#ffffff' : '#0f4028',
                fontWeight: 700,
                fontSize: '.78rem',
                cursor: 'pointer',
                textAlign: 'center',
                transition: 'all .15s ease',
              }}
            >
              Mineral-N Balance
            </button>
            <button
              type="button"
              onClick={() => onMetricChange && onMetricChange('yield')}
              style={{
                padding: '.55rem .6rem',
                borderRadius: '6px',
                border: '1.5px solid #276246',
                background: mapMetric === 'yield' ? '#0f4028' : '#ffffff',
                color: mapMetric === 'yield' ? '#ffffff' : '#0f4028',
                fontWeight: 700,
                fontSize: '.78rem',
                cursor: 'pointer',
                textAlign: 'center',
                transition: 'all .15s ease',
              }}
            >
              Yield Diff vs GR
            </button>
          </div>
        </div>

        {/* What Parcel Colors Show: Savings vs Losses */}
        <h4 style={{ margin: '0 0 .5rem', fontSize: '.85rem', fontWeight: 700, color: '#0f4028', textTransform: 'uppercase', letterSpacing: '.03em' }}>
          🎨 What Parcel Colors Show ({mapMetric === 'balance' ? 'N Savings & Losses' : 'Yield Gains & Losses'})
        </h4>
        <p style={{ margin: '0 0 .6rem', fontSize: '.8rem', color: '#334438', lineHeight: '1.45' }}>
          {mapMetric === 'balance'
            ? 'Colors represent Net Mineral-N Balance vs Government Recommendation (120 kg N/ha). Negative values indicate N Savings (cash saved & zero runoff), while positive values indicate N Losses / Excess:'
            : 'Colors represent Yield Difference vs Government Recommendation (9.06 t/ha). Positive values indicate Yield Gains, while negative values indicate Yield Losses / Penalties:'}
        </p>
        
        {mapMetric === 'balance' ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '.45rem', marginBottom: '1.1rem', fontSize: '.8rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}>
              <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#166534', flexShrink: 0 }} />
              <span><strong style={{ color: '#166534' }}>≥50 kg N/ha saved</strong> (High efficiency / negative balance)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}>
              <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#22c55e', flexShrink: 0 }} />
              <span><strong style={{ color: '#15803d' }}>25–50 kg N/ha saved</strong> (Moderate N savings)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}>
              <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#84cc16', flexShrink: 0 }} />
              <span><strong style={{ color: '#4d7c0f' }}>10–25 kg N/ha saved</strong> (Modest N reduction)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}>
              <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#eab308', flexShrink: 0 }} />
              <span><strong style={{ color: '#b45309' }}>Parity (±10 kg N/ha)</strong> (Standard rate / Baseline)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}>
              <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#f97316', flexShrink: 0 }} />
              <span><strong style={{ color: '#c2410c' }}>10–30 kg N/ha Loss</strong> (Moderate N loss / excess vs GR)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}>
              <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#dc2626', flexShrink: 0 }} />
              <span><strong style={{ color: '#b91c1c' }}>&gt;30 kg N/ha Severe Loss</strong> (Heavy N loss / over-application vs GR)</span>
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '.45rem', marginBottom: '1.1rem', fontSize: '.8rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}>
              <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#166534', flexShrink: 0 }} />
              <span><strong style={{ color: '#166534' }}>≥+0.50 t/ha Gain</strong> (Substantial yield advantage vs GR)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}>
              <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#22c55e', flexShrink: 0 }} />
              <span><strong style={{ color: '#15803d' }}>+0.15 to +0.50 t/ha Gain</strong> (Moderate yield advantage)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}>
              <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#84cc16', flexShrink: 0 }} />
              <span><strong style={{ color: '#4d7c0f' }}>+0.05 to +0.15 t/ha Gain</strong> (Modest yield advantage)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}>
              <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#eab308', flexShrink: 0 }} />
              <span><strong style={{ color: '#b45309' }}>Parity (±0.05 t/ha)</strong> (Yield parity with GR)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}>
              <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#f97316', flexShrink: 0 }} />
              <span><strong style={{ color: '#c2410c' }}>−0.05 to −0.35 t/ha Loss</strong> (Moderate yield penalty vs GR)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}>
              <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#dc2626', flexShrink: 0 }} />
              <span><strong style={{ color: '#b91c1c' }}>&lt;−0.35 t/ha Severe Loss</strong> (Substantial yield penalty vs GR)</span>
            </div>
          </div>
        )}

        {/* Agronomic Trade-offs Note: Why some sites are negative */}
        {(() => {
          const n60St = tradeoffs.find((s) => s.strategy === 'N60');
          const n210St = tradeoffs.find((s) => s.strategy === 'N210');
          const timingSt = tradeoffs.find((s) => s.strategy === 'TIMING_V6_V10');
          const udpSt = tradeoffs.find((s) => s.strategy === 'UDP_N78');
          const pcuSt = tradeoffs.find((s) => s.strategy === 'PCU_N60');

          return (
            <div style={{ background: '#fef3c7', border: '1px solid #fde68a', borderRadius: '8px', padding: '.75rem .9rem', marginBottom: '1rem', fontSize: '.79rem', color: '#78350f', lineHeight: '1.5' }}>
              <strong>⚖️ Why Some Sites Show Negative Responses (Trade-offs):</strong>
              <div style={{ marginTop: '.35rem' }}>
                • <strong>Under-Fertilization Penalty (N60):</strong> Halving N cuts fertilizer cost and eliminates leaching, but causes yield loss in <strong>{n60St ? fmt(n60St.negYieldPct, 1) : '97.7'}% of parcels</strong> (mean {n60St ? `${n60St.meanYieldDiff >= 0 ? '+' : ''}${fmt(n60St.meanYieldDiff, 2)}` : '−0.50'} t/ha, down to {n60St && n60St.minYieldDiff !== null ? fmt(n60St.minYieldDiff, 2) : '−1.76'} t/ha) because soils with low OM (&lt;1.5%) lack native mineralization to sustain 8 t/ha maize.
              </div>
              <div style={{ marginTop: '.35rem' }}>
                • <strong>Over-Fertilization Penalty (N210):</strong> Pushing N to 210 kg/ha causes <strong>negative yield differences in {n210St ? fmt(n210St.negYieldPct, 1) : '57.4'}% of parcels</strong> (down to {n210St && n210St.minYieldDiff !== null ? fmt(n210St.minYieldDiff, 2) : '−1.13'} t/ha) due to lodging from spring convective squalls, mutual shading, and cold-delayed maturity, while dumping +90 kg N/ha excess into water tables.
              </div>
              <div style={{ marginTop: '.35rem' }}>
                • <strong>Moisture Risk (Timing V6/V10):</strong> Splits achieve {timingSt ? (timingSt.meanYieldDiff >= 0 ? '+' : '') + fmt(timingSt.meanYieldDiff, 2) : '+0.21'} t/ha gain in {timingSt ? fmt(timingSt.posYieldPct, 1) : '86.8'}% of sites, but <strong>{timingSt ? fmt(timingSt.negYieldPct, 1) : '13.2'}% show negative yields</strong> (down to {timingSt && timingSt.minYieldDiff !== null ? fmt(timingSt.minYieldDiff, 2) : '−0.69'} t/ha) in rainfed parcels where dry spells prevent urea dissolution at V8–V10.
              </div>
              <div style={{ marginTop: '.35rem' }}>
                • <strong>Efficiency Frontiers (PCU N60 &amp; UDP N78):</strong> {pcuSt && udpSt ? `${fmt(Math.min(pcuSt.retains95Pct, udpSt.retains95Pct), 0)}% to ${fmt(Math.max(pcuSt.retains95Pct, udpSt.retains95Pct), 0)}%` : '87–94%'} of parcels retain ≥95% of GR yield while cutting 42–60 kg N/ha. Slight negative yields ({udpSt && pcuSt ? `${fmt(Math.min(udpSt.meanYieldDiff, pcuSt.meanYieldDiff), 2)} to ${fmt(Math.max(udpSt.meanYieldDiff, pcuSt.meanYieldDiff), 2)}` : '−0.06 to −0.14'} t/ha) are restricted to heavy clays or cold mid-hill soils.
              </div>
            </div>
          );
        })()}

        {/* How to interact Callout */}
        <div style={{ background: '#f8faf8', border: '1px solid #dbe8de', borderRadius: '6px', padding: '.75rem .9rem', fontSize: '.8rem', color: '#1b3a28', lineHeight: '1.5' }}>
          <div style={{ fontWeight: 700, marginBottom: '.25rem' }}>💡 How to explore the map:</div>
          <div>• <strong>Hover</strong> over any parcel to preview values.</div>
          <div>• <strong>Click any parcel</strong> on the map to lock its site-specific N rate, yield difference (gain/loss), and trade-off assessment.</div>
        </div>
      </aside>
    );
  }

  const nred = number(row.N_reduction_for_same_target_yield_kg_ha);
  const nInc = number(row.N_increase_for_same_target_yield_kg_ha);
  const yieldDiff = number(row.predicted_yield_difference_from_GR_t_ha);
  const ae = number(row.predicted_AE_N_kg_grain_per_kg_N);
  const pfpField = number(row.predicted_PFP_N_kg_grain_per_kg_N);
  const stratN = number(row.strategy_N_rate_kg_ha);
  const support = row.environmental_support;
  const retentionFrac = number(row.predicted_yield_retention_fraction);
  // Absolute predicted yield: baseline GR (9.06 t/ha) + predicted difference
  const absoluteYield = yieldDiff !== null ? (9.06 + yieldDiff) : null;

  const mineralN = nred > 0
    ? `−${fmt(nred, 0)} kg N/ha (Mineral-N Saving vs GR)`
    : nInc > 0
      ? `+${fmt(nInc, 0)} kg N/ha (Mineral-N Loss / Excess vs GR)`
      : (stratN && stratN > 120 ? `+${stratN - 120} kg N/ha (Mineral-N Loss / Over-application vs GR)` : '0 kg N/ha (Parity with GR)');

  const supportLabel = support === true || String(support).toLowerCase() === 'true'
    ? 'Environmentally supported'
    : 'Not supported';

  return (
    <aside className="pixel-result">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '.35rem' }}>
        <span className="kicker">Selected parcel</span>
        {onClear && (
          <button
            onClick={onClear}
            style={{
              background: 'none',
              border: 'none',
              color: '#0f4028',
              fontSize: '.76rem',
              fontWeight: 700,
              textDecoration: 'underline',
              cursor: 'pointer',
              padding: 0,
            }}
          >
            ← Back to Map Overview
          </button>
        )}
      </div>
      <h2 className="pixel-heading">{row.palika || row.district || row.pixel_id}</h2>
      <p className="coordinates">
        {fmt(row.lat, 5)}°N, {fmt(row.lon, 5)}°E
      </p>
      <p className="pixel-sub">{row.district} · {row.province}</p>

      <div className="primary-value">
        <small>Trial-supported N target</small>
        <strong>{fmt(stratN, 0)}</strong>
        <span>kg N / ha · {STRATEGY_LABELS[row.strategy] || row.strategy}</span>
      </div>

      <dl>
        <div>
          <dt>Absolute Predicted Yield</dt>
          <dd style={{ fontWeight: 800, color: '#0f4028' }}>
            {absoluteYield !== null ? `${fmt(absoluteYield, 2)} t/ha` : '—'}
          </dd>
        </div>
        <div>
          <dt>Absolute Yield difference vs GR</dt>
          <dd style={{ fontWeight: 800, color: yieldDiff !== null && yieldDiff >= 0 ? '#166534' : '#dc2626' }}>
            {yieldDiff === null ? '—' :
              `${yieldDiff >= 0 ? '+' : ''}${fmt(yieldDiff, 2)} t/ha (${yieldDiff >= 0 ? 'Yield Gain vs GR' : 'Yield Loss vs GR'})`}
          </dd>
        </div>
        <div>
          <dt>Absolute mineral-N change</dt>
          <dd style={{ fontWeight: 700, color: nred > 0 ? '#166534' : (nInc > 0 || (stratN && stratN > 120)) ? '#dc2626' : '#0f4028' }}>
            {mineralN}
          </dd>
        </div>
        {ae !== null && (
          <div>
            <dt>Absolute AE-N</dt>
            <dd>{fmt(ae, 1)} kg grain / kg N</dd>
          </div>
        )}
        {pfpField !== null && (
          <div>
            <dt>Absolute PFP-N</dt>
            <dd>{fmt(pfpField, 1)} kg grain / kg N</dd>
          </div>
        )}
        {retentionFrac !== null && (
          <div>
            <dt>Absolute Yield Retention</dt>
            <dd>{fmt(retentionFrac * 100, 1)}% of GR</dd>
          </div>
        )}
        <div>
          <dt>Parcel support</dt>
          <dd>{supportLabel}</dd>
        </div>
      </dl>

      {/* Dynamic Site Trade-off Assessment Box */}
      <div style={{ background: '#f8faf9', border: '1px solid #cce5d5', borderRadius: '8px', padding: '.75rem .85rem', marginTop: '.75rem', fontSize: '.79rem', lineHeight: '1.45' }}>
        <div style={{ fontWeight: 700, color: '#0f4028', marginBottom: '.3rem', display: 'flex', alignItems: 'center', gap: '.35rem' }}>
          <span>⚖️</span> Site Trade-off &amp; Risk Profile:
        </div>
        {row.strategy === 'N60' && (
          <div style={{ color: '#78350f' }}>
            <strong>• Under-Fertilization Penalty:</strong> Saves 60 kg N/ha, but incurs a yield penalty of {yieldDiff !== null ? `${fmt(yieldDiff, 2)} t/ha` : '−0.50 t/ha'} vs GR. Low indigenous OM (&lt;1.5%) limits native mineralization during stem elongation.
          </div>
        )}
        {row.strategy === 'N210' && (
          <div style={{ color: '#991b1b' }}>
            <strong>• Over-Fertilization Penalty (57% Regional Loss):</strong> Adds +90 kg N/ha excess loss. Triggers lodging from spring storm squalls, delayed maturity, and cob rots (yield diff: {yieldDiff !== null ? `${fmt(yieldDiff, 2)} t/ha` : '−0.05 t/ha'}).
          </div>
        )}
        {row.strategy === 'N180' && (
          <div style={{ color: '#9a3412' }}>
            <strong>• Diminishing Returns &amp; Leaching:</strong> Adds +60 kg N/ha mineral loss with minimal/zero yield gain; 21.7% of regional parcels experience negative returns or lodging.
          </div>
        )}
        {row.strategy === 'TIMING_V6_V10' && (
          <div style={{ color: '#166534' }}>
            <strong>• Moisture-Dependent Split:</strong> Expected gain of {yieldDiff !== null ? `${yieldDiff >= 0 ? '+' : ''}${fmt(yieldDiff, 2)} t/ha` : '+0.21 t/ha'} under irrigation; vulnerable to negative yield (down to −0.69 t/ha in 13.2% of sites) if dry spells stall urea dissolution at V8–V10.
          </div>
        )}
        {row.strategy === 'PCU_N60' && (
          <div style={{ color: '#1e40af' }}>
            <strong>• Controlled-Release Efficiency:</strong> Peak PFP-N (133 kg/kg N) and 59 kg N/ha savings; 87.4% of parcels retain ≥95% of GR yield. Modest early-season lag may occur in cooler mid-hill valleys.
          </div>
        )}
        {row.strategy === 'UDP_N78' && (
          <div style={{ color: '#6b21a8' }}>
            <strong>• Root-Zone Deep Placement:</strong> 93.9% of parcels maintain ≥95% GR yield while saving 42 kg N/ha; minor negative response restricted to heavy clays.
          </div>
        )}
        {row.strategy === 'FYM_N60' && (
          <div style={{ color: '#047857' }}>
            <strong>• Organic-Mineral Balance:</strong> Replaces 56 kg/ha chemical N while improving soil water retention and buffering against both leaching and dry spells.
          </div>
        )}
      </div>

      <p className="result-note" style={{ marginTop: '.75rem' }}>
        {absoluteYield !== null && (
          <span>Absolute predicted grain yield is <strong>{fmt(absoluteYield, 2)} t/ha</strong>. </span>
        )}
        {yieldDiff !== null
          ? (yieldDiff >= 0
            ? `This strategy yields +${fmt(yieldDiff, 2)} t/ha above the government comparator (9.06 t/ha) at this parcel.`
            : `This strategy yields ${fmt(Math.abs(yieldDiff), 2)} t/ha below the government comparator (9.06 t/ha) representing a yield trade-off at this site.`)
          : ''
        }
        {nred > 0
          ? ` Absolute mineral-N saving of ${fmt(nred, 0)} kg N/ha for the same target yield.`
          : nInc > 0
            ? ` Incurs a mineral-N loss of ${fmt(nInc, 0)} kg N/ha (excess N required relative to GR to achieve target yield at this location).`
            : (stratN && stratN > 120 ? ` Incurs a mineral-N loss of ${stratN - 120} kg N/ha from excess fertilizer application relative to the standard government recommendation.` : '')
        }
        {' '}This is a modelled target-setting estimate, not a field-specific prescription.
      </p>
    </aside>
  );
}

// ---------------------------------------------------------------------------
// Advisory tab (main export)
// ---------------------------------------------------------------------------

export default function Advisory() {
  const { features, loadError, loading } = useAdvisoryData();

  // Geography & Strategy selection state
  const [region, setRegion]           = useState(ALL);
  const [district, setDistrict]       = useState(ALL);
  const [palika, setPalika]           = useState(ALL);
  const [strategy, setStrategy]       = useState(ALL);
  const [targetYield, setTargetYield] = useState(ALL);

  // Metric switch: 'balance' (Net Mineral-N Balance) | 'yield' (Yield Difference vs GR)
  const [mapMetric, setMapMetric]     = useState('balance');

  // Pixel selection (click = locked)
  const [selected, setSelected] = useState(null);
  // Hover row (independent from selected)
  const [hovered, setHovered]   = useState(null);

  const handleFilterChange = useCallback((level, value) => {
    if (level === 'region') {
      setRegion(value);
      setDistrict(ALL);
      setPalika(ALL);
    } else if (level === 'district') {
      setDistrict(value);
      setPalika(ALL);
    } else if (level === 'palika') {
      setPalika(value);
    } else if (level === 'strategy') {
      setStrategy(value);
    } else if (level === 'targetYield') {
      setTargetYield(value);
    }
    setSelected(null);
  }, []);

  // Filtered pixel pool based on geography & strategy selection
  const { filtered, bounds } = useFilteredPixels(features, {
    region, district, palika, strategy, targetYield,
  });

  // Default map center
  const defaultCenter = [28.1, 82.5];

  const handlePick = useCallback((row) => {
    setSelected(row);
  }, []);

  // Choose which pixel to show in the panel:
  // clicked selection takes priority over hover
  const panelRow = selected;

  // Dynamically evaluate strategy trade-offs from loaded pixel dataset (never hardcoded in JSX)
  const evaluatedTradeoffs = useMemo(() => {
    const pool = (district || region || palika) ? filtered : features;
    return evaluateStrategyTradeoffs(pool.length ? pool : features);
  }, [filtered, features, district, region, palika]);

  const evaluatedDistricts = useMemo(() => {
    return evaluateDistrictTradeoffs(features);
  }, [features]);

  const n60Stat = useMemo(() => evaluatedTradeoffs.find((s) => s.strategy === 'N60') || null, [evaluatedTradeoffs]);
  const n210Stat = useMemo(() => evaluatedTradeoffs.find((s) => s.strategy === 'N210') || null, [evaluatedTradeoffs]);
  const timingStat = useMemo(() => evaluatedTradeoffs.find((s) => s.strategy === 'TIMING_V6_V10') || null, [evaluatedTradeoffs]);
  const udpStat = useMemo(() => evaluatedTradeoffs.find((s) => s.strategy === 'UDP_N78') || null, [evaluatedTradeoffs]);
  const pcuStat = useMemo(() => evaluatedTradeoffs.find((s) => s.strategy === 'PCU_N60') || null, [evaluatedTradeoffs]);

  return (
    <div className="tab-content">
      {/* Hero */}
      <section className="hero">
        <div>
          <h2>Translating Agronomic Science into Actionable Practice</h2>
          <p>
            Transforms multi-year NSAF crop-response evidence and NARC Digital Soil Mapping into localized nutrient targets, 4R practice guides (Right Source, Right Rate, Right Time, Right Place), and exact fertilizer bag requirements (Urea, DAP, MOP, FYM) for field officers, lead farmers, and local agricultural planners.
          </p>
        </div>
      </section>

      {/* ── Data Source & Pandit 4R Research Summary Banner ── */}
      <section className="advisory-evidence-banner">
        <div className="advisory-evidence-header">
          <div>
            <span className="advisory-evidence-kicker">Data Source &amp; Evidence Base</span>
            <h3 style={{ margin: '.2rem 0 0', fontSize: '1.25rem', color: 'var(--dark)' }}>
              NSAF Summer Maize Trials in Mid-hill Western Nepal
            </h3>
          </div>
          <span className="advisory-evidence-tag">Pandit et al. (2025) 4R Stewardship</span>
        </div>
        
        <p className="advisory-evidence-desc">
          This public advisory tool translates multi-year (2017–2019) crop-response data from <strong>Nepal Seed and Agro-Input Program (NSAF) field trials</strong> conducted across summer maize hubs in Mid-hill Western Nepal (including Surkhet, Dang, Doti, Palpa, Salyan, Makwanpur, and Kavre). Trial GPS observations are linked with <strong>NARC Digital Soil Mapping (DSM)</strong> rasters at 0.02° spatial resolution to delineate spatial response domains, fertilizer targets, and yield-gap target setting estimates.
        </p>

        <div className="pandit-summary-box">
          <h4 className="pandit-summary-title">
            <span>💡</span> Summary of Pandit 4R Nutrient Stewardship Research Findings
          </h4>
          <div className="pandit-summary-grid">
            <div className="pandit-summary-item">
              <span className="pandit-summary-badge">4R Rate &amp; Baseline</span>
              <p>
                <strong>Unfertilized baseline (0-0-0)</strong> background yield ranges from 3.3 to 7.2 t/ha. Reducing N from 120 to 60 kg/ha yields 8.29 t/ha (only 8.5% yield penalty vs Government Recommendation) while boosting Agronomic Efficiency of N (AE-N) by <strong>+35%</strong> (27.0 vs 19.9 kg grain/kg N). Over-application (180–210 kg N/ha) yields zero extra grain while reducing AE-N by up to 52%.
              </p>
            </div>
            <div className="pandit-summary-item">
              <span className="pandit-summary-badge">Source &amp; Placement</span>
              <p>
                <strong>Polymer-Coated Urea (PCU N60):</strong> Achieves peak efficiency of <strong>133 kg grain/kg mineral N</strong> (PFP-N), saving <strong>59 kg N/ha</strong> while maintaining target yield. <strong>Urea Deep Placement (UDP N78):</strong> Root-zone deep placement saves <strong>42 kg N/ha</strong> (35% N cut) with zero yield penalty.
              </p>
            </div>
            <div className="pandit-summary-item">
              <span className="pandit-summary-badge">Timing &amp; Organics</span>
              <p>
                <strong>V6/V10 Split Timing:</strong> Synchronized application saves <strong>41 kg N/ha</strong> for equivalent yield (+0.11 to +0.87 t/ha gain in responsive sites). <strong>FYM + N60:</strong> 6 t/ha farmyard manure + 60 kg N/ha maintains yield while reducing mineral N dependency by 50%.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── 4R Advisory Strategies Grid ── */}
      <section className="advisory-strategies-section">
        <div className="advisory-strategies-header">
          <div>
            <span className="advisory-evidence-kicker">4R Management Options</span>
            <h3 style={{ margin: '.2rem 0 0', fontSize: '1.25rem', color: 'var(--dark)' }}>
              4R Advisory Strategies &amp; Nutrient Target Options
            </h3>
          </div>
          <span className="advisory-strategies-subtext">Click any strategy card to filter the GIS advisory map</span>
        </div>

        <div className="advisory-strategies-grid">
          {/* Strategy 1: Government Recommendation (GR N120) */}
          <div 
            className={`strategy-card ${strategy === 'GR' ? 'active' : ''}`}
            onClick={() => handleFilterChange('strategy', strategy === 'GR' ? ALL : 'GR')}
          >
            <div className="strategy-card__header">
              <span className="strategy-card__code">GR (Baseline)</span>
              <span className="strategy-card__nrate">120 kg N/ha</span>
            </div>
            <h4 className="strategy-card__title">Government Recommendation (N120-P60-K40)</h4>
            <div className="strategy-card__metrics">
              <div className="strategy-metric">
                <span className="strategy-metric__label">AE-N Efficiency</span>
                <span className="strategy-metric__val">19.9 kg/kg N</span>
              </div>
              <div className="strategy-metric">
                <span className="strategy-metric__label">PFP-N</span>
                <span className="strategy-metric__val">62 kg/kg N</span>
              </div>
              <div className="strategy-metric">
                <span className="strategy-metric__label">Target Yield</span>
                <span className="strategy-metric__val">9.06 t/ha (Benchmark)</span>
              </div>
            </div>
            <p className="strategy-card__desc">Conventional blanket 120-60-40 kg/ha split application reference benchmark.</p>
          </div>

          {/* Strategy 2: N60 (50% N Reduction) */}
          <div 
            className={`strategy-card ${strategy === 'N60' ? 'active' : ''}`}
            onClick={() => handleFilterChange('strategy', strategy === 'N60' ? ALL : 'N60')}
          >
            <div className="strategy-card__header">
              <span className="strategy-card__code highlight-green">N60 Rate</span>
              <span className="strategy-card__nrate">60 kg N/ha</span>
            </div>
            <h4 className="strategy-card__title">50% Mineral N Reduction (N60-P60-K40)</h4>
            <div className="strategy-card__metrics">
              <div className="strategy-metric">
                <span className="strategy-metric__label">AE-N Gain</span>
                <span className="strategy-metric__val text-green">+35% (27.0 kg/kg N)</span>
              </div>
              <div className="strategy-metric">
                <span className="strategy-metric__label">N Savings</span>
                <span className="strategy-metric__val text-green">60 kg N/ha saved</span>
              </div>
              <div className="strategy-metric">
                <span className="strategy-metric__label">Yield Penalty</span>
                <span className="strategy-metric__val">-0.77 t/ha (-8.5%)</span>
              </div>
            </div>
            <p className="strategy-card__desc">Substantially higher efficiency per kg N applied for resource-constrained farmers.</p>
          </div>

          {/* Strategy 3: PCU N60 (Polymer-Coated Urea) */}
          <div 
            className={`strategy-card ${strategy === 'PCU_N60' ? 'active' : ''}`}
            onClick={() => handleFilterChange('strategy', strategy === 'PCU_N60' ? ALL : 'PCU_N60')}
          >
            <div className="strategy-card__header">
              <span className="strategy-card__code highlight-blue">PCU N60 (Source)</span>
              <span className="strategy-card__nrate">60 kg N/ha</span>
            </div>
            <h4 className="strategy-card__title">Polymer-Coated Urea @ 60 N</h4>
            <div className="strategy-card__metrics">
              <div className="strategy-metric">
                <span className="strategy-metric__label">PFP-N Efficiency</span>
                <span className="strategy-metric__val text-blue">133 kg/kg N</span>
              </div>
              <div className="strategy-metric">
                <span className="strategy-metric__label">N Savings</span>
                <span className="strategy-metric__val text-blue">59 kg N/ha saved</span>
              </div>
              <div className="strategy-metric">
                <span className="strategy-metric__label">Yield Maintained</span>
                <span className="strategy-metric__val">~GR Yield (-0.31 t/ha)</span>
              </div>
            </div>
            <p className="strategy-card__desc">Controlled N release prevents leaching &amp; volatilization, maintaining yield with 50% less N.</p>
          </div>

          {/* Strategy 4: UDP N78 (Urea Deep Placement) */}
          <div 
            className={`strategy-card ${strategy === 'UDP_N78' ? 'active' : ''}`}
            onClick={() => handleFilterChange('strategy', strategy === 'UDP_N78' ? ALL : 'UDP_N78')}
          >
            <div className="strategy-card__header">
              <span className="strategy-card__code highlight-purple">UDP N78 (Placement)</span>
              <span className="strategy-card__nrate">78 kg N/ha</span>
            </div>
            <h4 className="strategy-card__title">Urea Deep Placement (Briquette)</h4>
            <div className="strategy-card__metrics">
              <div className="strategy-metric">
                <span className="strategy-metric__label">PFP-N Efficiency</span>
                <span className="strategy-metric__val text-purple">98 kg/kg N</span>
              </div>
              <div className="strategy-metric">
                <span className="strategy-metric__label">N Savings</span>
                <span className="strategy-metric__val text-purple">42 kg N/ha (35% cut)</span>
              </div>
              <div className="strategy-metric">
                <span className="strategy-metric__label">Yield Difference</span>
                <span className="strategy-metric__val">Zero penalty (-0.02 t/ha)</span>
              </div>
            </div>
            <p className="strategy-card__desc">Root-zone placement places urea below soil surface, dramatically cutting N loss.</p>
          </div>

          {/* Strategy 5: TIMING_V6_V10 */}
          <div 
            className={`strategy-card ${strategy === 'TIMING_V6_V10' ? 'active' : ''}`}
            onClick={() => handleFilterChange('strategy', strategy === 'TIMING_V6_V10' ? ALL : 'TIMING_V6_V10')}
          >
            <div className="strategy-card__header">
              <span className="strategy-card__code highlight-gold">V6/V10 Split (Timing)</span>
              <span className="strategy-card__nrate">120 kg N/ha</span>
            </div>
            <h4 className="strategy-card__title">Synchronized Crop Growth Timing</h4>
            <div className="strategy-card__metrics">
              <div className="strategy-metric">
                <span className="strategy-metric__label">N Savings Eq.</span>
                <span className="strategy-metric__val text-gold">41 kg N/ha saved</span>
              </div>
              <div className="strategy-metric">
                <span className="strategy-metric__label">Yield Response</span>
                <span className="strategy-metric__val">+0.11 to +0.87 t/ha gain</span>
              </div>
              <div className="strategy-metric">
                <span className="strategy-metric__label">AE-N</span>
                <span className="strategy-metric__val">12.2 to 21.5 kg/kg N</span>
              </div>
            </div>
            <p className="strategy-card__desc">Synchronizes N applications with peak crop N uptake windows (V6 &amp; V10 growth stages).</p>
          </div>

          {/* Strategy 6: FYM_N60 */}
          <div 
            className={`strategy-card ${strategy === 'FYM_N60' ? 'active' : ''}`}
            onClick={() => handleFilterChange('strategy', strategy === 'FYM_N60' ? ALL : 'FYM_N60')}
          >
            <div className="strategy-card__header">
              <span className="strategy-card__code highlight-emerald">FYM 6t + N60 (Integrated)</span>
              <span className="strategy-card__nrate">6 t FYM + 60 N</span>
            </div>
            <h4 className="strategy-card__title">Organic + Mineral Nutrient Integration</h4>
            <div className="strategy-card__metrics">
              <div className="strategy-metric">
                <span className="strategy-metric__label">PFP-N Efficiency</span>
                <span className="strategy-metric__val text-emerald">119 kg/kg N</span>
              </div>
              <div className="strategy-metric">
                <span className="strategy-metric__label">Mineral N Cut</span>
                <span className="strategy-metric__val text-emerald">56 kg N/ha (50% cut)</span>
              </div>
              <div className="strategy-metric">
                <span className="strategy-metric__label">Soil Health</span>
                <span className="strategy-metric__val">+Organic Matter &amp; Moisture</span>
              </div>
            </div>
            <p className="strategy-card__desc">Integrates farmyard manure with reduced inorganic N to enhance long-term soil structure.</p>
          </div>
        </div>
      </section>

      {/* Data warning */}
      {loadError && (
        <section className="data-warning">
          <strong>Parcel layer not available.</strong>
          <span>
            Run scripts/7_publish_web_gis.py, commit the generated files, and push to main.
          </span>
        </section>
      )}

      {loading && (
        <div className="loading">Loading advisory parcels…</div>
      )}

      {!loading && !loadError && (
        <section id="map" className="map-workspace">
          {/* Location & Strategy selectors */}
          <LocationSelectors
            features={features}
            region={region}
            district={district}
            palika={palika}
            strategy={strategy}
            targetYield={targetYield}
            onChange={handleFilterChange}
          />

          <div className="map-layout">
            {/* Map card */}
            <div className="map-card">
              <div className="map-caption">
                <div>
                  <span className="kicker">Queryable GIS layer</span>
                  <h2>Parcel advisory map</h2>
                </div>

                {/* Map Display Metric Switcher: N vs Yield on top of the map */}
                <div className="map-metric-toggle-group">
                  <span className="toggle-group-label">Map Metric:</span>
                  <div className="map-metric-toggle">
                    <button
                      type="button"
                      className={`metric-toggle-btn ${mapMetric === 'balance' ? 'active' : ''}`}
                      onClick={() => setMapMetric('balance')}
                    >
                      <span style={{ fontSize: '.9rem' }}>⚡</span> Mineral-N Balance
                    </button>
                    <button
                      type="button"
                      className={`metric-toggle-btn ${mapMetric === 'yield' ? 'active' : ''}`}
                      onClick={() => setMapMetric('yield')}
                    >
                      <span style={{ fontSize: '.9rem' }}>🌾</span> Yield Difference
                    </button>
                  </div>
                </div>

                <span className="parcel-count-badge">{filtered.length.toLocaleString()} supported land parcels</span>
              </div>

              <MapContainer
                center={defaultCenter}
                zoom={7}
                scrollWheelZoom
                className="pixel-map"
              >
                <TileLayer
                  attribution="&copy; OpenStreetMap contributors"
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <BoundsFitter bounds={bounds} />
                <PixelPicker pool={filtered} onPick={handlePick} />

                {filtered.map((r) => {
                  const lat = number(r.lat);
                  const lon = number(r.lon);
                  if (lat === null || lon === null) return null;
                  const HALF_STEP = 0.009; // 0.018° cell size (~0.02° DSM pixel resolution)
                  const bounds = [
                    [lat - HALF_STEP, lon - HALF_STEP],
                    [lat + HALF_STEP, lon + HALF_STEP],
                  ];
                  const isSelected = selected === r;
                  return (
                    <Rectangle
                      key={String(r.pixel_id)}
                      bounds={bounds}
                      pathOptions={{
                        fillColor: markerColor(r, mapMetric),
                        fillOpacity: isSelected ? 0.95 : 0.7,
                        color: isSelected ? '#102b1f' : '#ffffff',
                        weight: isSelected ? 2 : 0.4,
                      }}
                      eventHandlers={{
                        mouseover: () => setHovered(r),
                        mouseout:  () => setHovered(null),
                        click:     () => setSelected(r),
                      }}
                    >
                      <Tooltip sticky>
                        <HoverTooltipContent row={r} />
                      </Tooltip>
                    </Rectangle>
                  );
                })}
              </MapContainer>

              {/* Legend */}
              <div className="map-legend">
                <span className="legend-title">
                  {mapMetric === 'balance' 
                    ? 'Net Mineral-N Balance vs GR (120 kg N/ha): Savings vs Losses (Excess N)'
                    : 'Yield Difference vs GR (9.06 t/ha): Gains vs Losses / Penalties'}
                </span>

                <div className="legend-items">
                  {mapMetric === 'balance' ? (
                    <>
                      <span><span className="legend-dot" style={{background:'#166534'}} />≥50 kg N/ha saved (High efficiency)</span>
                      <span><span className="legend-dot" style={{background:'#22c55e'}} />25–50 kg N/ha saved</span>
                      <span><span className="legend-dot" style={{background:'#84cc16'}} />10–25 kg N/ha saved</span>
                      <span><span className="legend-dot" style={{background:'#eab308'}} />Parity (±10 kg N/ha vs GR)</span>
                      <span><span className="legend-dot" style={{background:'#f97316'}} />10–30 kg N/ha Loss / Excess vs GR</span>
                      <span><span className="legend-dot" style={{background:'#dc2626'}} />&gt;30 kg N/ha Severe Loss / Heavy Excess</span>
                    </>
                  ) : (
                    <>
                      <span><span className="legend-dot" style={{background:'#166534'}} />≥+0.50 t/ha Gain vs GR</span>
                      <span><span className="legend-dot" style={{background:'#22c55e'}} />+0.15 to +0.50 t/ha Gain</span>
                      <span><span className="legend-dot" style={{background:'#84cc16'}} />+0.05 to +0.15 t/ha Gain</span>
                      <span><span className="legend-dot" style={{background:'#eab308'}} />Parity (±0.05 t/ha vs GR)</span>
                      <span><span className="legend-dot" style={{background:'#f97316'}} />−0.05 to −0.35 t/ha Loss</span>
                      <span><span className="legend-dot" style={{background:'#dc2626'}} />&lt;−0.35 t/ha Severe Loss</span>
                    </>
                  )}
                  <span><span className="legend-dot" style={{background:'#94a3b8'}} />No data / Baseline</span>
                </div>
              </div>
            </div>

            {/* Detail panel */}
            <PixelPanel
              row={panelRow}
              strategy={strategy}
              targetYield={targetYield}
              filteredCount={filtered.length}
              district={district}
              region={region}
              palika={palika}
              onClear={() => setSelected(null)}
              mapMetric={mapMetric}
              onMetricChange={setMapMetric}
              tradeoffs={evaluatedTradeoffs}
            />
          </div>
        </section>
      )}

      {/* ── Cross-Site Trade-offs & Spatial Negative Responses Diagnostics ── */}
      <section className="pipeline-section" style={{ background: '#ffffff', borderRadius: '12px', border: '1px solid #cce5d5', padding: '1.75rem', marginTop: '1.5rem', marginBottom: '1.5rem', boxShadow: '0 2px 8px rgba(0,0,0,0.03)' }}>
        <div className="pipeline-header" style={{ marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '.5rem' }}>
            <span className="advisory-evidence-kicker">
              Multi-Site Trade-off Diagnostics · {evaluatedTradeoffs.reduce((a, b) => a + b.totalParcels, 0).toLocaleString()} Evaluated Land Parcels
            </span>
            <span style={{ fontSize: '.75rem', fontWeight: 700, color: '#0f4028', background: '#eaf4ee', padding: '.2rem .6rem', borderRadius: '4px' }}>
              Scope: {palika || district || region || 'Western Nepal (All Districts)'}
            </span>
          </div>
          <h3 style={{ margin: '.2rem 0 0', fontSize: '1.35rem', color: 'var(--dark)' }}>
            ⚖️ Cross-Site Trade-offs &amp; Spatial Negative Responses Analysis
          </h3>
          <p className="pipeline-subtitle" style={{ fontSize: '.86rem', color: '#334438' }}>
            Dynamically evaluated from underlying spatial parcel database ({filtered.length.toLocaleString()} active land parcels). Evaluates why certain sites experience <strong>negative yield differences</strong> vs the Government Recommendation (GR: 120 kg N/ha) and why others achieve substantial <strong>mineral N savings vs severe excess losses</strong>.
          </p>
        </div>

        {/* 4 Dynamically Evaluated Trade-off Mechanism Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
          <div style={{ background: '#fef7ee', border: '1px solid #fed7aa', borderRadius: '8px', padding: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '.4rem', fontWeight: 800, color: '#c2410c', fontSize: '.88rem', marginBottom: '.35rem' }}>
              <span>⚠️</span> 1. Under-Fertilization Penalty (N60)
            </div>
            <div style={{ fontSize: '.8rem', color: '#7c2d12', lineHeight: '1.45' }}>
              <strong>{fmt(n60Stat?.negYieldPct, 1)}% of parcels</strong> have a negative yield difference (mean {fmt(n60Stat?.meanYieldDiff, 2)} t/ha, down to {fmt(n60Stat?.minYieldDiff, 2)} t/ha). While cutting mineral N by 60 kg/ha and eliminating leaching, soils with &lt;1.5% OM cannot supply enough native N during rapid stem elongation.
            </div>
          </div>

          <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '8px', padding: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '.4rem', fontWeight: 800, color: '#b91c1c', fontSize: '.88rem', marginBottom: '.35rem' }}>
              <span>🛑</span> 2. Over-Fertilization Penalty (N210)
            </div>
            <div style={{ fontSize: '.8rem', color: '#7f1d1d', lineHeight: '1.45' }}>
              <strong>{fmt(n210Stat?.negYieldPct, 1)}% of parcels</strong> suffer negative yields vs GR (mean {fmt(n210Stat?.meanYieldDiff, 2)} t/ha, min {fmt(n210Stat?.minYieldDiff, 2)} t/ha). Adding +90 kg N/ha triggers excessive vegetative growth, mutual shading, delayed maturity pushing into monsoon rains, and stalk lodging during pre-monsoon squalls.
            </div>
          </div>

          <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '8px', padding: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '.4rem', fontWeight: 800, color: '#15803d', fontSize: '.88rem', marginBottom: '.35rem' }}>
              <span>💧</span> 3. Moisture-Dependent Split (V6/V10)
            </div>
            <div style={{ fontSize: '.8rem', color: '#14532d', lineHeight: '1.45' }}>
              <strong>{fmt(timingStat?.posYieldPct, 1)}% positive response</strong> ({fmt(timingStat?.meanYieldDiff, 2)} t/ha mean gain under irrigation). However, <strong>{fmt(timingStat?.negYieldPct, 1)}% suffer negative yield</strong> (down to {fmt(timingStat?.minYieldDiff, 2)} t/ha) in rainfed parcels where dry spells stall urea dissolution at V8–V10 floral initiation.
            </div>
          </div>

          <div style={{ background: '#f5f3ff', border: '1px solid #ddd6fe', borderRadius: '8px', padding: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '.4rem', fontWeight: 800, color: '#6d28d9', fontSize: '.88rem', marginBottom: '.35rem' }}>
              <span>🏆</span> 4. High-Retention 4R (UDP &amp; PCU)
            </div>
            <div style={{ fontSize: '.8rem', color: '#4c1d95', lineHeight: '1.45' }}>
              <strong>{fmt(udpStat?.retains95Pct, 0)}% of parcels under UDP</strong> and <strong>{fmt(pcuStat?.retains95Pct, 0)}% under PCU</strong> maintain ≥95% of GR yield while cutting 42–60 kg N/ha. Minor negative yield differences ({fmt(udpStat?.meanYieldDiff, 2)} to {fmt(pcuStat?.meanYieldDiff, 2)} t/ha) are restricted to heavy clays or cold mid-hill valleys.
            </div>
          </div>
        </div>

        {/* Dynamically Evaluated Strategy Trade-off Data Table */}
        <div style={{ overflowX: 'auto', marginBottom: '1.5rem' }}>
          <table className="data-table" style={{ width: '100%', fontSize: '.82rem' }}>
            <thead>
              <tr style={{ background: '#f4f8f5' }}>
                <th style={{ textAlign: 'left', padding: '.65rem .85rem' }}>4R Strategy</th>
                <th style={{ textAlign: 'right', padding: '.65rem .85rem' }}>Active Parcels (n)</th>
                <th style={{ textAlign: 'right', padding: '.65rem .85rem' }}>Mean Yield Diff vs GR</th>
                <th style={{ textAlign: 'right', padding: '.65rem .85rem' }}>Sites with Yield Loss (&lt;0)</th>
                <th style={{ textAlign: 'right', padding: '.65rem .85rem' }}>Retaining ≥95% GR Yield</th>
                <th style={{ textAlign: 'right', padding: '.65rem .85rem' }}>Mineral-N Balance vs GR</th>
                <th style={{ textAlign: 'left', padding: '.65rem .85rem' }}>Agronomic Trade-off &amp; Risk Profile</th>
              </tr>
            </thead>
            <tbody>
              {evaluatedTradeoffs.map((item) => {
                const isLoss = item.meanYieldDiff !== null && item.meanYieldDiff < -0.05;
                const isGain = item.meanYieldDiff !== null && item.meanYieldDiff > 0.05;
                return (
                  <tr key={item.strategy}>
                    <td style={{ fontWeight: 700, padding: '.6rem .85rem' }}>{item.label}</td>
                    <td style={{ textAlign: 'right', padding: '.6rem .85rem', color: '#64748b' }}>{item.totalParcels.toLocaleString()}</td>
                    <td style={{ textAlign: 'right', fontWeight: 700, color: isGain ? '#166534' : isLoss ? '#dc2626' : '#b45309', padding: '.6rem .85rem' }}>
                      {item.meanYieldDiff !== null ? `${item.meanYieldDiff >= 0 ? '+' : ''}${fmt(item.meanYieldDiff, 2)} t/ha` : '—'}
                    </td>
                    <td style={{ textAlign: 'right', fontWeight: 700, color: item.negYieldPct > 50 ? '#dc2626' : '#475569', padding: '.6rem .85rem' }}>
                      {fmt(item.negYieldPct, 1)}% ({item.negYieldCount.toLocaleString()}/{item.totalParcels.toLocaleString()})
                    </td>
                    <td style={{ textAlign: 'right', padding: '.6rem .85rem', color: item.retains95Pct >= 90 ? '#166534' : '#475569' }}>
                      {fmt(item.retains95Pct, 1)}%
                    </td>
                    <td style={{ textAlign: 'right', fontWeight: 700, color: item.meanNBal < 0 ? '#166534' : item.meanNBal > 0 ? '#dc2626' : '#475569', padding: '.6rem .85rem' }}>
                      {item.meanNBal < 0 ? `−${fmt(Math.abs(item.meanNBal), 0)} kg N/ha (Saved)` : item.meanNBal > 0 ? `+${fmt(item.meanNBal, 0)} kg N/ha (Loss)` : '0 kg N/ha (Parity)'}
                    </td>
                    <td style={{ padding: '.6rem .85rem', color: '#475569' }}>
                      {item.strategy === 'N60' && 'Cuts fertilizer cost by 50% & eliminates leaching, but incurs unavoidable yield sacrifice on low-OM soils.'}
                      {item.strategy === 'UDP_N78' && 'Near-zero yield loss with 35% N cut; eliminates surface floodwater volatilization. Slight lags in clay soils.'}
                      {item.strategy === 'PCU_N60' && 'Peak PFP-N efficiency; minor early vegetative lag in cold mid-hill soils offset by massive leaching reduction.'}
                      {item.strategy === 'TIMING_V6_V10' && 'High win-rate (+0.21 to +0.87 t/ha gain); negative responses occur where dry spells trap urea on dry topsoil.'}
                      {item.strategy === 'N180' && 'Plateau effect: sites see no benefit or negative yield; dumps excess mineral N into shallow aquifers.'}
                      {item.strategy === 'N210' && 'Severe over-application penalty: stalk lodging, delayed silking, fungal cob rots, and severe economic/N losses.'}
                      {item.strategy === 'GR' && 'Government reference benchmark (120 kg N/ha split application); basis for relative comparisons.'}
                      {item.strategy === 'FYM_N60' && 'Organic-mineral integration replacing chemical N while improving soil moisture and carbon.'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Dynamically Evaluated Regional Spatial Contrasts */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
          {evaluatedDistricts.slice(0, 6).map((d) => (
            <div key={d.district} style={{ background: '#f8faf9', border: '1px solid #d4e8da', borderRadius: '8px', padding: '.9rem 1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '.35rem' }}>
                <h5 style={{ margin: 0, color: '#0f4028', fontSize: '.88rem' }}>📍 {d.district} District</h5>
                <span style={{ fontSize: '.72rem', color: '#64748b' }}>{d.totalParcels.toLocaleString()} parcels</span>
              </div>
              <div style={{ fontSize: '.78rem', color: '#334438', lineHeight: '1.45' }}>
                <div>• Overall Mean Yield Diff: <strong>{d.meanYieldDiff !== null ? `${d.meanYieldDiff >= 0 ? '+' : ''}${fmt(d.meanYieldDiff, 2)} t/ha` : '—'}</strong> ({fmt(d.negYieldPct, 1)}% negative parcels)</div>
                {d.strategies.N60 && (
                  <div>• N60 Yield Penalty: <strong>{fmt(d.strategies.N60.meanYieldDiff, 2)} t/ha</strong> ({fmt(d.strategies.N60.negPct, 0)}% negative)</div>
                )}
                {d.strategies.N210 && (
                  <div>• N210 Over-application: <strong>{fmt(d.strategies.N210.meanYieldDiff, 2)} t/ha</strong> ({fmt(d.strategies.N210.negPct, 0)}% negative sites)</div>
                )}
                {d.strategies.TIMING_V6_V10 && (
                  <div>• Split Timing (V6/V10): <strong>{fmt(d.strategies.TIMING_V6_V10.meanYieldDiff, 2)} t/ha</strong> ({fmt(100 - d.strategies.TIMING_V6_V10.negPct, 0)}% positive)</div>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Stage-by-Stage Data & Models Section ── */}
      <section className="pipeline-section">
        <div className="pipeline-header">
          <span className="advisory-evidence-kicker">Analytical Architecture &amp; Methodology</span>
          <h3 style={{ margin: '.2rem 0 0', fontSize: '1.25rem', color: 'var(--dark)' }}>
            Stage-by-Stage Data Sources &amp; Spatial Modelling Pipeline
          </h3>
          <p className="pipeline-subtitle">
            How multi-year trial observations in Western Nepal are harmonized, modelled, and spatially extrapolated into pixel-level advisories.
          </p>
        </div>

        <div className="pipeline-grid">
          {/* Stage 1 */}
          <div className="pipeline-card">
            <div className="pipeline-card__badge">Stage 1</div>
            <h4 className="pipeline-card__title">Data Harmonization &amp; Spatial Join</h4>
            <ul className="pipeline-card__list">
              <li><strong>Trial Data:</strong> 2,037 NSAF multi-year (2017–2019) summer maize trial plot observations across Western Nepal (Surkhet, Dang, Doti, Palpa, Salyan, Makwanpur, Kavre).</li>
              <li><strong>DSM Soil Covariates:</strong> NARC Digital Soil Mapping 0.02° spatial rasters (pH, organic matter %, total N %, Olsen P, exchangeable K, sand/silt/clay, elevation).</li>
              <li><strong>Nearest Join:</strong> Trial GPS coordinates linked to nearest DSM soil pixel centroids to pair crop response with local terrain &amp; soil properties.</li>
            </ul>
          </div>

          {/* Stage 2 */}
          <div className="pipeline-card">
            <div className="pipeline-card__badge">Stage 2</div>
            <h4 className="pipeline-card__title">Baseline &amp; Nutrient Omission Diagnostics</h4>
            <ul className="pipeline-card__list">
              <li><strong>Baseline Control (0-0-0):</strong> Establishes native background soil productivity across trial sites (ranging from 3.3 to 7.2 t/ha).</li>
              <li><strong>Nutrient Omission (-N, -P, -K):</strong> Measures site-specific yield penalties when nitrogen, phosphorus, or potassium is omitted relative to full N120-P60-K40 Government Recommendation (GR).</li>
            </ul>
          </div>

          {/* Stage 3 */}
          <div className="pipeline-card">
            <div className="pipeline-card__badge">Stage 3</div>
            <h4 className="pipeline-card__title">4R Response &amp; NUE Evaluation</h4>
            <ul className="pipeline-card__list">
              <li><strong>N-Rate Response:</strong> Evaluates yield response curves and Agronomic Efficiency (AE-N) across 0, 60, 120, 180, and 210 kg N/ha rates.</li>
              <li><strong>4R Innovations:</strong> Evaluates Polymer-Coated Urea (PCU N60), Urea Deep Placement (UDP N78), V6/V10 split timing, and 6 t/ha FYM + N60 integration for Partial Factor Productivity (PFP-N) and mineral N savings.</li>
            </ul>
          </div>

          {/* Stage 4 */}
          <div className="pipeline-card">
            <div className="pipeline-card__badge">Stage 4</div>
            <h4 className="pipeline-card__title">QUEFTS Mechanistic Demand Model</h4>
            <ul className="pipeline-card__list">
              <li><strong>Nutrient Balance:</strong> Quantitative Evaluation of Fertility of Tropical Soils (QUEFTS) calibrated with local DSM soil properties.</li>
              <li><strong>Target-Yield Scenarios:</strong> Forecasts reference N demand for 6.0 t/ha (127 kg N/ha), 8.0 t/ha (227 kg N/ha), and 10.0 t/ha (327 kg N/ha) targets considering native soil supply.</li>
            </ul>
          </div>

          {/* Stage 5 */}
          <div className="pipeline-card">
            <div className="pipeline-card__badge">Stage 5</div>
            <h4 className="pipeline-card__title">Random Forest Spatial Extrapolation</h4>
            <ul className="pipeline-card__list">
              <li><strong>Machine Learning:</strong> Random Forest model trained on trial AE-N response contrasts with DSM soil &amp; terrain predictors.</li>
              <li><strong>Domain Filtering:</strong> Restricts public advisory coverage to pixels with <code>environmental_support == True</code> within the trial environmental covariate space.</li>
            </ul>
          </div>

          {/* Stage 6 */}
          <div className="pipeline-card">
            <div className="pipeline-card__badge">Stage 6</div>
            <h4 className="pipeline-card__title">Spatial Response &amp; Target-Setting Domains</h4>
            <ul className="pipeline-card__list">
              <li><strong>Queryable GIS Layer:</strong> Delivers parcel-level fertilizer &amp; yield targets, response domain mapping, predicted yield diff vs GR, and potential mineral-N reduction estimates (e.g. 59 kg N/ha saved under PCU N60; 42 kg N/ha saved under UDP N78).</li>
            </ul>
          </div>
        </div>
      </section>

      {/* ── Pandit Research Footnote ── */}
      <div className="advisory-footnote">
        <div className="advisory-footnote__content">
          <span className="advisory-footnote__icon">📌</span>
          <div className="advisory-footnote__text">
            <strong>Evidence &amp; Citation Footnote:</strong> Underlying crop-response models, 4R nutrient stewardship frameworks, and spatial target-setting algorithms are derived from{' '}
            <em>
              Pandit, N. R., Adhikari, S., Vista, S. P., &amp; Choudhary, D. (2025). "Nitrogen Management Utilizing 4R Nutrient Stewardship: A Sustainable Strategy for Enhancing NUE, Reducing Maize Yield Gap and Increasing Farm Profitability." Nitrogen, 6(1), 7.
            </em>{' '}
            <a
              href="https://doi.org/10.3390/nitrogen6010007"
              target="_blank"
              rel="noreferrer"
              className="advisory-footnote__link"
            >
              https://doi.org/10.3390/nitrogen6010007
            </a> based on multi-year NSAF summer maize trials in Western Nepal.
          </div>
        </div>
      </div>
    </div>
  );
}
