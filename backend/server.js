const express = require('express');
const cors = require('cors');
const { exec } = require('child_process');
const path = require('path');

const app = express();
const PORT = 3001;

app.use(cors());
app.use(express.json());

const PROJECT_ROOT = path.resolve(__dirname, '..');
const SCRIPTS_DIR = path.join(PROJECT_ROOT, 'scripts');
const DATA_DIR = path.join(PROJECT_ROOT, 'Data');

// Serve the Data directory statically so frontend can access rasters/vectors
app.use('/data', express.static(DATA_DIR));

app.post('/api/run-script', (req, res) => {
  const { scriptName } = req.body;

  if (!scriptName) {
    return res.status(400).json({ error: 'scriptName is required' });
  }

  // Determine runner based on file extension
  let command;
  if (scriptName.endsWith('.py')) {
    command = `python "${path.join(SCRIPTS_DIR, scriptName)}"`;
  } else if (scriptName.endsWith('.R')) {
    command = `Rscript "${path.join(SCRIPTS_DIR, scriptName)}"`;
  } else {
    return res.status(400).json({ error: 'Unsupported script extension' });
  }

  console.log(`Executing: ${command}`);

  exec(command, { cwd: PROJECT_ROOT }, (error, stdout, stderr) => {
    if (error) {
      console.error(`Error executing ${scriptName}:`, error);
      console.error(`Stderr: ${stderr}`);
      return res.status(500).json({ 
        success: false, 
        error: error.message, 
        stderr 
      });
    }

    console.log(`Success: ${scriptName}`);
    res.json({ 
      success: true, 
      stdout 
    });
  });
});

app.listen(PORT, () => {
  console.log(`Backend server running on http://localhost:${PORT}`);
});
