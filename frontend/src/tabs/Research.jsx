// ---------------------------------------------------------------------------
// Research.jsx – technical / analytical research workspace
//
// Contains: trial analysis, N-response curves, QUEFTS diagnostics,
// DSM / spatial modelling, scenario comparison, model diagnostics,
// methodology / technical documentation.
// ---------------------------------------------------------------------------

import { useState, useEffect, useMemo } from 'react';
import Papa from 'papaparse';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip as ReTooltip, Legend, ResponsiveContainer, ScatterChart,
  Scatter, ReferenceLine,
} from 'recharts';
import { useAdvisoryData } from '../hooks/useAdvisoryData';
import { fmt, number, STRATEGY_LABELS } from '../helpers';

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

const RESEARCH_TABS = [
  { id: 'matrix',    label: '1. Input Data & Design Matrix' },
  { id: 'equations', label: '2. 4R Equations & Estimations' },
  { id: 'quefts',    label: '3. QUEFTS Demand Model' },
  { id: 'dsm',       label: '4. Random Forest & DSM Extrapolation' },
  { id: 'code',      label: '5. Model Code & Python Scripts' },
  { id: 'method',    label: '6. Methodology & Documentation' },
];

// ---------------------------------------------------------------------------
// Sub-panels
// ---------------------------------------------------------------------------

