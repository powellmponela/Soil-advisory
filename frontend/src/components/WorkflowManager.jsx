import React, { useState } from 'react';
import { PlayCircle, CheckCircle, Clock, Loader2, Workflow } from 'lucide-react';

const WORKFLOW_STEPS = [
  { id: '1c', name: '1c_extract_narc_western_highres_primary.py', desc: 'Extracts primary high-res NARC/DSM soil data' },
  { id: '2a', name: '2a_match_2018_trials_to_narc.py', desc: 'Matches 2018 trials to NARC spatial data' },
  { id: '2b', name: '2b_match_2019_demos_and_controls.py', desc: 'Matches 2019 demos and creates pooled controls' },
  { id: '2c', name: '2c_assign_farmer_ids.py', desc: 'Assigns standard farmer IDs' },
  { id: '4c', name: '4c_run_quefts_western_highres_primary.R', desc: 'Runs QUEFTS model for high-res pixels' },
  { id: '6', name: '6_consolidate_3year_trials.py', desc: 'Consolidates 3-year harmonized trials' },
  { id: '7', name: '7_train_nue_rf_model.py', desc: 'Trains NUE Random Forest Model' },
  { id: '8', name: '8_generate_spatial_impact_maps.py', desc: 'Generates spatial impact and advisory maps' },
  { id: '9', name: '9_calculate_national_impact.py', desc: 'Calculates national impact and savings' },
];

const WorkflowManager = () => {
  const [stepStatus, setStepStatus] = useState({}); // { [id]: 'idle' | 'running' | 'completed' }

  const runStep = async (step) => {
    setStepStatus(prev => ({ ...prev, [step.id]: 'running' }));
    
    try {
      const response = await fetch('http://localhost:3001/api/run-script', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scriptName: step.name })
      });
      
      const result = await response.json();
      
      if (result.success) {
        setStepStatus(prev => ({ ...prev, [step.id]: 'completed' }));
      } else {
        console.error("Script Error:", result.error);
        setStepStatus(prev => ({ ...prev, [step.id]: 'error' }));
      }
    } catch (err) {
      console.error("Server Error:", err);
      setStepStatus(prev => ({ ...prev, [step.id]: 'error' }));
    }
  };

  const runAll = async () => {
    for (const step of WORKFLOW_STEPS) {
      if (stepStatus[step.id] !== 'completed') {
        await runStep(step);
      }
    }
  };

  return (
    <div className="glass-panel" style={{ minHeight: '80vh' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Workflow size={28} color="var(--accent-secondary)" />
          Pipeline Workflow Execution
        </h2>
        <button className="btn" onClick={runAll}>
          <PlayCircle size={20} />
          Run All Steps Sequentially
        </button>
      </div>

      <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>
        Execute the data preparation, modeling, and output generation scripts step-by-step.
      </p>

      <div className="workflow-stepper">
        {WORKFLOW_STEPS.map((step, idx) => {
          const status = stepStatus[step.id] || 'idle';
          
          let stepClass = 'workflow-step';
          if (status === 'running') stepClass += ' active';
          if (status === 'completed') stepClass += ' completed';

          return (
            <div key={step.id} className={stepClass}>
              <div className="step-number">{idx + 1}</div>
              <div className="step-content">
                <div className="step-title">{step.name}</div>
                <div className="step-desc">{step.desc}</div>
              </div>
              <div className="step-actions">
                {status === 'idle' && (
                  <button className="btn-secondary" onClick={() => runStep(step)}>
                    <PlayCircle size={18} style={{ verticalAlign: 'middle', marginRight: '6px' }} />
                    Run Script
                  </button>
                )}
                {status === 'running' && (
                  <span style={{ color: 'var(--accent-primary)', display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}>
                    <Loader2 size={18} className="spinner" style={{ animation: 'spin 2s linear infinite' }} />
                    Executing...
                  </span>
                )}
                {status === 'completed' && (
                  <span style={{ color: 'var(--accent-secondary)', display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}>
                    <CheckCircle size={18} />
                    Completed
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default WorkflowManager;
