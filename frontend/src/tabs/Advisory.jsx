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
import { STRATEGY_LABELS, fmt, number, nearestRow } from '../helpers';

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
      ? `+${fmt(nInc, 0)} kg N/ha (Extra needed / Loss)`
      : (stratN && stratN > 120 ? `+${stratN - 120} kg N/ha (Excess vs GR)` : '0 kg N/ha (Parity)');

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
            ? 'Colors represent Net Mineral-N Balance (Savings vs Additional N Required / Excess) vs standard Government Recommendation (120 kg N/ha):'
            : 'Colors represent Yield Difference (Gains vs Losses / Penalties in t/ha) vs standard Government Recommendation (9.06 t/ha):'}
        </p>
        
        {mapMetric === 'balance' ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '.45rem', marginBottom: '1.1rem', fontSize: '.8rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}>
              <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#166534', flexShrink: 0 }} />
              <span><strong style={{ color: '#166534' }}>≥50 kg N/ha saved</strong> (High efficiency gain)</span>
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
              <span><strong style={{ color: '#c2410c' }}>10–30 kg N/ha extra needed</strong> (Loss / Over-application)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}>
              <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#dc2626', flexShrink: 0 }} />
              <span><strong style={{ color: '#b91c1c' }}>&gt;30 kg N/ha extra needed</strong> (High loss / Heavy excess)</span>
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '.45rem', marginBottom: '1.1rem', fontSize: '.8rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}>
              <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#166534', flexShrink: 0 }} />
              <span><strong style={{ color: '#166534' }}>≥+0.50 t/ha Gain</strong> (Substantial yield advantage)</span>
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
              <span><strong style={{ color: '#c2410c' }}>−0.05 to −0.35 t/ha Loss</strong> (Moderate yield penalty)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}>
              <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#dc2626', flexShrink: 0 }} />
              <span><strong style={{ color: '#b91c1c' }}>&lt;−0.35 t/ha Severe Loss</strong> (Substantial yield penalty)</span>
            </div>
          </div>
        )}

        {/* Agronomic Trade-offs Note */}
        <div style={{ background: '#fef3c7', border: '1px solid #fde68a', borderRadius: '8px', padding: '.75rem .9rem', marginBottom: '1rem', fontSize: '.79rem', color: '#78350f', lineHeight: '1.45' }}>
          <strong>⚖️ Agronomic Trade-offs (Savings vs Losses vs GR):</strong>
          <div style={{ marginTop: '.35rem' }}>
            • <strong>Yield Losses &amp; Extra N:</strong> Lower rates (N60) reduce mineral fertilizer costs, but cause an average yield loss of ~0.50 t/ha below GR across Western Nepal, and in low-fertility parcels require additional N to sustain 8–10 t/ha. Over-application (N180, N210) adds 60–90 kg N/ha excess with zero extra yield and can cause lodging-induced losses (up to −1.13 t/ha).
          </div>
          <div style={{ marginTop: '.35rem' }}>
            • <strong>Efficiency Gains:</strong> Enhanced 4R options (PCU, UDP, V6/V10 timing) achieve 25–59 kg N/ha savings while sustaining yield or providing gains up to +0.87 t/ha.
          </div>
        </div>

        {/* How to interact Callout */}
        <div style={{ background: '#f8faf8', border: '1px solid #dbe8de', borderRadius: '6px', padding: '.75rem .9rem', fontSize: '.8rem', color: '#1b3a28', lineHeight: '1.5' }}>
          <div style={{ fontWeight: 700, marginBottom: '.25rem' }}>💡 How to explore the map:</div>
          <div>• <strong>Hover</strong> over any parcel to preview values.</div>
          <div>• <strong>Click any parcel</strong> on the map to lock its site-specific N rate, yield difference (gain/loss), and advisory details.</div>
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
      ? `+${fmt(nInc, 0)} kg N/ha (Additional N Required / Deficit vs GR)`
      : (stratN && stratN > 120 ? `+${stratN - 120} kg N/ha (Excess Over-application vs GR)` : '0 kg N/ha (Parity with GR)');

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

      <p className="result-note">
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
            ? ` The model indicates ${fmt(nInc, 0)} kg N/ha more may be required to reach target yield at this location.`
            : (stratN && stratN > 120 ? ` Applies ${stratN - 120} kg N/ha excess fertilizer relative to the standard government recommendation.` : '')
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

  return (
    <div className="tab-content">
      {/* Hero */}
      <section className="hero">
        <div>
          <span className="kicker">Extension &amp; Practice Translation Workspace · Translating Agronomic Science into Actionable Practice</span>
          <h2>Site-Specific Extension Advisory &amp; 4R Fertilizer Guidelines for Maize</h2>
          <p>
            Translating multi-year NSAF crop-response evidence and NARC Digital Soil Mapping into site-specific fertilizer recommendations, 4R stewardship practice guides (Right Source, Right Rate, Right Time, Right Place), fertilizer bag requirements (Urea, DAP, MOP, FYM), and actionable field advice for extension agents, lead farmers, and local government agricultural officers in Western Nepal.
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
                <span>{filtered.length.toLocaleString()} supported land parcels</span>
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

              {/* Legend with Metric Switcher */}
              <div className="map-legend">
                <div className="legend-header">
                  <span className="legend-title">
                    {mapMetric === 'balance' 
                      ? 'Net Mineral-N Balance vs GR (120 kg N/ha): Savings vs Extra N / Losses'
                      : 'Yield Difference vs GR (9.06 t/ha): Gains vs Losses / Penalties'}
                  </span>
                  
                  {/* Quick Metric Switch Buttons */}
                  <div style={{ display: 'inline-flex', background: '#e8f3ed', padding: '3px', borderRadius: '6px', gap: '3px' }}>
                    <button
                      type="button"
                      onClick={() => setMapMetric('balance')}
                      style={{
                        padding: '4px 10px',
                        borderRadius: '4px',
                        border: 'none',
                        background: mapMetric === 'balance' ? '#0f4028' : 'transparent',
                        color: mapMetric === 'balance' ? '#ffffff' : '#0f4028',
                        cursor: 'pointer',
                        fontWeight: 700,
                        fontSize: '.75rem',
                      }}
                    >
                      Mineral-N Balance
                    </button>
                    <button
                      type="button"
                      onClick={() => setMapMetric('yield')}
                      style={{
                        padding: '4px 10px',
                        borderRadius: '4px',
                        border: 'none',
                        background: mapMetric === 'yield' ? '#0f4028' : 'transparent',
                        color: mapMetric === 'yield' ? '#ffffff' : '#0f4028',
                        cursor: 'pointer',
                        fontWeight: 700,
                        fontSize: '.75rem',
                      }}
                    >
                      Yield Diff vs GR
                    </button>
                  </div>
                </div>

                <div className="legend-items">
                  {mapMetric === 'balance' ? (
                    <>
                      <span><span className="legend-dot" style={{background:'#166534'}} />≥50 kg N/ha saved (High efficiency)</span>
                      <span><span className="legend-dot" style={{background:'#22c55e'}} />25–50 kg N/ha saved</span>
                      <span><span className="legend-dot" style={{background:'#84cc16'}} />10–25 kg N/ha saved</span>
                      <span><span className="legend-dot" style={{background:'#eab308'}} />Parity (±10 kg N/ha vs GR)</span>
                      <span><span className="legend-dot" style={{background:'#f97316'}} />10–30 kg N/ha extra needed (Loss)</span>
                      <span><span className="legend-dot" style={{background:'#dc2626'}} />&gt;30 kg N/ha extra needed / Excess</span>
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
            />
          </div>
        </section>
      )}

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
