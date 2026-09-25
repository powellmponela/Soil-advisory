import { useEffect, useMemo, useState } from 'react';
import { MapContainer, CircleMarker, TileLayer, Tooltip, useMapEvents } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import './index.css';

const STRATEGY_LABELS = {
  GR: 'Government N120',
  N60: 'N60',
  N180: 'N180',
  N210: 'N210',
  TIMING_V6_V10: 'V6/V10 timing',
  FYM_N60: 'FYM + N60',
  PCU_N120: 'PCU N120',
  PCU_N60: 'PCU N60',
  UDP_N78: 'UDP N78'
};

const METRICS = {
  yield: {
    label: 'Yield difference from government recommendation',
    field: 'predicted_yield_difference_from_GR_t_ha',
    unit: 't/ha'
  },
  nreq: {
    label: 'N required for same target yield',
    field: 'N_required_for_same_target_yield_kg_ha',
    unit: 'kg N/ha'
  },
  nchange: {
    label: 'N reduction / increase for same target yield',
    field: 'N_change_for_same_target_yield_kg_ha',
    unit: 'kg N/ha'
  },
  ae: {
    label: 'Predicted agronomic efficiency of N',
    field: 'predicted_AE_N_kg_grain_per_kg_N',
    unit: 'kg grain/kg N'
  },
  pfp: {
    label: 'Predicted partial factor productivity of N',
    field: 'predicted_PFP_N_kg_grain_per_kg_N',
    unit: 'kg grain/kg N'
  }
};

const number = (value) => {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
};
const fmt = (value, digits = 1) => {
  const n = number(value);
  return n === null ? '—' : n.toFixed(digits);
};
const bool = (v) => v === true || String(v).toLowerCase() === 'true';

function distance2(a, lat, lon) {
  const x = number(a.lon) - lon;
  const y = number(a.lat) - lat;
  return x * x + y * y;
}

function PixelPicker({ onPick }) {
  useMapEvents({
    click(e) {
      onPick(e.latlng.lat, e.latlng.lng);
    }
  });
  return null;
}

