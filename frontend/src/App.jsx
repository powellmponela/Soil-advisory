import { useState, useEffect } from 'react';
import Papa from 'papaparse';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Map, Activity, Sprout, Download, Database as DatabaseIcon, Workflow, LayoutDashboard } from 'lucide-react';
import DatabaseView from './components/DatabaseView';
import WorkflowManager from './components/WorkflowManager';
import './index.css';

function App() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('dashboard');

  useEffect(() => {
    const loadCSV = async () => {
      try {
        const response = await fetch('/nsaf_advisory_results.csv');
        const csvText = await response.text();
        
        Papa.parse(csvText, {
          header: true,
          dynamicTyping: true,
          complete: (results) => {
            const validData = results.data.filter(row => row.N_demand_kg_ha !== undefined);
            setData(validData);
            setLoading(false);
          },
          error: (error) => {
            console.error('Error parsing CSV:', error);
            setLoading(false);
          }
        });
      } catch (err) {
        console.error('Failed to fetch CSV', err);
        setLoading(false);
      }
    };
    
    loadCSV();
  }, []);

  if (loading) {
    return (
      <div className="loader-container">
        <div className="spinner"></div>
        <p>Loading DSS Advisory Models...</p>
      </div>
    );
  }

  const avgNDemand = data.reduce((acc, curr) => acc + (curr.N_demand_kg_ha || 0), 0) / (data.length || 1);
  const avgYieldGap = data.reduce((acc, curr) => acc + (curr.yield_gap_kg_ha || 0), 0) / (data.length || 1);
  const avgAEN = data.reduce((acc, curr) => acc + (curr.predicted_AE_N || 0), 0) / (data.length || 1);

  const chartData = data.slice(0, 50).map((d, i) => ({
    name: `Site ${i+1}`,
    NDemand: Math.max(0, d.N_demand_kg_ha || 0),
    YieldGap: d.yield_gap_kg_ha || 0
  }));

  const renderDashboard = () => (
    <>
      <div className="glass-panel" style={{ marginBottom: '2rem' }}>
        <h2 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Activity size={24} color="var(--accent-primary)" />
          Overview Analytics
        </h2>
        
        <div className="stat-grid">
          <div className="stat-card">
            <span className="stat-title">Avg N-Demand</span>
            <span className="stat-value">{avgNDemand.toFixed(1)} <span style={{fontSize: '1rem', color: 'var(--text-secondary)'}}>kg/ha</span></span>
          </div>
          <div className="stat-card">
            <span className="stat-title">Avg Yield Gap</span>
            <span className="stat-value blue">{avgYieldGap.toFixed(1)} <span style={{fontSize: '1rem', color: 'var(--text-secondary)'}}>kg/ha</span></span>
          </div>
          <div className="stat-card">
            <span className="stat-title">Avg AE-N</span>
            <span className="stat-value purple">{avgAEN.toFixed(2)}</span>
          </div>
        </div>

        <div style={{ marginTop: '2rem' }}>
          <h3 style={{ marginBottom: '1rem' }}>Demand vs Yield Gap (Sample)</h3>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorNDemand" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--accent-primary)" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="var(--accent-primary)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" vertical={false} />
                <XAxis dataKey="name" stroke="var(--text-secondary)" tick={{fontSize: 12}} hide />
                <YAxis stroke="var(--text-secondary)" tick={{fontSize: 12}} />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '8px' }}
                  itemStyle={{ color: 'var(--text-primary)' }}
                />
                <Area type="monotone" dataKey="NDemand" stroke="var(--accent-primary)" fillOpacity={1} fill="url(#colorNDemand)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="glass-panel" style={{ height: '700px', padding: '1rem', display: 'flex', flexDirection: 'column' }}>
        <h2 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem' }}>
          <Map size={24} color="var(--accent-secondary)" />
          Spatial Advisory Map
        </h2>
        <div className="map-container" style={{ flex: 1 }}>
          <MapContainer center={[27.7, 85.3]} zoom={7} scrollWheelZoom={true} style={{ height: '100%', width: '100%' }}>
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            />
            {data.slice(0, 300).map((point, idx) => {
              const lat = point.latitude || (27.7 + (Math.random() - 0.5) * 2);
              const lon = point.longitude || (85.3 + (Math.random() - 0.5) * 4);
              return (
              <CircleMarker 
                key={idx}
                center={[lat, lon]} 
                radius={4}
                pathOptions={{ 
                  color: point.N_demand_kg_ha > 150 ? '#ef4444' : '#10b981',
                  fillColor: point.N_demand_kg_ha > 150 ? '#ef4444' : '#10b981',
                  fillOpacity: 0.7 
                }}
              >
                <Popup>
                  <div style={{ fontFamily: 'Outfit, sans-serif' }}>
                    <h3 style={{ margin: '0 0 8px 0', borderBottom: '1px solid var(--border-color)', paddingBottom: '4px' }}>
                      <Sprout size={16} style={{ verticalAlign: 'middle', marginRight: '4px', color: 'var(--accent-primary)' }}/>
                      NSAF Advisory Plot
                    </h3>
                    <p style={{ margin: '4px 0' }}><strong>Yield Target:</strong> 8000 kg/ha</p>
                    <p style={{ margin: '4px 0' }}><strong>Base Yield:</strong> {(point.base_yield_kg_ha || 0).toFixed(0)} kg/ha</p>
                    <p style={{ margin: '4px 0' }}><strong>N-Demand:</strong> {(point.N_demand_kg_ha || 0).toFixed(1)} kg/ha</p>
                    <p style={{ margin: '4px 0' }}><strong>Predicted AE-N:</strong> {(point.predicted_AE_N || 0).toFixed(2)}</p>
                  </div>
                </Popup>
              </CircleMarker>
              );
            })}
          </MapContainer>
        </div>
      </div>
    </>
  );

  return (
    <div className="dashboard-container">
      {/* Sidebar Navigation */}
      <div className="sidebar">
        <div className="header">
          <h1>Soil Advisory</h1>
          <p>AURORA Decision Support System</p>
        </div>

        <div className="nav-menu">
          <button 
            className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            <LayoutDashboard size={20} />
            Analytics Dashboard
          </button>
          
          <button 
            className={`nav-item ${activeTab === 'database' ? 'active' : ''}`}
            onClick={() => setActiveTab('database')}
          >
            <DatabaseIcon size={20} />
            Data Inventory
          </button>
          
          <button 
            className={`nav-item ${activeTab === 'workflow' ? 'active' : ''}`}
            onClick={() => setActiveTab('workflow')}
          >
            <Workflow size={20} />
            Pipeline Workflow
          </button>
        </div>

        <button className="btn" style={{ width: '100%', justifyContent: 'center', marginTop: '2rem' }}>
          <Download size={20} />
          Export Report
        </button>
      </div>

      {/* Main Content Area */}
      <div className="main-content">
        {activeTab === 'dashboard' && renderDashboard()}
        {activeTab === 'database' && <DatabaseView />}
        {activeTab === 'workflow' && <WorkflowManager />}
      </div>
    </div>
  );
}

export default App;
