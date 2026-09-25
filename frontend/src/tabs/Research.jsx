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
  { id: 'trial',    label: '1. Baseline & Trial Evidence' },
  { id: 'nresponse',label: '2. N-Response & NUE' },
  { id: 'quefts',   label: '3. QUEFTS Demand' },
  { id: 'dsm',      label: '4. DSM Spatial Extrapolation' },
  { id: 'scenario', label: '5. Fertilizer Reduction Scenarios' },
  { id: 'method',   label: '6. Methodology & Documentation' },
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
      .filter((r) => number(r.reference_N_demand_kg_ha) !== null && number(r.predicted_AE_N_kg_grain_per_kg_N) !== null)
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
        Showing up to 2,000 pixels. Field: <code>reference_N_demand_kg_ha</code> (QUEFTS output).
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
      if (nd === null) return;
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

/** DSM / Spatial modelling panel */
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
      if (!map[dist]) map[dist] = { n: 0, aeSum: 0, ndSum: 0 };
      map[dist].n++;
      const aeVal = number(r.predicted_AE_N);
      const ndVal = number(r.N_demand_kg_ha);
      if (aeVal !== null) map[dist].aeSum += aeVal;
      if (ndVal !== null) map[dist].ndSum += ndVal;
    });
    return Object.entries(map).map(([d, v]) => ({
      district: d,
      count: v.n,
      meanAE: v.n ? v.aeSum / v.n : null,
      meanNDemand: v.n ? v.ndSum / v.n : null,
    })).sort((a, b) => String(a.district || '').localeCompare(String(b.district || '')));
  }, [rows]);

  if (loading) return <div className="loading">Loading spatial model data…</div>;

  return (
    <div className="research-panel">
      <h3>DSM / Spatial Modelling — District Summary</h3>
      <p className="research-note">
        Derived from spatial_advisory_results.csv ({rows.length.toLocaleString()} spatial pixels).
        DSM source types: {[...new Set(rows.map((r) => r.dsm_source).filter(Boolean))].join(', ')}.
      </p>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={districts} margin={{ left: 10, right: 10, bottom: 60 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
          <XAxis dataKey="district" angle={-40} textAnchor="end" tick={{ fontSize: 10 }} />
          <YAxis label={{ value: 'kg N/ha', angle: -90, position: 'insideLeft', fontSize: 11 }} />
          <ReTooltip formatter={(v) => fmt(v, 0) + ' kg N/ha'} />
          <Bar dataKey="meanNDemand" name="Mean N demand (QUEFTS)" fill="var(--green)" radius={[3,3,0,0]} />
          <Legend />
        </BarChart>
      </ResponsiveContainer>

      <div className="table-container" style={{marginTop:'1.5rem'}}>
        <table className="data-table">
          <thead>
            <tr>
              <th>District</th>
              <th>Pixels</th>
              <th>Mean AE-N</th>
              <th>Mean N demand (QUEFTS)</th>
            </tr>
          </thead>
          <tbody>
            {districts.map((d) => (
              <tr key={d.district}>
                <td>{d.district}</td>
                <td>{d.count}</td>
                <td>{fmt(d.meanAE, 1)}</td>
                <td>{fmt(d.meanNDemand, 0)}</td>
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
  const [activeTab, setActiveTab] = useState('trial');

  const panels = {
    trial:     <TrialAnalysis />,
    nresponse: <NResponseCurves />,
    quefts:    <QueftsDiagnostics />,
    dsm:       <DSMPanel />,
    scenario:  <ScenarioComparison />,
    method:    <Methodology />,
  };

  return (
    <div className="tab-content">
      <section className="hero research-hero">
        <div>
          <span className="kicker">Technical workspace · NSAF &amp; 4R Stewardship</span>
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