function App() {
  const [features, setFeatures] = useState([]);
  const [loadError, setLoadError] = useState('');
  const [strategy, setStrategy] = useState('PCU_N60');
  const [target, setTarget] = useState('8');
  const [metric, setMetric] = useState('nchange');
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    fetch('/advisory_pixels.geojson')
      .then((r) => {
        if (!r.ok) throw new Error('Pixel publication file is not available yet.');
        return r.json();
      })
      .then((geo) => {
        const rows = (geo.features || []).map((f) => ({
          ...(f.properties || {}),
          lon: f.geometry?.coordinates?.[0],
          lat: f.geometry?.coordinates?.[1]
        }));
        setFeatures(rows.filter((r) => number(r.lat) !== null && number(r.lon) !== null));
      })
      .catch((e) => setLoadError(e.message));
  }, []);

  const strategies = useMemo(
    () => [...new Set(features.map((r) => String(r.strategy)).filter(Boolean))],
    [features]
  );
  const targets = useMemo(
    () => [...new Set(features.map((r) => String(r.target_yield_t_ha)).filter(Boolean))]
      .sort((a, b) => Number(a) - Number(b)),
    [features]
  );

  useEffect(() => {
    if (strategies.length && !strategies.includes(strategy)) setStrategy(strategies[0]);
  }, [strategies, strategy]);
  useEffect(() => {
    if (targets.length && !targets.includes(target)) setTarget(targets[0]);
  }, [targets, target]);

  const filtered = useMemo(
    () => features.filter(
      (r) => String(r.strategy) === String(strategy) &&
             String(r.target_yield_t_ha) === String(target) &&
             bool(r.environmental_support)
    ),
    [features, strategy, target]
  );

  useEffect(() => {
    if (filtered.length) setSelected(filtered[0]);
    else setSelected(null);
  }, [strategy, target, features]);

  const center = useMemo(() => {
    if (!filtered.length) return [28.3, 82.0];
    const lat = filtered.reduce((s, r) => s + number(r.lat), 0) / filtered.length;
    const lon = filtered.reduce((s, r) => s + number(r.lon), 0) / filtered.length;
    return [lat, lon];
  }, [filtered]);

  const pickNearest = (lat, lon) => {
    if (!filtered.length) return;
    let best = filtered[0];
    let bestD = distance2(best, lat, lon);
    for (const row of filtered.slice(1)) {
      const d = distance2(row, lat, lon);
      if (d < bestD) {
        best = row;
        bestD = d;
      }
    }
    setSelected(best);
  };

  const value = selected ? number(selected[METRICS[metric].field]) : null;
  const nReduction = selected ? number(selected.N_reduction_for_same_target_yield_kg_ha) : null;
  const nIncrease = selected ? number(selected.N_increase_for_same_target_yield_kg_ha) : null;
  const yieldDiff = selected ? number(selected.predicted_yield_difference_from_GR_t_ha) : null;
  const nRequired = selected ? number(selected.N_required_for_same_target_yield_kg_ha) : null;
  const refN = selected ? number(selected.reference_N_demand_kg_ha) : null;
  const ae = selected ? number(selected.predicted_AE_N_kg_grain_per_kg_N) : null;
  const pfp = selected ? number(selected.predicted_PFP_N_kg_grain_per_kg_N) : null;

  const interpretation = () => {
    if (!selected) return 'Select a strategy and target yield, then click a modelled pixel on the map.';
    const y = yieldDiff === null
      ? 'Modelled yield difference is unavailable.'
      : yieldDiff >= 0
        ? 'Modelled yield is ' + fmt(yieldDiff, 2) + ' t/ha above the government comparator.'
        : 'Modelled yield is ' + fmt(Math.abs(yieldDiff), 2) + ' t/ha below the government comparator.';
    const n = nReduction !== null && nReduction > 0
      ? ' Potential mineral-N reduction is ' + fmt(nReduction, 0) + ' kg N/ha for the same target yield.'
      : nIncrease !== null && nIncrease > 0
        ? ' The model indicates ' + fmt(nIncrease, 0) + ' kg N/ha more may be required for the same target yield.'
        : '';
    return y + n + ' This is a modelled target-setting estimate, not a field-specific fertilizer prescription.';
  };

  return (
    <div>
      <header className="public-header">
        <div>
          <span className="kicker">NSAF maize • Nepal</span>
          <h1>Soil & Nutrient Advisory</h1>
        </div>
        <nav>
          <a href="#map">Pixel advisory</a>
          <a href="#method">Methodology</a>
          <a className="staff-link" href="/staff/login">Research workspace</a>
        </nav>
      </header>

      <main>
        <section className="hero">
          <div>
            <span className="kicker">From trial response to spatial fertilizer target setting</span>
            <h2>Query modelled fertilizer demand and yield response at a mapped pixel.</h2>
            <p>
              Choose a target yield and nutrient-management strategy, then click the map.
              The public interface reports only modelled, environmentally supported pixels
              produced by the spatial workflow.
            </p>
          </div>
        </section>

        {loadError && (
          <section className="data-warning">
            <strong>Pixel layer not published yet.</strong>
            <span>
              Run scripts/7_publish_web_gis.py locally, commit the generated advisory_pixels.geojson,
              advisory_pixels.csv and advisory_metadata.json files, and push to main.
            </span>
          </section>
        )}

        <section id="map" className="map-workspace">
          <div className="map-controls">
            <label>
              Target yield
              <select value={target} onChange={(e) => setTarget(e.target.value)}>
                {targets.map((x) => <option key={x} value={x}>{x} t/ha</option>)}
              </select>
            </label>
            <label>
              Strategy
              <select value={strategy} onChange={(e) => setStrategy(e.target.value)}>
                {strategies.map((x) => <option key={x} value={x}>{STRATEGY_LABELS[x] || x}</option>)}
              </select>
            </label>
            <label>
              Map variable
              <select value={metric} onChange={(e) => setMetric(e.target.value)}>
                {Object.entries(METRICS).map(([key, m]) => (
                  <option key={key} value={key}>{m.label}</option>
                ))}
              </select>
            </label>
          </div>

          <div className="map-layout">
            <div className="map-card">
              <div className="map-caption">
                <div>
                  <span className="kicker">Queryable GIS layer</span>
                  <h2>{METRICS[metric].label}</h2>
                </div>
                <span>{filtered.length.toLocaleString()} supported pixels</span>
              </div>

              <MapContainer center={center} zoom={7} scrollWheelZoom className="pixel-map">
                <TileLayer
                  attribution="&copy; OpenStreetMap contributors"
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <PixelPicker onPick={pickNearest} />
                {filtered.map((r) => (
                  <CircleMarker
                    key={String(r.pixel_id)}
                    center={[number(r.lat), number(r.lon)]}
                    radius={3}
                    pathOptions={{ fillOpacity: 0.72, weight: 0 }}
                    eventHandlers={{ click: () => setSelected(r) }}
                  >
                    <Tooltip>
                      {STRATEGY_LABELS[r.strategy] || r.strategy}<br />
                      {METRICS[metric].label}: {fmt(r[METRICS[metric].field], 1)} {METRICS[metric].unit}
                    </Tooltip>
                  </CircleMarker>
                ))}
              </MapContainer>
            </div>

            <aside className="pixel-result">
              <span className="kicker">Selected pixel</span>
              <h2>{selected ? (selected.palika || selected.district || selected.pixel_id) : 'Click the map'}</h2>
              <p className="coordinates">
                {selected ? fmt(selected.lat, 5) + ', ' + fmt(selected.lon, 5) : '—'}
              </p>

              <div className="primary-value">
                <small>{METRICS[metric].label}</small>
                <strong>{fmt(value, metric === 'yield' ? 2 : 1)}</strong>
                <span>{METRICS[metric].unit}</span>
              </div>

              <dl>
                <div><dt>Target yield</dt><dd>{selected ? fmt(selected.target_yield_t_ha, 1) + ' t/ha' : '—'}</dd></div>
                <div><dt>Strategy</dt><dd>{selected ? (STRATEGY_LABELS[selected.strategy] || selected.strategy) : '—'}</dd></div>
                <div><dt>Yield difference vs GR</dt><dd>{fmt(yieldDiff, 2)} t/ha</dd></div>
                <div><dt>N required</dt><dd>{fmt(nRequired, 0)} kg N/ha</dd></div>
                <div><dt>Reference N demand</dt><dd>{fmt(refN, 0)} kg N/ha</dd></div>
                <div><dt>Potential N reduction</dt><dd>{fmt(nReduction, 0)} kg N/ha</dd></div>
                <div><dt>AE-N</dt><dd>{fmt(ae, 1)}</dd></div>
                <div><dt>PFP-N</dt><dd>{fmt(pfp, 1)}</dd></div>
              </dl>

              <p className="result-note">{interpretation()}</p>
            </aside>
          </div>
        </section>

        <section id="method" className="method">
          <span className="kicker">Methodology</span>
          <h2>How to interpret the pixel advisory</h2>
          <p>
            The map uses the same pixel-level outputs generated by the spatial modelling workflow.
            NSAF treatment-response evidence is linked to DSM/NARC soil covariates and QUEFTS-derived
            nutrient demand. Strategy-specific models estimate yield response and nutrient-use efficiency.
          </p>
          <p>
            AE-N is used where an appropriate zero-N reference is available. PFP-N is used for FYM,
            PCU and UDP strategies where that reference is not consistently available. Potential mineral-N
            reduction is the modelled difference in N requirement for the same target yield; it is not a
            measured reduction in nitrogen loss.
          </p>
          <p className="caution">
            DSM values are predicted soil properties rather than direct measurements at each pixel.
            Results are spatial response and target-setting estimates and should be interpreted with
            model-support and local agronomic information.
          </p>
        </section>
      </main>

      <footer>
        Public interface: modelled supported pixels only • Research data and models remain restricted
      </footer>
    </div>
  );
}

export default App;
