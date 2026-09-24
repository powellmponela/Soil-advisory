import React, { useState, useEffect } from 'react';
import Papa from 'papaparse';
import { Database, FileText, CheckCircle2, XCircle } from 'lucide-react';

const DatabaseView = () => {
  const [inventory, setInventory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadInventory = async () => {
      try {
        const response = await fetch('/stage0_input_inventory.csv');
        const csvText = await response.text();
        Papa.parse(csvText, {
          header: true,
          dynamicTyping: true,
          complete: (results) => {
            setInventory(results.data.filter(item => item.name)); // filter empty rows
            setLoading(false);
          }
        });
      } catch (err) {
        console.error('Failed to load inventory', err);
        setLoading(false);
      }
    };
    loadInventory();
  }, []);

  if (loading) {
    return (
      <div className="loader-container">
        <div className="spinner"></div>
        <p>Loading Database Inventory...</p>
      </div>
    );
  }

  // Group inventory by category
  const grouped = inventory.reduce((acc, curr) => {
    if (!acc[curr.category]) {
      acc[curr.category] = [];
    }
    acc[curr.category].push(curr);
    return acc;
  }, {});

  return (
    <div className="glass-panel" style={{ minHeight: '80vh' }}>
      <h2 style={{ marginBottom: '2rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <Database size={28} color="var(--accent-primary)" />
        Database & Input Inventory
      </h2>

      {Object.entries(grouped).map(([category, items]) => (
        <div key={category} style={{ marginBottom: '3rem' }}>
          <h3 style={{ marginBottom: '1rem', color: 'var(--text-secondary)', textTransform: 'capitalize' }}>
            {category.replace(/_/g, ' ')}
          </h3>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Name / Path</th>
                  <th>Type</th>
                  <th>Size (MB)</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item, idx) => (
                  <tr key={idx}>
                    <td>
                      {item.exists ? (
                        <span className="status-badge success"><CheckCircle2 size={14} style={{marginRight: '4px'}}/> Available</span>
                      ) : (
                        <span className="status-badge error"><XCircle size={14} style={{marginRight: '4px'}}/> Missing</span>
                      )}
                    </td>
                    <td>
                      <div style={{ fontWeight: 500, color: 'var(--text-primary)' }}>
                        <FileText size={16} style={{ verticalAlign: 'middle', marginRight: '6px', color: 'var(--accent-secondary)'}} />
                        {item.name}
                      </div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                        {item.path}
                      </div>
                    </td>
                    <td>{item.is_dir ? 'Directory' : 'File'}</td>
                    <td>{item.size_mb || '-'}</td>
                    <td style={{ maxWidth: '300px', fontSize: '0.9rem' }}>{item.notes}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
};

export default DatabaseView;
