import "./styles.css";

const sections = [
  {
    kicker: "Baseline",
    title: "Unfertilized production",
    text: "The 0-0-0 treatment provides the observed yield floor under no mineral N, P or K. Site-to-site and year-to-year differences establish that farmers begin from different production conditions before fertilizer is applied."
  },
  {
    kicker: "Diagnosis",
    title: "Nutrient omission",
    text: "Nutrient omission contrasts identify the relative importance of N, P and K. N was the most consistent major nutrient constraint, P response was generally more moderate, and K response showed stronger local variability."
  },
  {
    kicker: "Efficiency",
    title: "N rate and timing",
    text: "AE-N is calculated against 0PK for N-rate and timing comparisons. The evidence is used to compare grain return per unit N with yield achieved under the government recommendation."
  },
  {
    kicker: "Alternatives",
    title: "FYM, PCU and UDP",
    text: "Partial factor productivity of mineral N is used for FYM, PCU and UDP where a consistent 0PK comparator is not available. Yield differences from GR remain the production reference."
  }
];

const metrics = [
  ["AE-N", "kg grain kg⁻¹ N", "Agronomic efficiency relative to 0PK"],
  ["PFP-N", "kg grain kg⁻¹ mineral N", "For FYM, PCU and UDP strategies"],
  ["Yield difference", "t ha⁻¹", "Difference from government recommendation"],
  ["N requirement", "kg N ha⁻¹", "Estimated N required for the same target yield"]
];

document.querySelector("#app").innerHTML = `
<header class="site-header">
  <div class="shell header-inner">
    <div class="brand">
      <div class="brand-mark">SA</div>
      <div>
        <div class="brand-title">Soil Advisory</div>
        <div class="brand-sub">Nepal maize nutrient management</div>
      </div>
    </div>
    <nav>
      <a href="#evidence">Evidence</a>
      <a href="#spatial">Spatial analysis</a>
      <a href="#methods">Methods</a>
      <a href="#references">References</a>
    </nav>
  </div>
</header>

<main>
  <section class="hero">
    <div class="shell hero-grid">
      <div>
        <div class="eyebrow">Research evidence → advisory</div>
        <h1>From trial response to spatial fertilizer target setting</h1>
        <p class="lead">
          A reproducible framework for translating NSAF maize trials into nutrient-response evidence,
          nitrogen-use efficiency, target-yield demand, and spatial response domains for western Nepal.
        </p>
        <div class="hero-actions">
          <a class="btn primary" href="#evidence">Explore evidence</a>
          <a class="btn secondary" href="#methods">View analytical logic</a>
        </div>
      </div>
      <div class="hero-card">
        <div class="hero-card-label">Analytical sequence</div>
        <div class="flow">
          <span>0-0-0</span><b>→</b><span>Omission</span><b>→</b><span>NPK</span><b>→</b><span>N rate</span><b>→</b><span>4R</span><b>→</b><span>Spatial target</span>
        </div>
        <p>Observed trial contrasts remain separate from DSM covariates and QUEFTS demand scenarios.</p>
      </div>
    </div>
  </section>

  <section id="evidence" class="section shell">
    <div class="section-heading">
      <div class="eyebrow">NSAF experimental evidence</div>
      <h2>Progressive nutrient-management interpretation</h2>
      <p>The reporting sequence follows the experimental design rather than collapsing treatments into a single response indicator.</p>
    </div>
    <div class="card-grid">
      ${sections.map(s => `
        <article class="evidence-card">
          <div class="card-kicker">${s.kicker}</div>
          <h3>${s.title}</h3>
          <p>${s.text}</p>
        </article>
      `).join("")}
    </div>
  </section>

  <section id="spatial" class="section section-tint">
    <div class="shell">
      <div class="section-heading">
        <div class="eyebrow">Western Nepal</div>
        <h2>Spatial response and fertilizer-demand indicators</h2>
        <p>
          Spatial prediction is used to characterize response domains, while QUEFTS provides target-yield nutrient-demand scenarios.
          DSM values are interpreted as modelled covariates, not as measured soil samples at every pixel.
        </p>
      </div>
      <div class="metric-grid">
        ${metrics.map(m => `
          <div class="metric-card">
            <div class="metric-name">${m[0]}</div>
            <div class="metric-unit">${m[1]}</div>
            <div class="metric-desc">${m[2]}</div>
          </div>
        `).join("")}
      </div>
      <div class="note">
        <strong>Current use:</strong> response comparison, target setting and identification of spatial heterogeneity.
        Pixel-level predictions retain model-support and validation limitations.
      </div>
    </div>
  </section>

  <section id="methods" class="section shell">
    <div class="section-heading">
      <div class="eyebrow">Methods</div>
      <h2>Keep the models distinct</h2>
    </div>
    <div class="methods-grid">
      <div>
        <h3>Observed trial response</h3>
        <p>Yield gain, AE-N, PFP-N and differences from GR are calculated from the NSAF treatment structure using matched site-year evidence.</p>
      </div>
      <div>
        <h3>QUEFTS demand</h3>
        <p>Target-yield nutrient demand is estimated from native nutrient supply and explicit internal- and recovery-efficiency assumptions.</p>
      </div>
      <div>
        <h3>Spatial extrapolation</h3>
        <p>Trial-derived response indicators are related to soil and environmental covariates, with extrapolation restricted by environmental support.</p>
      </div>
    </div>
  </section>

  <section id="references" class="section references">
    <div class="shell">
      <div class="section-heading">
        <div class="eyebrow">Scientific basis</div>
        <h2>Selected reference</h2>
      </div>
      <article class="reference-card">
        <p>
          Pandit, N. R., Adhikari, S., Vista, S. P., & Choudhary, D. (2025).
          <em>Nitrogen Management Utilizing 4R Nutrient Stewardship: A Sustainable Strategy for Enhancing NUE,
          Reducing Maize Yield Gap and Increasing Farm Profitability.</em>
          Nitrogen, 6(1), 7.
        </p>
        <a href="https://doi.org/10.3390/nitrogen6010007" target="_blank" rel="noreferrer">Open publication ↗</a>
      </article>
    </div>
  </section>
</main>

<footer>
  <div class="shell footer-inner">
    <span>Soil Advisory · Nepal</span>
    <span>Research workflow for reproducible nutrient-management analysis</span>
  </div>
</footer>
`;
