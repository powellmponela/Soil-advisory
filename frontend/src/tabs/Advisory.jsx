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
  CircleMarker,
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

function LocationSelectors({ features, region, district, palika, onChange }) {
  const { regions, districts, palikas } = useGeographyOptions(
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

  // Geography cascade state
  const [region, setRegion]     = useState(ALL);
  const [district, setDistrict] = useState(ALL);
  const [palika, setPalika]     = useState(ALL);

  // Pixel selection (click = locked)
  const [selected, setSelected] = useState(null);
  // Hover row (independent from selected)
  const [hovered, setHovered]   = useState(null);

  const handleGeoChange = useCallback((level, value) => {
    if (level === 'region') {
      setRegion(value);
      setDistrict(ALL);
      setPalika(ALL);
    } else if (level === 'district') {
      setDistrict(value);
      setPalika(ALL);
    } else {
      setPalika(value);
    }
    setSelected(null);
  }, []);

  // Filtered pixel pool based on geography selection
  const { filtered, bounds } = useFilteredPixels(features, { region, district, palika });

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
          <span className="kicker">NSAF maize · Nepal · Pixel-based advisory</span>
          <h2>Pixel-based fertilizer and yield advisory</h2>
          <p>
            Explore trial-supported nitrogen targets, expected yield response and
            potential mineral-N reduction for model-supported locations.
          </p>
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
          {/* Location selectors */}
          <LocationSelectors
            features={features}
            region={region}
            district={district}
            palika={palika}
            onChange={handleGeoChange}
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

                {filtered.map((r) => (
                  <CircleMarker
                    key={String(r.pixel_id)}
                    center={[number(r.lat), number(r.lon)]}
                    radius={selected === r ? 7 : 4}
                    pathOptions={{
                      fillColor: markerColor(r),
                      fillOpacity: selected === r ? 1 : 0.75,
                      color: selected === r ? '#fff' : 'transparent',
                      weight: selected === r ? 1.5 : 0,
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
                  </CircleMarker>
                ))}
              </MapContainer>

              {/* Legend */}
              <div className="map-legend">
                <span className="legend-title">Mineral-N reduction potential</span>
                <div className="legend-items">
                  <span><span className="legend-dot" style={{background:'#166534'}} />≥50 kg N/ha</span>
                  <span><span className="legend-dot" style={{background:'#22c55e'}} />25–50 kg N/ha</span>
                  <span><span className="legend-dot" style={{background:'#fbbf24'}} />10–25 kg N/ha</span>
                  <span><span className="legend-dot" style={{background:'#f97316'}} />&lt;10 kg N/ha</span>
                  <span><span className="legend-dot" style={{background:'#94a3b8'}} />No data</span>
                </div>
              </div>
            </div>

            {/* Detail panel */}
            <PixelPanel row={panelRow} />
          </div>
        </section>
      )}
    </div>
  );
}