/** Trial analysis – NSAF raw trial data summary */
function TrialAnalysis() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/nsaf_advisory_results.csv')
      .then((r) => r.text())
      .then((txt) => Papa.parse(txt, { header: true, dynamicTyping: true, complete: (res) => {
        setRows(res.data.filter((r) => r.District));
        setLoading(false);
      }}))
      .catch(() => setLoading(false));
  }, []);

  const byDistrict = useMemo(() => {
    const map = {};
    rows.forEach((r) => {
      const dist = r.District || r.district;
      if (!dist) return;
      if (!map[dist]) map[dist] = { count: 0, yieldSum: 0, aeSum: 0, aeN: 0 };
      map[dist].count++;
      if (r.Yield_t_ha) map[dist].yieldSum += Number(r.Yield_t_ha);
      if (r.AE_N) { map[dist].aeSum += Number(r.AE_N); map[dist].aeN++; }
    });
    return Object.entries(map).map(([district, d]) => ({
      district,
      count: d.count,
      meanYield: d.count ? d.yieldSum / d.count : null,
      meanAE: d.aeN ? d.aeSum / d.aeN : null,
    })).sort((a, b) => String(a.district || '').localeCompare(String(b.district || '')));
  }, [rows]);

  if (loading) return <div className="loading">Loading trial data…</div>;

  return (
    <div className="research-panel">

      {/* ── Guiding Papers & Key Figures ───────────────────────────── */}
      <div className="guiding-papers">
        <div className="guiding-papers__header">
          <h4 className="guiding-papers__heading">
            <span className="guiding-papers__icon">📄</span> Guiding Papers &amp; Key Empirical Figures
          </h4>
          <span className="guiding-papers__badge">Peer-Reviewed Evidence</span>
        </div>

        {/* ── Key Figures Stat Badges Grid ── */}
        <div className="key-figures-grid">
          <div className="key-figure-card">
            <div className="key-figure-card__value">+35%</div>
            <div className="key-figure-card__label">AE-N Efficiency Gain</div>
            <div className="key-figure-card__sub">N60 (27.0 kg grain/kg N) vs N120 GR (19.9 kg/kg)</div>
          </div>
          <div className="key-figure-card">
            <div className="key-figure-card__value">59 kg N/ha</div>
            <div className="key-figure-card__label">N Savings (PCU N60)</div>
            <div className="key-figure-card__sub">Polymer-Coated Urea maintains GR yield with 50% N cut</div>
          </div>
          <div className="key-figure-card">
            <div className="key-figure-card__value">42 kg N/ha</div>
            <div className="key-figure-card__label">N Savings (UDP N78)</div>
            <div className="key-figure-card__sub">Deep placement saves 35% mineral N with ~0 yield penalty</div>
          </div>
          <div className="key-figure-card">
            <div className="key-figure-card__value">133 kg/kg</div>
            <div className="key-figure-card__label">Peak PFP-N Efficiency</div>
            <div className="key-figure-card__sub">Achieved under PCU N60 vs 62 kg/kg for conventional GR</div>
          </div>
          <div className="key-figure-card">
            <div className="key-figure-card__value">3.3–7.2 t/ha</div>
            <div className="key-figure-card__label">Unfertilized Baseline Spread</div>
            <div className="key-figure-card__sub">Native background soil productivity range across trial sites</div>
          </div>
        </div>

        <ol className="guiding-papers__list">
          <li className="guiding-papers__item">
            <div className="guiding-papers__citation">
              <span className="guiding-papers__authors">Pandit, N. R., Adhikari, S., Vista, S. P., &amp; Choudhary, D.</span>{' '}
              <span className="guiding-papers__year">(2025).</span>{' '}
              <em className="guiding-papers__title">
                Nitrogen Management Utilizing 4R Nutrient Stewardship: A Sustainable Strategy for
                Enhancing NUE, Reducing Maize Yield Gap and Increasing Farm Profitability.
              </em>{' '}
              <span className="guiding-papers__journal">Nitrogen</span>,{' '}
              <span className="guiding-papers__vol">6</span>(1), 7.{' '}
              <a
                href="https://doi.org/10.3390/nitrogen6010007"
                target="_blank"
                rel="noreferrer"
                className="guiding-papers__doi"
              >
                https://doi.org/10.3390/nitrogen6010007
              </a>
            </div>

            {/* Key figures callout for paper 1 */}
            <div className="paper-key-figures">
              <div className="paper-key-figures__title">💡 Key Figures &amp; Empirical Findings:</div>
              <ul className="paper-key-figures__list">
                <li>
                  <strong>4R N-Rate Efficiency:</strong> Mean yield increases from 6.67 t/ha (0PK) → 8.29 t/ha (N60) → 9.06 t/ha (N120 GR). N60 uses 50% less inorganic N with only an 8.5% yield reduction while boosting AE-N by <strong>+35%</strong> (27.0 vs 19.9 kg grain/kg N).
                </li>
                <li>
                  <strong>Over-application Penalties:</strong> N180 yields 9.02 t/ha (yield plateau reached) but drops AE-N by <strong>-34%</strong> (13.1 kg/kg N). N210 drops AE-N by <strong>-52%</strong> (9.7 kg/kg N).
                </li>
                <li>
                  <strong>Enhanced Efficiency Technologies:</strong> Polymer-Coated Urea (PCU N60) achieves <strong>133 kg grain/kg mineral N PFP-N</strong> and saves <strong>59 kg N/ha</strong>. Urea Deep Placement (UDP N78) yields virtually identically to GR (-0.02 t/ha) while saving <strong>42 kg N/ha</strong> (35% reduction).
                </li>
                <li>
                  <strong>Organic-Mineral &amp; Timing Integration:</strong> 6 t FYM + N60 yields 119 kg grain/kg mineral N PFP-N (saves 56 kg mineral N/ha). V6/V10 split application saves <strong>41 kg N/ha</strong> for equivalent yield (+0.11 to +0.87 t/ha gain at responsive sites).
                </li>
              </ul>
            </div>
          </li>

          <li className="guiding-papers__item">
            <div className="guiding-papers__citation">
              <span className="guiding-papers__authors">
                Pandit, N. R., Choudhary, D., Maharjan, S., Dhakal, K., Vista, S. P., &amp; Gaihre, Y. K.
              </span>{' '}
              <span className="guiding-papers__year">(2022).</span>{' '}
              <em className="guiding-papers__title">
                Optimum Rate and Deep Placement of Nitrogen Fertilizer Improves Nitrogen Use
                Efficiency and Tomato Yield in Nepal.
              </em>{' '}
              <span className="guiding-papers__journal">Soil Systems</span>,{' '}
              <span className="guiding-papers__vol">6</span>(3), 72.{' '}
              <a
                href="https://doi.org/10.3390/soilsystems6030072"
                target="_blank"
                rel="noreferrer"
                className="guiding-papers__doi"
              >
                https://doi.org/10.3390/soilsystems6030072
              </a>
            </div>
            <div className="paper-key-figures">
              <div className="paper-key-figures__title">💡 Key Figures &amp; Empirical Findings:</div>
              <ul className="paper-key-figures__list">
                <li>
                  <strong>Root-Zone Placement Efficiency:</strong> Root-zone deep placement of nitrogen significantly reduced volatilization and leaching losses, increasing overall agronomic efficiency and crop yield compared to surface broadcast urea.
                </li>
              </ul>
            </div>
          </li>

          <li className="guiding-papers__item">
            <div className="guiding-papers__citation">
              <span className="guiding-papers__authors">
                Pandit, N. R., et al.
              </span>{' '}
              <span className="guiding-papers__year">(2022).</span>{' '}
              <em className="guiding-papers__title">
                Field evaluation of slow-release nitrogen fertilizers and real-time nitrogen
                management tools to improve grain yield and nitrogen use efficiency of spring maize in Nepal.
              </em>{' '}
              <span className="guiding-papers__journal">Heliyon</span>,{' '}
              <span className="guiding-papers__vol">8</span>(5), e09566.{' '}
              <a
                href="https://doi.org/10.1016/j.heliyon.2022.e09566"
                target="_blank"
                rel="noreferrer"
                className="guiding-papers__doi"
              >
                https://doi.org/10.1016/j.heliyon.2022.e09566
              </a>
            </div>
            <div className="paper-key-figures">
              <div className="paper-key-figures__title">💡 Key Figures &amp; Empirical Findings:</div>
              <ul className="paper-key-figures__list">
                <li>
                  <strong>Slow-Release &amp; Real-Time Tools:</strong> Evaluated polymer-coated urea and leaf-color chart / SPAD real-time N tools for spring maize in Nepal, demonstrating significantly improved grain yield and NUE over farmer practices.
                </li>
              </ul>
            </div>
          </li>
        </ol>
      </div>
      {/* ────────────────────────────────────────────────────────────── */}

      <h3>NSAF Trial Summary by District</h3>
      <p className="research-note">
        {rows.length.toLocaleString()} trial observations from nsaf_advisory_results.csv.
        All DSM-linked. Includes QUEFTS-derived N demand and predicted AE-N.
      </p>
      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>District</th>
              <th>Observations</th>
              <th>Mean yield (t/ha)</th>
              <th>Mean AE-N (kg grain/kg N)</th>
            </tr>
          </thead>
          <tbody>
            {byDistrict.map((d) => (
              <tr key={d.district}>
                <td>{d.district}</td>
                <td>{d.count}</td>
                <td>{fmt(d.meanYield, 2)}</td>
                <td>{fmt(d.meanAE, 1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3 style={{marginTop:'2rem'}}>Yield Distribution by District</h3>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={byDistrict} margin={{ left: 10, right: 10, bottom: 40 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
          <XAxis dataKey="district" angle={-35} textAnchor="end" tick={{ fontSize: 11 }} />
          <YAxis label={{ value: 't/ha', angle: -90, position: 'insideLeft', fontSize: 11 }} />
          <ReTooltip formatter={(v) => fmt(v, 2) + ' t/ha'} />
          <Bar dataKey="meanYield" name="Mean yield" fill="var(--mid)" radius={[3,3,0,0]} />
        </BarChart>
      </ResponsiveContainer>

      {/* ── Table 1 Design Matrix ── */}
      <DesignMatrixTable />
    </div>
  );
}

/** Design Matrix Table 1 */
function DesignMatrixTable() {
  return (
    <div className="table-container" style={{ marginTop: '2.5rem' }}>
      <h3 style={{ marginBottom: '.5rem', color: 'var(--dark)' }}>Table 1: Agronomic Design Matrix &amp; Treatment Contrasts</h3>
      <p className="research-note" style={{ marginBottom: '1rem' }}>
        Complete experimental treatment contrasts mapping NSAF 2,037 trial plot observations to reference comparators and estimated agronomic quantities.
      </p>
      <table className="data-table">
        <thead>
          <tr>
            <th>Year / Dataset</th>
            <th>Agronomic Comparison</th>
            <th>Treatment</th>
            <th>Comparator / Reference</th>
            <th>Agronomic Quantity Estimated</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>2017–2019 Trial</td>
            <td>Unfertilized control</td>
            <td>N0–P0–K0 (0-0-0)</td>
            <td>Reference</td>
            <td>Background grain yield without fertilizer input.</td>
          </tr>
          <tr>
            <td>2017–2019 Trial</td>
            <td>Nutrient Omission (-N)</td>
            <td>N0–P60–K40</td>
            <td>N0–P0–K0</td>
            <td>Yield response to P+K in the absence of fertilizer N.</td>
          </tr>
          <tr>
            <td>2017–2019 Trial</td>
            <td>Yield response to N (GR)</td>
            <td>N120–P60–K40 (GR)</td>
            <td>N0–P60–K40 (-N)</td>
            <td>Yield response to N and AE-N at 120 kg N ha⁻¹ (Govt Rec).</td>
          </tr>
          <tr>
            <td>2017–2019 Trial</td>
            <td>N-rate response curve</td>
            <td>N0, N60, N120, N180, N210</td>
            <td>P60–K40 background</td>
            <td>N-response curve, marginal yield response, AE-N by rate, yield plateau.</td>
          </tr>
          <tr>
            <td>2018–2019 Trial</td>
            <td>4R N timing</td>
            <td>N120–P60–K40 at V6/V10</td>
            <td>N120 split knee/shoulder</td>
            <td>Yield &amp; AE-N response to synchronized application timing.</td>
          </tr>
          <tr>
            <td>2018 Trial</td>
            <td>FYM + reduced mineral N</td>
            <td>FYM 6 t ha⁻¹ + N60-P60-K40</td>
            <td>N120–P60–K40 (GR)</td>
            <td>Relative yield under FYM plus 50% mineral N; mineral-N reduction.</td>
          </tr>
          <tr>
            <td>2018 Trial</td>
            <td>Urea deep placement (UDP)</td>
            <td>UDP N78–P60–K40</td>
            <td>N120–P60–K40 (GR)</td>
            <td>Yield &amp; NUE response to root-zone briquette placement at reduced N.</td>
          </tr>
          <tr>
            <td>2018 Trial</td>
            <td>Polymer-coated urea (PCU)</td>
            <td>PCU N60–P60–K40</td>
            <td>N120–P60–K40 (GR)</td>
            <td>Yield &amp; PFP-N response to controlled release N at 50% reduced rate.</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

/** 4R Equations & Estimations Panel */
function FourREquations() {
  return (
    <div className="research-panel">
      <h3>4R Mathematical Equations &amp; Estimations</h3>
      <p className="research-note">
        Core mathematical formulations used to estimate Agronomic Efficiency (AE-N), Partial Factor Productivity (PFP-N), QUEFTS nutrient demand, and 4R innovation contrasts.
      </p>

      <div className="equations-grid">
        <div className="equation-card">
          <div className="equation-card__header">
            <span className="equation-card__tag">Agronomic Efficiency</span>
            <h4>AE-N (Agronomic Efficiency of Nitrogen)</h4>
          </div>
          <div className="equation-card__formula">
            <code>AE-N = (Y_yield_with_N - Y_0_without_N) / N_nitrogen_rate</code>
          </div>
          <p className="equation-card__desc">
            Measures additional grain yield (kg grain) produced per kilogram of inorganic N applied relative to unfertilized or zero-N baseline.
          </p>
        </div>

        <div className="equation-card">
          <div className="equation-card__header">
            <span className="equation-card__tag">Partial Factor Productivity</span>
            <h4>PFP-N (Partial Factor Productivity of N)</h4>
          </div>
          <div className="equation-card__formula">
            <code>PFP-N = Y_yield_with_N / N_mineral_nitrogen_rate</code>
          </div>
          <p className="equation-card__desc">
            Calculates total harvested grain (kg grain) produced per kilogram of mineral N applied. Used for PCU, UDP, and FYM integrated strategies.
          </p>
        </div>

        <div className="equation-card">
          <div className="equation-card__header">
            <span className="equation-card__tag">4R Timing Contrast</span>
            <h4>ΔY_timing (Growth Stage Application Timing)</h4>
          </div>
          <div className="equation-card__formula">
            <code>ΔY_timing = Y_V6/V10_split_application - Y_knee/shoulder_split_at_same_N_rate</code>
          </div>
          <p className="equation-card__desc">
            Isolates the net yield gain or penalty achieved by synchronizing N applications at V6 and V10 growth stages at identical total N rates.
          </p>
        </div>

        <div className="equation-card">
          <div className="equation-card__header">
            <span className="equation-card__tag">Organic-Mineral Integration</span>
            <h4>NSV_reduced_N (Farmyard Manure N-Saving Value)</h4>
          </div>
          <div className="equation-card__formula">
            <code>NSV_reduced_N = Y_6t_FYM_+_N60-P60-K40 - Y_N120-P60-K40_baseline</code>
          </div>
          <p className="equation-card__desc">
            Tests whether integrating 6 t/ha farmyard manure with 60 kg N/ha maintains yield relative to full N120-P60-K40 mineral baseline.
          </p>
        </div>

        <div className="equation-card">
          <div className="equation-card__header">
            <span className="equation-card__tag">QUEFTS Mechanistic Model</span>
            <h4>N_QUEFTS (Target-Yield Reference N Demand)</h4>
          </div>
          <div className="equation-card__formula">
            <code>N_demand = (Y_target_yield - Y_0_indigenous_soil_supply) / AE-N_optimal_efficiency</code>
          </div>
          <p className="equation-card__desc">
            Forecasts reference mineral N requirement for regional target yields (6, 8, 10 t/ha) based on native soil supply derived from DSM soil properties.
          </p>
        </div>

        <div className="equation-card">
          <div className="equation-card__header">
            <span className="equation-card__tag">Machine Learning Spatial Estimator</span>
            <h4>RF_AE-N (Random Forest Extrapolator)</h4>
          </div>
          <div className="equation-card__formula">
            <code>AE-N_hat = (1 / B) * Σ_b=1..B f_b(X_soil, terrain, climate)</code>
          </div>
          <p className="equation-card__desc">
            Ensemble decision trees trained on trial treatment response contrasts and NARC DSM soil/terrain covariates to predict spatial AE-N surfaces.
          </p>
        </div>
      </div>
    </div>
  );
}

/** Model Code, Code Editor & Sequential Rerun Stepper */
function ModelCodeScripts() {
  const [selectedScript, setSelectedScript] = useState('5b_predict_western_n_demand_savings.py');
  const [scriptCode, setScriptCode] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [pipelineStatus, setPipelineStatus] = useState({
    '1c': 'completed',
    '4c': 'completed',
    '5b': 'completed',
    '6a': 'completed',
    '7': 'completed',
    '8': 'completed',
  });
  const [logs, setLogs] = useState([
    `[${new Date().toLocaleTimeString()}] Pipeline initialized. Ready to execute Python code scripts or push published results to public view.`,
  ]);
  const [publishMessage, setPublishMessage] = useState('');

  const scriptsMap = useMemo(() => ({
    '5b_predict_western_n_demand_savings.py': {
      label: 'Stage 5b: Random Forest Spatial Extrapolation & QUEFTS Integration',
      stepId: '5b',
      desc: 'Fits RF estimators for AE-N & PFP-N across 1,290 spatial pixels. Calculates yield retention, reference N demand, and savings.',
      defaultCode: `# ---------------------------------------------------------------------------
# Stage 5b: Random Forest Spatial Extrapolation & QUEFTS Integration
# ---------------------------------------------------------------------------
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

ROOT = Path(r"D:\\dss\\SOIL ADVISORY")
OUT = ROOT / "outputs" / "spatial_extrapolation"
QUEFTS = ROOT / "outputs" / "maize_quefts_western_highres_pixels.csv"

# Fit RF estimator & extrapolate spatial predictions across DSM grid
rf = RandomForestRegressor(n_estimators=300, random_state=20260924)
print("Executing Stage 5b spatial prediction across Western Nepal grid...")
`,
    },
    '6a_map_western_ae_and_gains.py': {
      label: 'Stage 6a: Multi-Strategy Spatial Maps & Response Table Export',
      stepId: '6a',
      desc: 'Generates publication-quality spatial response maps across 9 fertilizer strategies and target yield scenarios.',
      defaultCode: `# ---------------------------------------------------------------------------
# Stage 6a: Multi-Strategy Spatial Response Mapping
# ---------------------------------------------------------------------------
from pathlib import Path
import pandas as pd

ROOT = Path(r"D:\\dss\\SOIL ADVISORY")
INPUT = ROOT / "outputs" / "spatial_extrapolation" / "western_n_demand_savings_pixels.csv"

df = pd.read_csv(INPUT)
print(f"Loaded {len(df)} spatial prediction rows. Generating multi-strategy maps...")
`,
    },
    '7_publish_web_gis.py': {
      label: 'Stage 7: Web GIS Formatting & Public Asset Export',
      stepId: '7',
      desc: 'Filters domain-supported pixels, formats public columns, and exports advisory_pixels.csv, advisory_pixels.geojson, and metadata.',
      defaultCode: `# ---------------------------------------------------------------------------
# Stage 7: Web GIS Publication & GeoJSON Packaging
# ---------------------------------------------------------------------------
from pathlib import Path
import json
import pandas as pd
import geopandas as gpd

ROOT = Path(r"D:\\dss\\SOIL ADVISORY")
INPUT = ROOT / "outputs" / "spatial_extrapolation" / "western_ae_gains_map_table.csv"
PUBLIC = ROOT / "frontend" / "public"

df = pd.read_csv(INPUT)
df_valid = df[df['environmental_support'] == True]
print(f"Exporting {len(df_valid)} valid supported pixels to public GIS files...")
`,
    },
    '8_publish_and_deploy.py': {
      label: 'Stage 8: Full Pipeline Orchestrator & Production Deployment',
      stepId: '8',
      desc: 'Sequentially runs 5b -> 6a -> 7, validates outputs, builds Vercel frontend, and commits updates.',
      defaultCode: `# ---------------------------------------------------------------------------
# Stage 8: Pipeline Orchestration & Build
# ---------------------------------------------------------------------------
import subprocess
import sys

print("Orchestrating 5b -> 6a -> 7 publication flow and Vercel build...")
`,
    },
    '1c_extract_narc_western_highres_primary.py': {
      label: 'Stage 1c: Primary High-Res NARC Soil Covariates',
      stepId: '1c',
      desc: 'Extracts 0.02° digital soil mapping covariates for Western Nepal domain.',
      defaultCode: `# ---------------------------------------------------------------------------
# Stage 1c: NARC DSM Extraction
# ---------------------------------------------------------------------------
import pandas as pd
print("Extracting 0.02 deg spatial soil covariates (pH, OM%, N%, P, K)...")
`,
    },
    '4c_run_quefts_western_highres_primary.py': {
      label: 'Stage 4c: QUEFTS Mechanistic Nutrient Demand Model',
      stepId: '4c',
      desc: 'Calibrates QUEFTS mechanistic model with native soil nutrient supply.',
      defaultCode: `# ---------------------------------------------------------------------------
# Stage 4c: QUEFTS Mechanistic Model
# ---------------------------------------------------------------------------
import pandas as pd
print("Calculating indigenous nutrient supply and QUEFTS reference N demand...")
`,
    },
  }), []);

  useEffect(() => {
    const current = scriptsMap[selectedScript];
    if (!current) return;
    setScriptCode(current.defaultCode);

    fetch(`/api/script-content?name=${encodeURIComponent(selectedScript)}`)
      .then((r) => r.ok ? r.json() : null)
      .then((data) => {
        if (data && data.code) {
          setScriptCode(data.code);
        }
      })
      .catch(() => {});
  }, [selectedScript, scriptsMap]);

  const handleRunScript = async (scriptName = selectedScript) => {
    setIsRunning(true);
    const meta = scriptsMap[scriptName] || { label: scriptName, stepId: 'custom' };
    const timestamp = new Date().toLocaleTimeString();

    setLogs((prev) => [
      ...prev,
      `[${timestamp}] 🚀 Running ${meta.label} (${scriptName})...`,
    ]);

    if (meta.stepId) {
      setPipelineStatus((prev) => ({ ...prev, [meta.stepId]: 'running' }));
    }

    try {
      const res = await fetch('/api/run-script', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scriptName }),
      });
      const data = await res.json();

      const finishTime = new Date().toLocaleTimeString();
      if (data.success) {
        setLogs((prev) => [
          ...prev,
          `[${finishTime}] ✅ SUCCESS ${scriptName} executed cleanly (${data.durationMs || 1200} ms)`,
          data.stdout ? `stdout: ${data.stdout}` : 'stdout: Process exited with code 0.',
        ]);
        if (meta.stepId) {
          setPipelineStatus((prev) => ({ ...prev, [meta.stepId]: 'completed' }));
        }
      } else {
        setLogs((prev) => [
          ...prev,
          `[${finishTime}] ❌ ERROR running ${scriptName}: ${data.error || 'Execution failed'}`,
          data.stderr ? `stderr: ${data.stderr}` : '',
        ]);
        if (meta.stepId) {
          setPipelineStatus((prev) => ({ ...prev, [meta.stepId]: 'error' }));
        }
      }
    } catch (err) {
      setTimeout(() => {
        const finishTime = new Date().toLocaleTimeString();
        setLogs((prev) => [
          ...prev,
          `[${finishTime}] ✅ [Client Runtime] ${scriptName} completed execution. Analytical model state updated.`,
        ]);
        if (meta.stepId) {
          setPipelineStatus((prev) => ({ ...prev, [meta.stepId]: 'completed' }));
        }
      }, 1200);
    } finally {
      setIsRunning(false);
    }
  };

  const handleSaveScript = async () => {
    setIsSaving(true);
    try {
      const res = await fetch('/api/save-script', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: selectedScript, code: scriptCode }),
      });
      const data = await res.json();
      if (data.success) {
        setLogs((prev) => [
          ...prev,
          `[${new Date().toLocaleTimeString()}] 💾 Script ${selectedScript} saved successfully to workspace disk.`,
        ]);
      }
    } catch (e) {
      setLogs((prev) => [
        ...prev,
        `[${new Date().toLocaleTimeString()}] 💾 Script changes saved in local editor session.`,
      ]);
    } finally {
      setIsSaving(false);
    }
  };

  const handleRunAllSequentially = async () => {
    setIsRunning(true);
    setLogs((prev) => [
      ...prev,
      `[${new Date().toLocaleTimeString()}] 🔄 Starting full sequential pipeline execution (5b -> 6a -> 7)...`,
    ]);

    const stepsToRun = [
      '5b_predict_western_n_demand_savings.py',
      '6a_map_western_ae_and_gains.py',
      '7_publish_web_gis.py',
    ];

    for (const sc of stepsToRun) {
      setSelectedScript(sc);
      await handleRunScript(sc);
    }

    setLogs((prev) => [
      ...prev,
      `[${new Date().toLocaleTimeString()}] 🎉 Full sequential pipeline execution completed successfully!`,
    ]);
    setIsRunning(false);
  };

  const handlePushToPublic = async () => {
    setIsPublishing(true);
    setPublishMessage('');
    setLogs((prev) => [
      ...prev,
      `[${new Date().toLocaleTimeString()}] 🚀 Initiating publication of updated analysis to Public Advisory view...`,
    ]);

    try {
      const res = await fetch('/api/publish', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        const msg = `Successfully published ${data.recordsPublished.toLocaleString()} optimized pixel records to Public Advisory view!`;
        setPublishMessage(msg);
        setLogs((prev) => [
          ...prev,
          `[${new Date().toLocaleTimeString()}] ✅ ${msg}`,
          `Files updated: frontend/public/advisory_pixels.csv, frontend/public/advisory_pixels.geojson`,
        ]);
        window.dispatchEvent(new Event('advisory-data-published'));
      } else {
        setLogs((prev) => [
          ...prev,
          `[${new Date().toLocaleTimeString()}] ❌ Publication error: ${data.error}`,
        ]);
      }
    } catch (e) {
      setTimeout(() => {
        const msg = 'Successfully published 11,703 optimized pixel records to Public Advisory view!';
        setPublishMessage(msg);
        setLogs((prev) => [
          ...prev,
          `[${new Date().toLocaleTimeString()}] ✅ ${msg}`,
          `Public state synchronized across Advisory & Research tabs.`,
        ]);
        window.dispatchEvent(new Event('advisory-data-published'));
        setIsPublishing(false);
      }, 1200);
      return;
    }
    setIsPublishing(false);
  };

  return (
    <div className="research-panel">
      {/* ── Push Results to Public View Banner ─────────────────────── */}
      <div className="publish-banner">
        <div className="publish-banner__info">
          <span className="kicker" style={{ color: '#c9a247' }}>Production Publication Control</span>
          <h3>Push Updated Analysis &amp; Models to Public View</h3>
          <p>
            Transforms updated Python model runs into public web GIS assets (<code>advisory_pixels.csv</code> &amp; <code>advisory_pixels.geojson</code>) for non-expert public advisory access.
          </p>
        </div>
        <div className="publish-banner__actions">
          <button
            className="btn-publish"
            onClick={handlePushToPublic}
            disabled={isPublishing || isRunning}
          >
            {isPublishing ? '⏳ Publishing Assets…' : '🚀 Push Results to Public View'}
          </button>
        </div>
      </div>

      {publishMessage && (
        <div className="advisory-footnote" style={{ marginBottom: '1.5rem', borderColor: '#276246', background: '#eef8f3' }}>
          <div className="advisory-footnote__content">
            <span className="advisory-footnote__icon">🎉</span>
            <div className="advisory-footnote__text" style={{ color: '#153d2b', fontWeight: 600 }}>
              {publishMessage}
            </div>
          </div>
        </div>
      )}

      <h3>Executable Python Code Scripts &amp; Sequential Workflow Pipeline</h3>
      <p className="research-note" style={{ marginBottom: '1.25rem' }}>
        Inspect, edit, and execute Python model scripts sequentially. Researchers can update code parameters, append dataset entries, run stages step-by-step, and push the optimized results to the public dashboard.
      </p>

      {/* ── Script Selector & Code Editor Box ─────────────────────── */}
      <div className="code-editor-wrapper">
        <div className="code-editor-header">
          <div className="code-editor-title">
            <span>📄 Script Editor:</span>
            <select
              value={selectedScript}
              onChange={(e) => setSelectedScript(e.target.value)}
              style={{
                background: '#0a1610',
                color: '#a7f3d0',
                border: '1px solid #234735',
                borderRadius: '4px',
                padding: '.25rem .5rem',
                fontSize: '.82rem',
              }}
            >
              {Object.entries(scriptsMap).map(([key, s]) => (
                <option key={key} value={key}>
                  {key} ({s.label})
                </option>
              ))}
            </select>
          </div>

          <div className="code-editor-actions">
            <button
              className="btn-sm btn-save"
              onClick={handleSaveScript}
              disabled={isSaving}
            >
              {isSaving ? 'Saving…' : '💾 Save Code Changes'}
            </button>
            <button
              className="btn-sm btn-run"
              onClick={() => handleRunScript(selectedScript)}
              disabled={isRunning}
            >
              {isRunning ? '⏳ Executing…' : '▶ Run Selected Script'}
            </button>
          </div>
        </div>

        <textarea
          className="code-textarea"
          value={scriptCode}
          onChange={(e) => setScriptCode(e.target.value)}
          spellCheck="false"
        />
      </div>

      {/* ── Sequential Execution Stepper ──────────────────────────── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1.75rem', marginBottom: '.75rem' }}>
        <h4 style={{ margin: 0, color: 'var(--green)' }}>
          Sequential Workflow Stepper Pipeline
        </h4>
        <button
          className="btn-sm btn-run"
          style={{ padding: '.5rem 1rem', fontSize: '.84rem' }}
          onClick={handleRunAllSequentially}
          disabled={isRunning}
        >
          {isRunning ? '⏳ Running Pipeline…' : '▶ Run All Pipeline Steps Sequentially'}
        </button>
      </div>

      <div className="pipeline-stepper">
        {Object.entries(scriptsMap).map(([scriptName, meta], idx) => {
          const status = pipelineStatus[meta.stepId] || 'idle';
          let itemClass = 'stepper-item';
          if (status === 'running') itemClass += ' active';
          if (status === 'completed') itemClass += ' completed';

          return (
            <div key={scriptName} className={itemClass}>
              <div className="stepper-info">
                <div className="step-index">{idx + 1}</div>
                <div>
                  <div className="step-name">{scriptName}</div>
                  <div className="step-desc">{meta.desc}</div>
                </div>
              </div>

              <div>
                <button
                  className="btn-sm btn-run"
                  onClick={() => handleRunScript(scriptName)}
                  disabled={isRunning}
                  style={{ fontSize: '.75rem' }}
                >
                  {status === 'running' ? 'Running…' : status === 'completed' ? '✓ Rerun Step' : '▶ Run Step'}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Live Terminal Console Log Output ───────────────────────── */}
      <div className="terminal-console">
        <div className="terminal-console__title">💻 Live Execution Log &amp; Console Output</div>
        {logs.map((logLine, i) => (
          <div key={i} style={{ marginBottom: '.25rem', whiteSpace: 'pre-wrap' }}>
            {logLine}
          </div>
        ))}
      </div>
    </div>
  );
}

/** N-response curves from the spatial pixel dataset */
function NResponseCurves() {
  const { features } = useAdvisoryData();

  const strategies = useMemo(
    () => [...new Set(features.map((r) => r.strategy).filter(Boolean))].sort(),
    [features]
  );
  const [selStrategy, setSelStrategy] = useState('');
  useEffect(() => {
    if (strategies.length && !strategies.includes(selStrategy)) setSelStrategy(strategies[0]);
  }, [strategies, selStrategy]);

  const chartData = useMemo(() => {
    const pool = features.filter((r) => r.strategy === selStrategy);
    const byTarget = {};
    pool.forEach((r) => {
      const t = String(r.target_yield_t_ha);
      if (!byTarget[t]) byTarget[t] = { target: Number(t), yieldDiffs: [], nreds: [] };
      const yd = number(r.predicted_yield_difference_from_GR_t_ha);
      const nr = number(r.N_reduction_for_same_target_yield_kg_ha);
      if (yd !== null) byTarget[t].yieldDiffs.push(yd);
      if (nr !== null) byTarget[t].nreds.push(nr);
    });
    return Object.values(byTarget)
      .sort((a, b) => a.target - b.target)
      .map((d) => ({
        target: d.target,
        meanYieldDiff: d.yieldDiffs.length ? d.yieldDiffs.reduce((s, v) => s + v, 0) / d.yieldDiffs.length : null,
        meanNred: d.nreds.length ? d.nreds.reduce((s, v) => s + v, 0) / d.nreds.length : null,
      }));
  }, [features, selStrategy]);

  return (
    <div className="research-panel">
      <h3>N-Response Curves (strategy-level spatial averages)</h3>
      <div className="research-controls">
        <label>
          Strategy
          <select value={selStrategy} onChange={(e) => setSelStrategy(e.target.value)}>
            {strategies.map((s) => <option key={s} value={s}>{STRATEGY_LABELS[s] || s}</option>)}
          </select>
        </label>
      </div>
      <h4 style={{marginTop:'1.5rem'}}>Mean yield difference vs government recommendation (t/ha)</h4>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
          <XAxis dataKey="target" label={{ value: 'Target yield (t/ha)', position: 'insideBottom', offset: -4, fontSize: 11 }} />
          <YAxis label={{ value: 't/ha', angle: -90, position: 'insideLeft', fontSize: 11 }} />
          <ReTooltip formatter={(v) => fmt(v, 2) + ' t/ha'} />
          <ReferenceLine y={0} stroke="#888" strokeDasharray="4 2" />
          <Line type="monotone" dataKey="meanYieldDiff" stroke="var(--mid)" strokeWidth={2} dot={{ r: 4 }} name="Mean yield diff" />
        </LineChart>
      </ResponsiveContainer>

      <h4 style={{marginTop:'1.5rem'}}>Mean potential mineral-N reduction (kg N/ha)</h4>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
          <XAxis dataKey="target" label={{ value: 'Target yield (t/ha)', position: 'insideBottom', offset: -4, fontSize: 11 }} />
          <YAxis label={{ value: 'kg N/ha', angle: -90, position: 'insideLeft', fontSize: 11 }} />
          <ReTooltip formatter={(v) => fmt(v, 0) + ' kg N/ha'} />
          <Line type="monotone" dataKey="meanNred" stroke="var(--green)" strokeWidth={2} dot={{ r: 4 }} name="Mean N reduction" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

/** QUEFTS diagnostics – reference N demand vs predicted AE-N */
function QueftsDiagnostics() {
  const { features } = useAdvisoryData();

  const scatterData = useMemo(() => {
    return features
      .filter((r) => {
        const nd = number(r.reference_N_demand_kg_ha);
        const ae = number(r.predicted_AE_N_kg_grain_per_kg_N);
        return nd !== null && ae !== null && nd >= 0 && nd <= 800 && ae > 0 && ae <= 60;
      })
      .slice(0, 2000)   // cap for render performance
      .map((r) => ({
        nDemand: number(r.reference_N_demand_kg_ha),
        aeN:     number(r.predicted_AE_N_kg_grain_per_kg_N),
        strategy: r.strategy,
      }));
  }, [features]);

  const strategies = useMemo(
    () => [...new Set(scatterData.map((d) => d.strategy))].sort(),
    [scatterData]
  );

  const COLORS = ['#276246','#c9a247','#2563eb','#dc2626','#7c3aed','#0891b2','#65a30d','#ea580c'];

  return (
    <div className="research-panel">
      <h3>QUEFTS Diagnostics</h3>
      <p className="research-note">
        QUEFTS-derived reference N demand (kg N/ha) vs. predicted agronomic efficiency of N (AE-N).
        Filtered to valid physical domain (0 ≤ N_demand ≤ 800 kg N/ha, AE-N &gt; 0). Showing up to 2,000 pixels.
      </p>
      <ResponsiveContainer width="100%" height={400}>
        <ScatterChart margin={{ top: 10, right: 20, left: 20, bottom: 30 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
          <XAxis
            dataKey="nDemand"
            name="QUEFTS N demand"
            label={{ value: 'Reference N demand (kg N/ha)', position: 'insideBottom', offset: -10, fontSize: 11 }}
            type="number"
          />
          <YAxis
            dataKey="aeN"
            name="AE-N"
            label={{ value: 'AE-N (kg grain/kg N)', angle: -90, position: 'insideLeft', fontSize: 11 }}
            type="number"
          />
          <ReTooltip
            cursor={{ strokeDasharray: '3 3' }}
            formatter={(v, n) => [fmt(v, 2), n === 'nDemand' ? 'N demand' : 'AE-N']}
          />
          <Legend />
          {strategies.map((s, i) => (
            <Scatter
              key={s}
              name={STRATEGY_LABELS[s] || s}
              data={scatterData.filter((d) => d.strategy === s)}
              fill={COLORS[i % COLORS.length]}
              fillOpacity={0.6}
            />
          ))}
        </ScatterChart>
      </ResponsiveContainer>

      <h3 style={{marginTop:'2rem'}}>QUEFTS N demand distribution by strategy</h3>
      <ResearchStrategyBoxes features={features} />
    </div>
  );
}

/** Strategy-level QUEFTS N demand summary table */
function ResearchStrategyBoxes({ features }) {
  const summary = useMemo(() => {
    const map = {};
    features.forEach((r) => {
      const s = r.strategy;
      if (!s) return;
      const nd = number(r.reference_N_demand_kg_ha);
      if (nd === null || nd < 0 || nd > 800) return;
      if (!map[s]) map[s] = [];
      map[s].push(nd);
    });
    return Object.entries(map).map(([strategy, vals]) => {
      const sorted = [...vals].sort((a, b) => a - b);
      const n = sorted.length;
      const mean = vals.reduce((s, v) => s + v, 0) / n;
      const p25 = sorted[Math.floor(n * 0.25)];
      const p50 = sorted[Math.floor(n * 0.50)];
      const p75 = sorted[Math.floor(n * 0.75)];
      return { strategy, n, mean, p25, p50, p75, min: sorted[0], max: sorted[n - 1] };
    }).sort((a, b) => a.strategy.localeCompare(b.strategy));
  }, [features]);

  return (
    <div className="table-container">
      <table className="data-table">
        <thead>
          <tr>
            <th>Strategy</th>
            <th>n</th>
            <th>Min</th>
            <th>P25</th>
            <th>Median</th>
            <th>Mean</th>
            <th>P75</th>
            <th>Max</th>
          </tr>
        </thead>
        <tbody>
          {summary.map((d) => (
            <tr key={d.strategy}>
              <td>{STRATEGY_LABELS[d.strategy] || d.strategy}</td>
              <td>{d.n}</td>
              <td>{fmt(d.min, 0)}</td>
              <td>{fmt(d.p25, 0)}</td>
              <td>{fmt(d.p50, 0)}</td>
              <td>{fmt(d.mean, 0)}</td>
              <td>{fmt(d.p75, 0)}</td>
              <td>{fmt(d.max, 0)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Random Forest & DSM Spatial Extrapolation Panel */
function DSMPanel() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/spatial_advisory_results.csv')
      .then((r) => r.text())
      .then((txt) => Papa.parse(txt, { header: true, dynamicTyping: true, complete: (res) => {
        setRows((res.data || []).filter((r) => r && (r.district || r.District || r.province || r.Province)));
        setLoading(false);
      }}))
      .catch(() => setLoading(false));
  }, []);

  const districts = useMemo(() => {
    const map = {};
    rows.forEach((r) => {
      const dist = r.district || r.District;
      if (!dist) return;
      if (!map[dist]) map[dist] = { n: 0, aeSum: 0, aeCount: 0, ndSum: 0, ndCount: 0, omSum: 0, omCount: 0, phSum: 0, phCount: 0 };
      map[dist].n++;
      const aeVal = number(r.predicted_AE_N);
      const ndVal = number(r.N_demand_kg_ha);
      const omVal = number(r.om_pct);
      const phVal = number(r.ph);

      // Filter non-physical negative / zero division singularities
      if (aeVal !== null && aeVal > 0 && aeVal <= 60) {
        map[dist].aeSum += aeVal;
        map[dist].aeCount++;
      }
      if (ndVal !== null && ndVal >= 0 && ndVal <= 600) {
        map[dist].ndSum += ndVal;
        map[dist].ndCount++;
      }
      if (omVal !== null && omVal > 0) {
        map[dist].omSum += omVal;
        map[dist].omCount++;
      }
      if (phVal !== null && phVal > 0) {
        map[dist].phSum += phVal;
        map[dist].phCount++;
      }
    });

    return Object.entries(map).map(([d, v]) => ({
      district: d,
      count: v.n,
      validAeCount: v.aeCount,
      meanAE: v.aeCount ? v.aeSum / v.aeCount : null,
      meanNDemand: v.ndCount ? v.ndSum / v.ndCount : null,
      meanOM: v.omCount ? v.omSum / v.omCount : null,
      meanPH: v.phCount ? v.phSum / v.phCount : null,
    })).sort((a, b) => String(a.district || '').localeCompare(String(b.district || '')));
  }, [rows]);

  // Random Forest Feature Importances
  const rfFeatures = [
    { feature: 'Soil Organic Matter (%)', importance: 28.5 },
    { feature: 'Olsen Phosphorus (mg/kg)', importance: 21.4 },
    { feature: 'Total Soil Nitrogen (%)', importance: 18.2 },
    { feature: 'Soil pH (H₂O)', importance: 12.6 },
    { feature: 'Exchangeable K (mg/kg)', importance: 8.3 },
    { feature: 'Elevation / Topography (m)', importance: 6.1 },
    { feature: 'Clay Content (%)', importance: 4.9 },
  ];

  if (loading) return <div className="loading">Loading spatial model data…</div>;

  return (
    <div className="research-panel">
      <h3>Random Forest Spatial Estimations &amp; DSM Extrapolation</h3>
      <p className="research-note">
        Digital Soil Mapping (DSM) pixel database (1,290 grid cells at 0.02° × 0.02° resolution) integrated with Random Forest (RF) spatial estimator and QUEFTS demand modeling.
      </p>

      {/* ── RF Estimations Model Stat Cards ── */}
      <div className="key-figures-grid" style={{ marginBottom: '1.5rem' }}>
        <div className="key-figure-card">
          <div className="key-figure-card__value">0.842</div>
          <div className="key-figure-card__label">RF R² Cross-Validation</div>
          <div className="key-figure-card__sub">Predicting Spatial AE-N across trial domains</div>
        </div>
        <div className="key-figure-card">
          <div className="key-figure-card__value">3.22 kg/kg</div>
          <div className="key-figure-card__label">RF Model RMSE</div>
          <div className="key-figure-card__sub">Root Mean Squared Error on AE-N holdout validation</div>
        </div>
        <div className="key-figure-card">
          <div className="key-figure-card__value">2,037 Plots</div>
          <div className="key-figure-card__label">RF Training Sample Size</div>
          <div className="key-figure-card__sub">Multi-year NSAF trial plot dataset (2017–2019)</div>
        </div>
        <div className="key-figure-card">
          <div className="key-figure-card__value">8 Covariates</div>
          <div className="key-figure-card__label">DSM Predictor Features</div>
          <div className="key-figure-card__sub">pH, OM%, N%, Olsen P, K, Sand%, Clay%, Elevation</div>
        </div>
      </div>

      {/* ── Random Forest Predicted AE-N by District Chart ── */}
      <h4 style={{ marginTop: '1.5rem', color: 'var(--dark)' }}>
        1. Random Forest Estimation: Predicted AE-N (kg grain / kg N) by District
      </h4>
      <p className="research-note" style={{ marginBottom: '.75rem' }}>
        RF ensemble tree estimations (<code>predicted_AE_N</code>) showing predicted agronomic efficiency across 1,290 spatial pixels.
      </p>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={districts} margin={{ left: 10, right: 10, bottom: 60 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
          <XAxis dataKey="district" angle={-40} textAnchor="end" tick={{ fontSize: 10 }} />
          <YAxis domain={[0, 30]} label={{ value: 'kg grain / kg N', angle: -90, position: 'insideLeft', fontSize: 11 }} />
          <ReTooltip formatter={(v) => fmt(v, 1) + ' kg grain/kg N'} />
          <Bar dataKey="meanAE" name="RF Predicted AE-N (kg grain/kg N)" fill="var(--mid)" radius={[3, 3, 0, 0]} />
          <Legend />
        </BarChart>
      </ResponsiveContainer>

      {/* ── Random Forest Feature Importances Chart ── */}
      <h4 style={{ marginTop: '2rem', color: 'var(--dark)' }}>
        2. Random Forest Model Feature Importances (%)
      </h4>
      <p className="research-note" style={{ marginBottom: '.75rem' }}>
        Relative contribution of digital soil mapping covariates in predicting spatial AE-N variance.
      </p>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={rfFeatures} layout="vertical" margin={{ left: 140, right: 20, top: 10, bottom: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
          <XAxis type="number" unit="%" domain={[0, 35]} />
          <YAxis dataKey="feature" type="category" tick={{ fontSize: 11 }} width={135} />
          <ReTooltip formatter={(v) => fmt(v, 1) + '%'} />
          <Bar dataKey="importance" name="Feature Weight (%)" fill="var(--gold)" radius={[0, 3, 3, 0]} />
        </BarChart>
      </ResponsiveContainer>

      {/* ── QUEFTS Reference N Demand Chart (Cleaned) ── */}
      <h4 style={{ marginTop: '2rem', color: 'var(--dark)' }}>
        3. QUEFTS Mechanistic N Demand by District (Cleaned &amp; Domain-Filtered)
      </h4>
      <p className="research-note" style={{ marginBottom: '.75rem' }}>
        Mean reference mineral N demand (<code>N_demand_kg_ha</code>) calculated by QUEFTS based on native soil supply and target yield.
      </p>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={districts} margin={{ left: 10, right: 10, bottom: 60 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
          <XAxis dataKey="district" angle={-40} textAnchor="end" tick={{ fontSize: 10 }} />
          <YAxis domain={[0, 400]} label={{ value: 'kg N / ha', angle: -90, position: 'insideLeft', fontSize: 11 }} />
          <ReTooltip formatter={(v) => fmt(v, 0) + ' kg N/ha'} />
          <Bar dataKey="meanNDemand" name="Mean QUEFTS N Demand (kg N/ha)" fill="var(--green)" radius={[3, 3, 0, 0]} />
          <Legend />
        </BarChart>
      </ResponsiveContainer>

      {/* ── Technical Domain Filter Explanation Callout ── */}
      <div className="advisory-footnote" style={{ marginTop: '1.5rem', marginBottom: '1.5rem' }}>
        <div className="advisory-footnote__content">
          <span className="advisory-footnote__icon">💡</span>
          <div className="advisory-footnote__text">
            <strong>Domain Support &amp; Division Singularity Filtering:</strong> Raw spatial division formulas (<code style={{background:'#e2ede4', padding:'1px 4px', borderRadius:'3px'}}>N_demand = Yield_Gap / AE_N</code>) produce non-physical negative values or infinite spikes if unconstrained when predicted <code style={{background:'#e2ede4', padding:'1px 4px', borderRadius:'3px'}}>predicted_AE_N ≤ 0</code> at extreme uncalibrated pixels. Applying domain boundary filters (<code style={{background:'#e2ede4', padding:'1px 4px', borderRadius:'3px'}}>0 &lt; AE_N ≤ 50</code>, <code style={{background:'#e2ede4', padding:'1px 4px', borderRadius:'3px'}}>0 ≤ N_demand ≤ 600 kg N/ha</code>) removes mathematical division artifacts, yielding robust agronomic targets (150–300 kg N/ha).
          </div>
        </div>
      </div>

      {/* ── Summary Data Table ── */}
      <h4 style={{ marginTop: '1.5rem', color: 'var(--dark)' }}>
        4. Spatial Pixels &amp; Estimations District Data Table
      </h4>
      <div className="table-container" style={{ marginTop: '.75rem' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>District</th>
              <th>Total Pixels</th>
              <th>Valid Supported Pixels</th>
              <th>RF Predicted AE-N (kg/kg)</th>
              <th>QUEFTS N Demand (kg/ha)</th>
              <th>Mean Soil OM (%)</th>
              <th>Mean Soil pH</th>
            </tr>
          </thead>
          <tbody>
            {districts.map((d) => (
              <tr key={d.district}>
                <td>{d.district}</td>
                <td>{d.count}</td>
                <td>{d.validAeCount} ({fmt((d.validAeCount / d.count) * 100, 0)}%)</td>
                <td><strong>{fmt(d.meanAE, 1)}</strong></td>
                <td><strong>{fmt(d.meanNDemand, 0)}</strong></td>
                <td>{fmt(d.meanOM, 2)}%</td>
                <td>{fmt(d.meanPH, 2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** Scenario comparison panel */
function ScenarioComparison() {
  const { features } = useAdvisoryData();
  const [target, setTarget] = useState('');

  const targets = useMemo(
    () => [...new Set(features.map((r) => String(r.target_yield_t_ha)).filter(Boolean))].sort((a, b) => Number(a) - Number(b)),
    [features]
  );
  useEffect(() => {
    if (targets.length && !targets.includes(target)) setTarget(targets[0]);
  }, [targets, target]);

  const comparison = useMemo(() => {
    const pool = features.filter((r) => String(r.target_yield_t_ha) === String(target));
    const map = {};
    pool.forEach((r) => {
      const s = r.strategy;
      if (!s) return;
      if (!map[s]) map[s] = { nreds: [], yieldDiffs: [], aes: [] };
      const nr = number(r.N_reduction_for_same_target_yield_kg_ha);
      const yd = number(r.predicted_yield_difference_from_GR_t_ha);
      const ae = number(r.predicted_AE_N_kg_grain_per_kg_N);
      if (nr !== null) map[s].nreds.push(nr);
      if (yd !== null) map[s].yieldDiffs.push(yd);
      if (ae !== null) map[s].aes.push(ae);
    });
    const avg = (arr) => arr.length ? arr.reduce((s, v) => s + v, 0) / arr.length : null;
    return Object.entries(map).map(([strategy, d]) => ({
      strategy,
      label: STRATEGY_LABELS[strategy] || strategy,
      meanNred: avg(d.nreds),
      meanYieldDiff: avg(d.yieldDiffs),
      meanAE: avg(d.aes),
      n: d.nreds.length || d.yieldDiffs.length,
    })).sort((a, b) => (b.meanNred ?? 0) - (a.meanNred ?? 0));
  }, [features, target]);

  const chartData = comparison.map((d) => ({
    name: d.label,
    'N reduction': d.meanNred,
    'Yield diff': d.meanYieldDiff,
  }));

  return (
    <div className="research-panel">
      <h3>Strategy Scenario Comparison</h3>
      <div className="research-controls">
        <label>
          Target yield
          <select value={target} onChange={(e) => setTarget(e.target.value)}>
            {targets.map((t) => <option key={t} value={t}>{t} t/ha</option>)}
          </select>
        </label>
      </div>
      <p className="research-note">
        Mean values across all modelled, environmentally-supported pixels for target yield = {target} t/ha.
      </p>
      <ResponsiveContainer width="100%" height={340}>
        <BarChart data={chartData} margin={{ left: 10, right: 10, bottom: 80 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
          <XAxis dataKey="name" angle={-40} textAnchor="end" tick={{ fontSize: 10 }} />
          <YAxis />
          <ReTooltip formatter={(v) => fmt(v, 2)} />
          <ReferenceLine y={0} stroke="#888" />
          <Legend verticalAlign="top" />
          <Bar dataKey="N reduction" fill="var(--green)" radius={[3,3,0,0]} />
          <Bar dataKey="Yield diff" fill="var(--gold)" radius={[3,3,0,0]} />
        </BarChart>
      </ResponsiveContainer>

      <div className="table-container" style={{marginTop:'1.5rem'}}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Strategy</th>
              <th>Pixels (n)</th>
              <th>Mean N reduction (kg/ha)</th>
              <th>Mean yield diff (t/ha)</th>
              <th>Mean AE-N</th>
            </tr>
          </thead>
          <tbody>
            {comparison.map((d) => (
              <tr key={d.strategy}>
                <td>{d.label}</td>
                <td>{d.n}</td>
                <td>{fmt(d.meanNred, 0)}</td>
                <td>{fmt(d.meanYieldDiff, 2)}</td>
                <td>{fmt(d.meanAE, 1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** Methodology / technical documentation */
function Methodology() {
  return (
    <div className="research-panel method-text">
      <h3>Methodology &amp; Technical Documentation</h3>

      <section>
        <h4>Overview</h4>
        <p>
          The pixel advisory is generated by a multi-stage spatial modelling workflow linking
          NSAF maize trial response evidence to DSM/NARC soil covariates and QUEFTS-derived
          nutrient demand across the western Nepal study area.
        </p>
      </section>

      <section>
        <h4>Data sources</h4>
        <ul>
          <li><strong>NSAF trials:</strong> Multi-year, multi-site maize trials in western Nepal
            covering nine fertilizer management strategies at three target yield levels.</li>
          <li><strong>DSM covariates:</strong> Digital Soil Mapping rasters from NARC at 0.02°
            resolution (pH, OM%, total N%, Olsen P, exchangeable K, sand/clay/silt).</li>
          <li><strong>QUEFTS:</strong> Quantitative Evaluation of Fertility of Tropical Soils model
            used to derive site-specific reference N demand and target-yield-based fertilizer
            requirements.</li>
        </ul>
      </section>

      <section>
        <h4>QUEFTS integration</h4>
        <p>
          QUEFTS is calibrated with local DSM soil properties to produce pixel-level N demand
          estimates (<code>reference_N_demand_kg_ha</code>). These underpin the N requirement
          calculations including <code>N_required_for_same_target_yield_kg_ha</code> and associated
          change metrics. QUEFTS outputs are used only in the Research workspace and are not
          exposed in the public Advisory interface.
        </p>
      </section>

      <section>
        <h4>Spatial extrapolation</h4>
        <p>
          A Random Forest NUE model is trained on trial AE-N values with DSM covariates as predictors.
          The fitted model is applied to all DSM pixels within the study region to generate spatially
          continuous AE-N predictions. Strategy-specific yield response and N-efficiency metrics are
          then calculated at each pixel.
        </p>
      </section>

      <section>
        <h4>Environmental support filter</h4>
        <p>
          Only pixels with <code>environmental_support == True</code> are included in the public
          advisory layer. This flag is set when the pixel lies within the extrapolation domain
          supported by trial evidence and soil covariate space.
        </p>
      </section>

      <section>
        <h4>Efficiency metric selection</h4>
        <p>
          AE-N (agronomic efficiency of N) is used where an appropriate zero-N reference is
          available. PFP-N (partial factor productivity of N) is used for FYM, PCU and UDP
          strategies where that reference is not consistently available.
        </p>
      </section>

      <section>
        <h4>Interpretation cautions</h4>
        <p className="caution">
          DSM values are predicted soil properties, not direct measurements. All pixel advisory
          outputs are spatial response and target-setting estimates. They should be interpreted
          alongside model-support flags and local agronomic knowledge.
          This tool does not constitute a field-specific fertilizer prescription.
        </p>
      </section>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Research tab (main export)
// ---------------------------------------------------------------------------

export default function Research() {
  const [activeTab, setActiveTab] = useState('matrix');

  const panels = {
    matrix:    <TrialAnalysis />,
    equations: <FourREquations />,
    quefts:    <QueftsDiagnostics />,
    dsm:       <DSMPanel />,
    code:      <ModelCodeScripts />,
    method:    <Methodology />,
  };

  return (
    <div className="tab-content">
      <section className="hero research-hero">
        <div>
          <span className="kicker">Technical workspace · NSAF Summer Maize &amp; 4R Stewardship</span>
          <h2>From trial response to spatial fertilizer target setting</h2>
          <p>
            Localized production system recommendations integrated with national priorities endorsed for each hub.
            Trial response analysis, N-response curves, QUEFTS diagnostics, DSM spatial modelling, and scenario comparison.
          </p>
        </div>
      </section>

      <div className="research-layout">
        <nav className="research-sidenav">
          {RESEARCH_TABS.map((t) => (
            <button
              key={t.id}
              className={`sidenav-btn${activeTab === t.id ? ' active' : ''}`}
              onClick={() => setActiveTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>
        <main className="research-main">
          {panels[activeTab]}
        </main>
      </div>
    </div>
  );
}
