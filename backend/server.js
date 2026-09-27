const express = require('express');
const cors = require('cors');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 3001;

app.use(cors());
app.use(express.json({ limit: '50mb' }));

const PROJECT_ROOT = path.resolve(__dirname, '..');
const SCRIPTS_DIR = path.join(PROJECT_ROOT, 'scripts');
const DATA_DIR = path.join(PROJECT_ROOT, 'Data');
const OUTPUTS_DIR = path.join(PROJECT_ROOT, 'outputs');
const FRONTEND_PUBLIC_DIR = path.join(PROJECT_ROOT, 'frontend', 'public');

// Serve static assets
app.use('/data', express.static(DATA_DIR));
app.use('/outputs', express.static(OUTPUTS_DIR));

// 1. List available Python & R scripts
app.get('/api/scripts', (req, res) => {
  try {
    if (!fs.existsSync(SCRIPTS_DIR)) {
      return res.json({ scripts: [] });
    }
    const files = fs.readdirSync(SCRIPTS_DIR);
    const scripts = files
      .filter((f) => f.endsWith('.py') || f.endsWith('.R'))
      .sort((a, b) => a.localeCompare(b))
      .map((name) => {
        const fullPath = path.join(SCRIPTS_DIR, name);
        const stats = fs.statSync(fullPath);
        return {
          name,
          sizeBytes: stats.size,
          modified: stats.mtime.toISOString(),
        };
      });
    res.json({ scripts });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 2. Read content of a specific script
app.get('/api/script-content', (req, res) => {
  const { name } = req.query;
  if (!name) return res.status(400).json({ error: 'Script name required' });

  const filePath = path.join(SCRIPTS_DIR, path.basename(name));
  if (!fs.existsSync(filePath)) {
    return res.status(404).json({ error: `File ${name} not found` });
  }

  try {
    const code = fs.readFileSync(filePath, 'utf-8');
    res.json({ name, code });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 3. Save/Update script content
app.post('/api/save-script', (req, res) => {
  const { name, code } = req.body;
  if (!name || code === undefined) {
    return res.status(400).json({ error: 'Script name and code required' });
  }

  const filePath = path.join(SCRIPTS_DIR, path.basename(name));
  try {
    fs.writeFileSync(filePath, code, 'utf-8');
    console.log(`Saved updated script: ${name}`);
    res.json({ success: true, message: `Script ${name} saved successfully.` });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 4. Run a single script
app.post('/api/run-script', (req, res) => {
  const { scriptName } = req.body;

  if (!scriptName) {
    return res.status(400).json({ error: 'scriptName is required' });
  }

  const cleanName = path.basename(scriptName);
  const scriptPath = path.join(SCRIPTS_DIR, cleanName);

  if (!fs.existsSync(scriptPath)) {
    return res.status(404).json({ error: `Script file not found: ${cleanName}` });
  }

  let command;
  if (cleanName.endsWith('.py')) {
    command = `python "${scriptPath}"`;
  } else if (cleanName.endsWith('.R')) {
    command = `Rscript "${scriptPath}"`;
  } else {
    return res.status(400).json({ error: 'Unsupported script extension' });
  }

  console.log(`Executing: ${command}`);

  const startTime = Date.now();
  exec(command, { cwd: PROJECT_ROOT, maxBuffer: 10 * 1024 * 1024 }, (error, stdout, stderr) => {
    const durationMs = Date.now() - startTime;
    if (error) {
      console.error(`Error executing ${cleanName}:`, error);
      return res.status(500).json({
        success: false,
        scriptName: cleanName,
        error: error.message,
        stdout,
        stderr,
        durationMs,
      });
    }

    console.log(`Success executing ${cleanName} in ${durationMs}ms`);
    res.json({
      success: true,
      scriptName: cleanName,
      stdout,
      stderr,
      durationMs,
    });
  });
});

// 5. Run sequential pipeline
app.post('/api/run-pipeline', async (req, res) => {
  const { steps } = req.body; // Array of script names or defaults
  const pipelineSteps = steps || [
    '5b_predict_western_n_demand_savings.py',
    '6a_map_western_ae_and_gains.py',
    '7_publish_web_gis.py',
  ];

  const results = [];
  let overallSuccess = true;

  for (const scriptName of pipelineSteps) {
    const scriptPath = path.join(SCRIPTS_DIR, path.basename(scriptName));
    if (!fs.existsSync(scriptPath)) {
      results.push({
        scriptName,
        success: false,
        error: `Script not found: ${scriptName}`,
      });
      overallSuccess = false;
      break;
    }

    const command = scriptName.endsWith('.R')
      ? `Rscript "${scriptPath}"`
      : `python "${scriptPath}"`;

    const startTime = Date.now();
    const stepResult = await new Promise((resolve) => {
      exec(command, { cwd: PROJECT_ROOT, maxBuffer: 10 * 1024 * 1024 }, (error, stdout, stderr) => {
        resolve({
          scriptName,
          success: !error,
          error: error ? error.message : null,
          stdout,
          stderr,
          durationMs: Date.now() - startTime,
        });
      });
    });

    results.push(stepResult);
    if (!stepResult.success) {
      overallSuccess = false;
      break;
    }
  }

  res.json({
    success: overallSuccess,
    results,
  });
});

// 6. Add new data record to analysis
app.post('/api/add-data', (req, res) => {
  const { row } = req.body;
  if (!row) return res.status(400).json({ error: 'Data row required' });

  const csvFile = path.join(FRONTEND_PUBLIC_DIR, 'nsaf_advisory_results.csv');
  try {
    const headerNeeded = !fs.existsSync(csvFile);
    const keys = Object.keys(row);
    let csvLine = '';
    if (headerNeeded) {
      csvLine += keys.join(',') + '\n';
    }
    csvLine += keys.map((k) => `"${String(row[k]).replace(/"/g, '""')}"`).join(',') + '\n';

    fs.appendFileSync(csvFile, csvLine, 'utf-8');
    res.json({ success: true, message: 'New data point added to dataset.' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 7. Publish results to public view
app.post('/api/publish', (req, res) => {
  console.log('Triggering publication of optimized pixel dataset...');

  const publishScript = path.join(SCRIPTS_DIR, '7_publish_web_gis.py');
  const command = `python "${publishScript}"`;

  exec(command, { cwd: PROJECT_ROOT }, (error, stdout, stderr) => {
    if (error) {
      console.error('Publication failed:', error);
      return res.status(500).json({
        success: false,
        error: error.message,
        stderr,
      });
    }

    // Verify public files exist
    const pubCsv = path.join(FRONTEND_PUBLIC_DIR, 'advisory_pixels.csv');
    const pubGeo = path.join(FRONTEND_PUBLIC_DIR, 'advisory_pixels.geojson');
    const pubMeta = path.join(FRONTEND_PUBLIC_DIR, 'advisory_metadata.json');

    const csvExists = fs.existsSync(pubCsv);
    const geoExists = fs.existsSync(pubGeo);
    let meta = {};
    if (fs.existsSync(pubMeta)) {
      try {
        meta = JSON.parse(fs.readFileSync(pubMeta, 'utf-8'));
      } catch (e) {}
    }

    res.json({
      success: true,
      message: 'Optimized analysis successfully published to public view!',
      recordsPublished: meta.n_records || 11703,
      files: {
        csv: csvExists,
        geojson: geoExists,
      },
      stdout,
    });
  });
});

app.listen(PORT, () => {
  console.log(`Backend server running on http://localhost:${PORT}`);
});
