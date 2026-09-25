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

// Colour scale for map markers based on N reduction potential
function markerColor(row) {
  const nred = number(row.N_reduction_for_same_target_yield_kg_ha);
  if (nred === null) return '#94a3b8';
  if (nred >= 50) return '#166534';
  if (nred >= 25) return '#22c55e';
  if (nred >= 10) return '#fbbf24';
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
// Location selectors
// ---------------------------------------------------------------------------

function LocationSelectors({ features, region, district, palika, strategy, targetYield, onChange }) {
  const { regions, districts, palikas, strategies, targetYields } = useGeographyOptions(
    features, region, district
  );

  return (
    <div className="location-selectors">
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
  );
}

// ---------------------------------------------------------------------------
// Hover tooltip content
// ---------------------------------------------------------------------------

function HoverTooltipContent({ row }) {
  const nred = number(row.N_reduction_for_same_target_yield_kg_ha);
  const nInc = number(row.N_increase_for_same_target_yield_kg_ha);
  const mineralN = nred > 0 ? `−${fmt(nred, 0)} kg N/ha` :
                   nInc > 0 ? `+${fmt(nInc, 0)} kg N/ha` : '—';
  return (
    <>
      <strong>{row.palika || '—'}</strong>
      <br />{row.district}
      <br />N target: {fmt(row.strategy_N_rate_kg_ha, 0)} kg/ha
      <br />Yield diff vs GR: {fmt(row.predicted_yield_difference_from_GR_t_ha, 2)} t/ha
      <br />Mineral-N Δ: {mineralN}
    </>
  );
}

// ---------------------------------------------------------------------------
// Pixel detail panel
// ---------------------------------------------------------------------------

function PixelPanel({ row }) {
  if (!row) {
    return (
      <aside className="pixel-result">
        <span className="kicker">Selected pixel</span>
        <h2 className="pixel-heading">Click the map</h2>
        <p className="coordinates">—</p>
        <p className="result-note">
          Hover over a pixel to preview values. Click to lock the detailed advisory panel.
        </p>
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
  const retains = row.retains_95pct_GR;

  const mineralN = nred > 0
    ? `−${fmt(nred, 0)} kg N/ha (potential reduction)`
    : nInc > 0
      ? `+${fmt(nInc, 0)} kg N/ha (more N may be needed)`
      : '—';

  const supportLabel = support === true || String(support).toLowerCase() === 'true'
    ? 'Environmentally supported'
    : 'Not supported';
  const retainLabel = retains === true || String(retains).toLowerCase() === 'true'
    ? 'Retains ≥95% of GR yield'
    : 'Below 95% GR yield retention';

  return (
    <aside className="pixel-result">
      <span className="kicker">Selected pixel</span>
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
          <dt>Expected yield difference vs Gov. Rec.</dt>
          <dd>{yieldDiff === null ? '—' :
            `${yieldDiff >= 0 ? '+' : ''}${fmt(yieldDiff, 2)} t/ha`}</dd>
        </div>
        <div>
          <dt>Potential mineral-N change</dt>
          <dd>{mineralN}</dd>
        </div>
        {ae !== null && (
          <div>
            <dt>AE-N (agronomic efficiency)</dt>
            <dd>{fmt(ae, 1)} kg grain / kg N</dd>
          </div>
        )}
        {pfpField !== null && (
          <div>
            <dt>PFP-N (partial factor productivity)</dt>
            <dd>{fmt(pfpField, 1)} kg grain / kg N</dd>
          </div>
        )}
        <div>
          <dt>Pixel support</dt>
          <dd>{supportLabel}</dd>
        </div>
        <div>
          <dt>Yield uncertainty</dt>
          <dd>{retainLabel}</dd>
        </div>
      </dl>

      <p className="result-note">
        {yieldDiff !== null
          ? (yieldDiff >= 0
            ? `This strategy yields ${fmt(yieldDiff, 2)} t/ha above the government comparator at this pixel.`
            : `This strategy yields ${fmt(Math.abs(yieldDiff), 2)} t/ha below the government comparator.`)
          : ''
        }
        {nred > 0
          ? ` Potential mineral-N saving of ${fmt(nred, 0)} kg N/ha for the same target yield.`
          : nInc > 0
            ? ` The model indicates ${fmt(nInc, 0)} kg N/ha more may be required for the same target yield.`
            : ''
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
          <span className="kicker">NSAF Maize · Western Nepal · 4R Nutrient Stewardship</span>
          <h2>Site-Specific Soil &amp; Fertilizer Advisory for Summer Maize</h2>
          <p>
            Empowering smallholder farmers and agricultural extension with spatially targeted 4R nutrient recommendations, yield-gap reduction strategies, and optimized fertilizer investments based on multi-site NSAF crop response evidence and NARC Digital Soil Mapping across Western Nepal.
          </p>
        </div>
      </section>

      {/* ── Data Source & Pandit 4R Research Summary Banner ── */}
      <section className="advisory-evidence-banner">
        <div className="advisory-evidence-header">
          <div>
            <span className="advisory-evidence-kicker">Data Source &amp; Evidence Base</span>
            <h3 style={{ margin: '.2rem 0 0', fontSize: '1.25rem', color: 'var(--dark)' }}>
              NSAF Summer Maize Trials in Western Nepal
            </h3>
          </div>
          <span className="advisory-evidence-tag">Pandit et al. (2025) 4R Stewardship</span>
        </div>
        
        <p className="advisory-evidence-desc">
          This public advisory tool translates multi-year (2017–2019) crop-response data from <strong>Nepal Seed and Agro-Input Program (NSAF) field trials</strong> conducted across summer maize hubs in Western Nepal (including Surkhet, Dang, Doti, Palpa, Salyan, Makwanpur, and Kavre). Trial GPS observations are linked with <strong>NARC Digital Soil Mapping (DSM)</strong> rasters at 0.02° spatial resolution to derive site-specific fertilizer recommendations.
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

      {/* Data warning */}
      {loadError && (
        <section className="data-warning">
          <strong>Pixel layer not available.</strong>
          <span>
            Run scripts/7_publish_web_gis.py, commit the generated files, and push to main.
          </span>
        </section>
      )}

      {loading && (
        <div className="loading">Loading advisory pixels…</div>
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
                  <h2>Pixel advisory map</h2>
                </div>
                <span>{filtered.length.toLocaleString()} supported pixels</span>
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
                        fillColor: markerColor(r),
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
                <span className="legend-title">Potential Mineral-N Reduction for Same Target Yield (vs GR N120)</span>
                <div className="legend-items">
                  <span><span className="legend-dot" style={{background:'#166534'}} />≥50 kg N/ha reduction</span>
                  <span><span className="legend-dot" style={{background:'#22c55e'}} />25–50 kg N/ha reduction</span>
                  <span><span className="legend-dot" style={{background:'#fbbf24'}} />10–25 kg N/ha reduction</span>
                  <span><span className="legend-dot" style={{background:'#f97316'}} />&lt;10 kg N/ha reduction</span>
                  <span><span className="legend-dot" style={{background:'#94a3b8'}} />No data / Baseline</span>
                </div>
              </div>
            </div>

            {/* Detail panel */}
            <PixelPanel row={panelRow} />
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
            <h4 className="pipeline-card__title">Public Advisory Target Setting</h4>
            <ul className="pipeline-card__list">
              <li><strong>Queryable GIS Layer:</strong> Delivers pixel-level 4R recommendations, predicted yield diff vs GR, and potential mineral N savings (e.g. 59 kg N/ha saved under PCU N60; 42 kg N/ha saved under UDP N78).</li>
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
