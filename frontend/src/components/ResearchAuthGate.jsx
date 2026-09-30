import React, { useState, useEffect } from 'react';

export const ROLE_CONFIG = {
  view: {
    id: 'view',
    label: 'View (Read-Only)',
    badgeColor: '#475569',
    badgeBg: '#f1f5f9',
    badgeBorder: '#cbd5e1',
    icon: '👁️',
    description: 'Inspect multi-year trial plots, QUEFTS calibration, site-year-treatment statistics, and model code.',
    passwords: ['view2026', 'view'],
    canUpload: false,
    canSuggest: false,
    canEdit: false,
    canPublish: false,
  },
  suggest: {
    id: 'suggest',
    label: 'Suggest (Contributor)',
    badgeColor: '#0369a1',
    badgeBg: '#e0f2fe',
    badgeBorder: '#7dd3fc',
    icon: '✍️',
    description: 'View all datasets and propose additional trial plot observations or field notes for review.',
    passwords: ['suggest2026', 'suggest'],
    canUpload: false,
    canSuggest: true,
    canEdit: false,
    canPublish: false,
  },
  edit: {
    id: 'edit',
    label: 'Edit (Administrator / Lead)',
    badgeColor: '#15803d',
    badgeBg: '#dcfce7',
    badgeBorder: '#86efac',
    icon: '🛠️',
    description: 'Full administrative rights to upload CSV datasets, modify trial records, manage users, and publish updates.',
    passwords: ['edit2026', 'edit', 'admin2026', 'powell2026', 'soil2026'],
    canUpload: true,
    canSuggest: true,
    canEdit: true,
    canPublish: true,
    isAdmin: true,
  },
};

const AUTH_STORAGE_KEY = 'soil_advisory_research_auth';
const REGISTRY_STORAGE_KEY = 'soil_advisory_user_registry';
const REQUESTS_STORAGE_KEY = 'soil_advisory_access_requests';

// Initial pre-configured registry of approved emails
const DEFAULT_REGISTRY = {
  'powellmponel@gmail.com': { role: 'edit', name: 'Powell Mponela (Admin)', org: 'Soil Advisory Lead', approvedAt: '2026-09-28' },
  'admin@soiladvisory.org': { role: 'edit', name: 'Powell Mponela', org: 'NARC / CIMMYT', approvedAt: '2026-09-28' },
  'viewer@narc.gov.np': { role: 'view', name: 'NARC Extension Officer', org: 'NARC', approvedAt: '2026-09-29' },
  'agronomist@cimmyt.org': { role: 'suggest', name: 'Field Agronomist', org: 'CIMMYT', approvedAt: '2026-09-29' },
  'lead@soiladvisory.org': { role: 'edit', name: 'Lead Scientist', org: 'Soil Advisory', approvedAt: '2026-09-29' },
};

// Initial sample access request for Powell Mponela to review
const DEFAULT_REQUESTS = [
  {
    id: 'req_1',
    email: 'karnali.extension@moald.gov.np',
    name: 'Karnali Extension Unit',
    org: 'Ministry of Agriculture and Livestock Development',
    desiredRole: 'suggest',
    reason: 'Review trial data and contribute 2026 summer maize verification plots from Surkhet and Salyan.',
    submittedAt: '2026-09-30 08:30',
    status: 'pending',
  },
];

export function getRegistry() {
  try {
    const raw = localStorage.getItem(REGISTRY_STORAGE_KEY);
    if (raw) return { ...DEFAULT_REGISTRY, ...JSON.parse(raw) };
  } catch (_) {}
  return DEFAULT_REGISTRY;
}

export function saveRegistry(registry) {
  try {
    localStorage.setItem(REGISTRY_STORAGE_KEY, JSON.stringify(registry));
  } catch (_) {}
}

export function getAccessRequests() {
  try {
    const raw = localStorage.getItem(REQUESTS_STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch (_) {}
  return DEFAULT_REQUESTS;
}

export function saveAccessRequests(requests) {
  try {
    localStorage.setItem(REQUESTS_STORAGE_KEY, JSON.stringify(requests));
  } catch (_) {}
}

export function getStoredAuth() {
  try {
    const raw = sessionStorage.getItem(AUTH_STORAGE_KEY) || localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed && parsed.role && ROLE_CONFIG[parsed.role]) {
      return parsed;
    }
  } catch (_) {}
  return null;
}

export function saveAuth(role, email = null, remember = false) {
  const data = JSON.stringify({ role, email, timestamp: Date.now() });
  sessionStorage.setItem(AUTH_STORAGE_KEY, data);
  if (remember) {
    localStorage.setItem(AUTH_STORAGE_KEY, data);
  }
}

export function clearAuth() {
  sessionStorage.removeItem(AUTH_STORAGE_KEY);
  localStorage.removeItem(AUTH_STORAGE_KEY);
}

export default function ResearchAuthGate({ onLogin }) {
  const [activeTab, setActiveTab] = useState('email'); // 'email' | 'request' | 'password'
  
  // Email Login State
  const [loginEmail, setLoginEmail] = useState('');
  const [remember, setRemember] = useState(true);
  const [emailError, setEmailError] = useState('');
  const [emailSuccess, setEmailSuccess] = useState('');

  // Access Request Form State
  const [reqEmail, setReqEmail] = useState('');
  const [reqName, setReqName] = useState('');
  const [reqOrg, setReqOrg] = useState('');
  const [reqRole, setReqRole] = useState('view');
  const [reqReason, setReqReason] = useState('');
  const [reqSubmitted, setReqSubmitted] = useState(false);

  // Role Password State
  const [selectedRole, setSelectedRole] = useState('view');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [passError, setPassError] = useState('');

  const [registry, setRegistry] = useState(getRegistry());

  useEffect(() => {
    setRegistry(getRegistry());
  }, []);

  // Handle email login
  const handleEmailLogin = (e) => {
    e.preventDefault();
    setEmailError('');
    setEmailSuccess('');
    const cleanEmail = loginEmail.trim().toLowerCase();

    // Check if Powell Mponela admin
    if (cleanEmail === 'powellmponel@gmail.com' || cleanEmail === 'powell.mponela@cimmyt.org') {
      saveAuth('edit', cleanEmail, remember);
      setEmailSuccess('🎉 Welcome back, Admin Powell Mponela! Logging into Edit role…');
      setTimeout(() => onLogin('edit', cleanEmail), 500);
      return;
    }

    const reg = getRegistry();
    const user = reg[cleanEmail];

    if (user && user.role && ROLE_CONFIG[user.role]) {
      saveAuth(user.role, cleanEmail, remember);
      setEmailSuccess(`🎉 Welcome, ${user.name || cleanEmail}! Granted ${ROLE_CONFIG[user.role].label} access.`);
      setTimeout(() => onLogin(user.role, cleanEmail), 500);
    } else {
      setEmailError(`No approved role found for "${cleanEmail}". Please submit an access request below for Admin Powell Mponela to grant you View, Suggest, or Edit access.`);
    }
  };

  // Handle access request submission
  const handleRequestSubmit = (e) => {
    e.preventDefault();
    const cleanEmail = reqEmail.trim().toLowerCase();
    const requests = getAccessRequests();

    const newReq = {
      id: `req_${Date.now()}`,
      email: cleanEmail,
      name: reqName.trim(),
      org: reqOrg.trim(),
      desiredRole: reqRole,
      reason: reqReason.trim(),
      submittedAt: new Date().toISOString().replace('T', ' ').slice(0, 16),
      status: 'pending',
    };

    saveAccessRequests([newReq, ...requests.filter((r) => r.email !== cleanEmail)]);
    setReqSubmitted(true);
  };

  // Handle role password login
  const handlePasswordLogin = (e) => {
    e.preventDefault();
    setPassError('');
    const cfg = ROLE_CONFIG[selectedRole];
    const cleaned = password.trim().toLowerCase();

    if (cfg && cfg.passwords.includes(cleaned)) {
      saveAuth(selectedRole, null, remember);
      onLogin(selectedRole, null);
    } else {
      setPassError(`Invalid passcode for ${cfg.label} role.`);
    }
  };

  return (
    <div style={{
      maxWidth: '720px',
      margin: '2.5rem auto',
      background: '#ffffff',
      borderRadius: '16px',
      boxShadow: '0 10px 30px rgba(0, 30, 15, 0.08), 0 2px 8px rgba(0, 0, 0, 0.04)',
      border: '1px solid #d1e3d7',
      overflow: 'hidden',
    }}>
      {/* Header Banner */}
      <div style={{
        background: 'linear-gradient(135deg, #0f4028 0%, #1e5a3c 100%)',
        color: '#ffffff',
        padding: '2rem 2.25rem 1.75rem',
        textAlign: 'center',
      }}>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '56px',
          height: '56px',
          background: 'rgba(255, 255, 255, 0.15)',
          borderRadius: '50%',
          fontSize: '1.8rem',
          marginBottom: '.85rem',
          boxShadow: '0 2px 10px rgba(0,0,0,0.15)',
        }}>
          🔒
        </div>
        <h2 style={{ margin: '0 0 .5rem', fontSize: '1.65rem', fontFamily: 'Source Serif 4, serif' }}>
          Research Workspace Access
        </h2>
        <p style={{ margin: 0, color: '#d0e5d8', fontSize: '.92rem', lineHeight: 1.5, maxWidth: '560px', marginLeft: 'auto', marginRight: 'auto' }}>
          Restricted agronomic workspace. Request role-based access with your email address for review by <strong>Admin Powell Mponela</strong> (View, Suggest, and Edit tiers).
        </p>
      </div>

      {/* Mode Navigation Tabs */}
      <div style={{
        display: 'flex',
        borderBottom: '1px solid #e2e8f0',
        background: '#f8fafc',
      }}>
        <button
          type="button"
          onClick={() => setActiveTab('email')}
          style={{
            flex: 1,
            padding: '.85rem',
            background: activeTab === 'email' ? '#ffffff' : 'transparent',
            border: 'none',
            borderBottom: activeTab === 'email' ? '3px solid #0f4028' : '3px solid transparent',
            color: activeTab === 'email' ? '#0f4028' : '#64748b',
            fontWeight: 800,
            fontSize: '.88rem',
            cursor: 'pointer',
          }}
        >
          ✉️ Sign In with Email
        </button>
        <button
          type="button"
          onClick={() => { setActiveTab('request'); setReqSubmitted(false); }}
          style={{
            flex: 1,
            padding: '.85rem',
            background: activeTab === 'request' ? '#ffffff' : 'transparent',
            border: 'none',
            borderBottom: activeTab === 'request' ? '3px solid #0f4028' : '3px solid transparent',
            color: activeTab === 'request' ? '#0f4028' : '#64748b',
            fontWeight: 800,
            fontSize: '.88rem',
            cursor: 'pointer',
          }}
        >
          📝 Request Access
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('password')}
          style={{
            flex: 1,
            padding: '.85rem',
            background: activeTab === 'password' ? '#ffffff' : 'transparent',
            border: 'none',
            borderBottom: activeTab === 'password' ? '3px solid #0f4028' : '3px solid transparent',
            color: activeTab === 'password' ? '#0f4028' : '#64748b',
            fontWeight: 800,
            fontSize: '.88rem',
            cursor: 'pointer',
          }}
        >
          🔑 Role Passcode
        </button>
      </div>

      <div style={{ padding: '2rem 2.25rem' }}>
        {/* ── TAB 1: EMAIL SIGN IN ── */}
        {activeTab === 'email' && (
          <div>
            <div style={{ marginBottom: '1.25rem' }}>
              <h3 style={{ margin: '0 0 .35rem', color: '#0f4028', fontSize: '1.15rem' }}>
                Sign In with Granted Email Address
              </h3>
              <p style={{ margin: 0, color: '#64748b', fontSize: '.84rem' }}>
                Enter the email address registered with or granted permissions by Admin Powell Mponela.
              </p>
            </div>

            <form onSubmit={handleEmailLogin}>
              <div style={{ marginBottom: '1.25rem' }}>
                <label style={{ display: 'block', fontSize: '.78rem', fontWeight: 800, textTransform: 'uppercase', color: '#133e2b', marginBottom: '.4rem' }}>
                  Institutional / Professional Email
                </label>
                <input
                  type="email"
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                  placeholder="e.g. your.name@narc.gov.np or cimmyt.org"
                  required
                  autoFocus
                  style={{
                    width: '100%',
                    padding: '.75rem 1rem',
                    fontSize: '.95rem',
                    borderRadius: '8px',
                    border: '1.5px solid #276246',
                    outline: 'none',
                    boxSizing: 'border-box',
                    background: '#fcfdfd',
                  }}
                />
              </div>

              {emailError && (
                <div style={{
                  background: '#fef2f2',
                  border: '1px solid #f87171',
                  color: '#991b1b',
                  padding: '.75rem 1rem',
                  borderRadius: '8px',
                  fontSize: '.82rem',
                  marginBottom: '1.25rem',
                  lineHeight: 1.5,
                }}>
                  <div style={{ fontWeight: 700, marginBottom: '.25rem' }}>⚠ Access Not Yet Granted</div>
                  {emailError}
                  <div style={{ marginTop: '.5rem' }}>
                    <button
                      type="button"
                      onClick={() => { setActiveTab('request'); setReqEmail(loginEmail); }}
                      style={{
                        background: '#991b1b',
                        color: '#fff',
                        border: 'none',
                        padding: '.35rem .75rem',
                        borderRadius: '4px',
                        fontSize: '.76rem',
                        fontWeight: 700,
                        cursor: 'pointer',
                      }}
                    >
                      Fill Access Request Form →
                    </button>
                  </div>
                </div>
              )}

              {emailSuccess && (
                <div style={{
                  background: '#f0fdf4',
                  border: '1px solid #86efac',
                  color: '#166534',
                  padding: '.75rem 1rem',
                  borderRadius: '8px',
                  fontSize: '.84rem',
                  marginBottom: '1.25rem',
                  fontWeight: 700,
                }}>
                  {emailSuccess}
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '.45rem', fontSize: '.82rem', color: '#475569', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={remember}
                    onChange={(e) => setRemember(e.target.checked)}
                  />
                  Stay signed in on this computer
                </label>
              </div>

              <button
                type="submit"
                style={{
                  width: '100%',
                  padding: '.85rem 1.25rem',
                  background: '#0f4028',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '8px',
                  fontSize: '1rem',
                  fontWeight: 800,
                  cursor: 'pointer',
                  boxShadow: '0 4px 12px rgba(15, 64, 40, 0.25)',
                }}
              >
                Sign In to Research Space
              </button>
            </form>

            {/* Quick Demo Logins for Instant Testing */}
            <div style={{ marginTop: '1.75rem', paddingTop: '1.25rem', borderTop: '1px dashed #cbd5e1' }}>
              <div style={{ fontSize: '.75rem', fontWeight: 800, textTransform: 'uppercase', color: '#64748b', marginBottom: '.65rem' }}>
                ⚡ One-Click Verified Accounts for Testing
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '.65rem' }}>
                <button
                  type="button"
                  onClick={() => setLoginEmail('powellmponel@gmail.com')}
                  style={{
                    background: '#f0fdf4',
                    border: '1px solid #bbf7d0',
                    borderRadius: '6px',
                    padding: '.5rem .75rem',
                    textAlign: 'left',
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ fontWeight: 800, fontSize: '.78rem', color: '#15803d' }}>
                    👑 Admin Powell Mponela (Edit)
                  </div>
                  <div style={{ fontSize: '.72rem', color: '#475569' }}>powellmponel@gmail.com</div>
                </button>
                <button
                  type="button"
                  onClick={() => setLoginEmail('viewer@narc.gov.np')}
                  style={{
                    background: '#f8fafc',
                    border: '1px solid #e2e8f0',
                    borderRadius: '6px',
                    padding: '.5rem .75rem',
                    textAlign: 'left',
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ fontWeight: 800, fontSize: '.78rem', color: '#334155' }}>
                    👁️ NARC Researcher (View)
                  </div>
                  <div style={{ fontSize: '.72rem', color: '#475569' }}>viewer@narc.gov.np</div>
                </button>
                <button
                  type="button"
                  onClick={() => setLoginEmail('agronomist@cimmyt.org')}
                  style={{
                    background: '#f0f9ff',
                    border: '1px solid #bae6fd',
                    borderRadius: '6px',
                    padding: '.5rem .75rem',
                    textAlign: 'left',
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ fontWeight: 800, fontSize: '.78rem', color: '#0369a1' }}>
                    ✍️ Field Agronomist (Suggest)
                  </div>
                  <div style={{ fontSize: '.72rem', color: '#475569' }}>agronomist@cimmyt.org</div>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── TAB 2: REQUEST ACCESS ── */}
        {activeTab === 'request' && (
          <div>
            {!reqSubmitted ? (
              <div>
                <div style={{ marginBottom: '1.25rem' }}>
                  <h3 style={{ margin: '0 0 .35rem', color: '#0f4028', fontSize: '1.15rem' }}>
                    Request Role-Based Access from Powell Mponela
                  </h3>
                  <p style={{ margin: 0, color: '#64748b', fontSize: '.84rem' }}>
                    Submit your details and requested role. Admin Powell Mponela reviews and grants <strong>View</strong>, <strong>Suggest</strong>, or <strong>Edit</strong> permissions.
                  </p>
                </div>

                <form onSubmit={handleRequestSubmit}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '.76rem', fontWeight: 800, textTransform: 'uppercase', color: '#133e2b', marginBottom: '.3rem' }}>
                        Your Full Name
                      </label>
                      <input
                        type="text"
                        value={reqName}
                        onChange={(e) => setReqName(e.target.value)}
                        placeholder="e.g. Dr. Rita Sharma"
                        required
                        style={{ width: '100%', padding: '.65rem .85rem', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '.88rem', boxSizing: 'border-box' }}
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', fontSize: '.76rem', fontWeight: 800, textTransform: 'uppercase', color: '#133e2b', marginBottom: '.3rem' }}>
                        Your Email Address
                      </label>
                      <input
                        type="email"
                        value={reqEmail}
                        onChange={(e) => setReqEmail(e.target.value)}
                        placeholder="e.g. rita.sharma@narc.gov.np"
                        required
                        style={{ width: '100%', padding: '.65rem .85rem', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '.88rem', boxSizing: 'border-box' }}
                      />
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '.76rem', fontWeight: 800, textTransform: 'uppercase', color: '#133e2b', marginBottom: '.3rem' }}>
                        Institution / Organization
                      </label>
                      <input
                        type="text"
                        value={reqOrg}
                        onChange={(e) => setReqOrg(e.target.value)}
                        placeholder="e.g. NARC, MoALD, CIMMYT, University"
                        required
                        style={{ width: '100%', padding: '.65rem .85rem', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '.88rem', boxSizing: 'border-box' }}
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', fontSize: '.76rem', fontWeight: 800, textTransform: 'uppercase', color: '#133e2b', marginBottom: '.3rem' }}>
                        Requested Role
                      </label>
                      <select
                        value={reqRole}
                        onChange={(e) => setReqRole(e.target.value)}
                        style={{ width: '100%', padding: '.65rem .85rem', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '.88rem', fontWeight: 700, background: '#fff', boxSizing: 'border-box' }}
                      >
                        <option value="view">👁️ View (Read-Only Data &amp; Models)</option>
                        <option value="suggest">✍️ Suggest (Contribute Observations)</option>
                        <option value="edit">🛠️ Edit (Admin &amp; Publishing)</option>
                      </select>
                    </div>
                  </div>

                  <div style={{ marginBottom: '1.25rem' }}>
                    <label style={{ display: 'block', fontSize: '.76rem', fontWeight: 800, textTransform: 'uppercase', color: '#133e2b', marginBottom: '.3rem' }}>
                      Purpose of Access / Project Details
                    </label>
                    <textarea
                      value={reqReason}
                      onChange={(e) => setReqReason(e.target.value)}
                      placeholder="Describe what research data or tools you plan to evaluate or contribute..."
                      rows={3}
                      required
                      style={{ width: '100%', padding: '.65rem .85rem', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '.85rem', fontFamily: 'inherit', boxSizing: 'border-box' }}
                    />
                  </div>

                  <button
                    type="submit"
                    style={{
                      width: '100%',
                      padding: '.85rem',
                      background: '#0f4028',
                      color: '#ffffff',
                      border: 'none',
                      borderRadius: '8px',
                      fontSize: '.95rem',
                      fontWeight: 800,
                      cursor: 'pointer',
                    }}
                  >
                    Submit Access Request to Powell Mponela
                  </button>
                </form>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '1.5rem 0' }}>
                <div style={{ fontSize: '2.5rem', marginBottom: '.75rem' }}>✅</div>
                <h3 style={{ margin: '0 0 .5rem', color: '#0f4028' }}>Access Request Received!</h3>
                <p style={{ color: '#475569', fontSize: '.9rem', maxWidth: '480px', margin: '0 auto 1.5rem', lineHeight: 1.6 }}>
                  Your request for <strong>{ROLE_CONFIG[reqRole].label}</strong> role has been queued for <strong>Admin Powell Mponela</strong>.
                  Once approved, you will be able to sign in instantly with your email (<code>{reqEmail}</code>).
                </p>
                <button
                  type="button"
                  onClick={() => { setActiveTab('email'); setLoginEmail(reqEmail); }}
                  className="btn-sm"
                  style={{
                    background: '#0f4028',
                    color: '#fff',
                    padding: '.6rem 1.25rem',
                    borderRadius: '6px',
                    fontWeight: 700,
                    border: 'none',
                    cursor: 'pointer',
                  }}
                >
                  Back to Sign In
                </button>
              </div>
            )}
          </div>
        )}

        {/* ── TAB 3: ROLE PASSCODES (DIRECT TESTING / ADMIN) ── */}
        {activeTab === 'password' && (
          <div>
            <div style={{ marginBottom: '1.25rem' }}>
              <h3 style={{ margin: '0 0 .35rem', color: '#0f4028', fontSize: '1.15rem' }}>
                Direct Role Passcode Login
              </h3>
              <p style={{ margin: 0, color: '#64748b', fontSize: '.84rem' }}>
                Administrators and staff with pre-issued role tokens can authenticate directly.
              </p>
            </div>

            {/* Role Buttons */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '.75rem', marginBottom: '1.25rem' }}>
              {Object.values(ROLE_CONFIG).map((r) => (
                <button
                  key={r.id}
                  type="button"
                  onClick={() => { setSelectedRole(r.id); setPassError(''); }}
                  style={{
                    padding: '.75rem .5rem',
                    borderRadius: '8px',
                    border: selectedRole === r.id ? '2px solid #0f4028' : '1px solid #cbd5e1',
                    background: selectedRole === r.id ? '#f2f9f5' : '#ffffff',
                    cursor: 'pointer',
                    textAlign: 'center',
                  }}
                >
                  <div style={{ fontSize: '1.3rem' }}>{r.icon}</div>
                  <div style={{ fontSize: '.84rem', fontWeight: 800, color: selectedRole === r.id ? '#0f4028' : '#334155' }}>
                    {r.id.toUpperCase()}
                  </div>
                </button>
              ))}
            </div>

            <form onSubmit={handlePasswordLogin}>
              <div style={{ marginBottom: '1.25rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '.3rem' }}>
                  <label style={{ fontSize: '.76rem', fontWeight: 800, textTransform: 'uppercase', color: '#133e2b' }}>
                    Password for {selectedRole.toUpperCase()} Role
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    style={{ background: 'none', border: 'none', fontSize: '.75rem', color: '#0f4028', fontWeight: 700, cursor: 'pointer' }}
                  >
                    {showPassword ? 'Hide 🙈' : 'Show 👁️'}
                  </button>
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={`Enter password for ${selectedRole}...`}
                  required
                  style={{ width: '100%', padding: '.75rem 1rem', borderRadius: '8px', border: '1.5px solid #276246', fontSize: '.95rem', boxSizing: 'border-box' }}
                />
              </div>

              {passError && (
                <div style={{ background: '#fef2f2', border: '1px solid #f87171', color: '#991b1b', padding: '.65rem 1rem', borderRadius: '6px', fontSize: '.82rem', marginBottom: '1.25rem' }}>
                  ⚠ {passError}
                </div>
              )}

              <button
                type="submit"
                style={{ width: '100%', padding: '.85rem', background: '#0f4028', color: '#ffffff', border: 'none', borderRadius: '8px', fontSize: '.95rem', fontWeight: 800, cursor: 'pointer' }}
              >
                Authenticate as {selectedRole.toUpperCase()}
              </button>
            </form>

            <div style={{ marginTop: '1.25rem', padding: '.75rem', background: '#f8fafc', borderRadius: '6px', fontSize: '.76rem', color: '#475569' }}>
              <strong>Pre-configured Passcodes:</strong> View: <code>view2026</code> | Suggest: <code>suggest2026</code> | Edit / Admin: <code>powell2026</code> or <code>edit2026</code>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/** Admin Modal for Powell Mponela to review pending email requests and grant roles */
export function AdminRoleManagerModal({ isOpen, onClose, onRegistryUpdated }) {
  const [requests, setRequests] = useState(getAccessRequests());
  const [registry, setRegistry] = useState(getRegistry());
  const [manualEmail, setManualEmail] = useState('');
  const [manualName, setManualName] = useState('');
  const [manualRole, setManualRole] = useState('view');
  const [msg, setMsg] = useState('');

  if (!isOpen) return null;

  const handleGrant = (email, role, name = '', org = '') => {
    const updatedReg = {
      ...registry,
      [email]: { role, name, org, approvedAt: new Date().toISOString().slice(0, 10) },
    };
    saveRegistry(updatedReg);
    setRegistry(updatedReg);

    // Update request status
    const updatedReqs = requests.map((r) => r.email === email ? { ...r, status: 'approved', grantedRole: role } : r);
    saveAccessRequests(updatedReqs);
    setRequests(updatedReqs);

    setMsg(`✅ Granted "${role.toUpperCase()}" role to ${email}.`);
    if (onRegistryUpdated) onRegistryUpdated(updatedReg);
  };

  const handleRevoke = (email) => {
    const updatedReg = { ...registry };
    delete updatedReg[email];
    saveRegistry(updatedReg);
    setRegistry(updatedReg);
    setMsg(`Removed access for ${email}.`);
    if (onRegistryUpdated) onRegistryUpdated(updatedReg);
  };

  const handleManualAdd = (e) => {
    e.preventDefault();
    if (!manualEmail.trim()) return;
    handleGrant(manualEmail.trim().toLowerCase(), manualRole, manualName.trim(), 'Direct Grant');
    setManualEmail('');
    setManualName('');
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0, 0, 0, 0.65)',
      zIndex: 10000,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '1.5rem',
    }}>
      <div style={{
        background: '#ffffff',
        borderRadius: '16px',
        maxWidth: '820px',
        width: '100%',
        maxHeight: '90vh',
        overflowY: 'auto',
        boxShadow: '0 20px 40px rgba(0,0,0,0.3)',
      }}>
        {/* Modal Header */}
        <div style={{
          background: '#0f4028',
          color: '#ffffff',
          padding: '1.25rem 1.5rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderRadius: '16px 16px 0 0',
        }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.2rem' }}>👑 Admin Console: Powell Mponela</h3>
            <span style={{ fontSize: '.76rem', color: '#d0e5d8' }}>Review Access Requests &amp; Manage User Permissions</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: '#fff', fontSize: '1.5rem', cursor: 'pointer', padding: 0 }}
          >
            ✕
          </button>
        </div>

        <div style={{ padding: '1.5rem' }}>
          {msg && (
            <div style={{ background: '#f0fdf4', border: '1px solid #86efac', color: '#166534', padding: '.65rem 1rem', borderRadius: '6px', fontSize: '.84rem', fontWeight: 700, marginBottom: '1.25rem' }}>
              {msg}
            </div>
          )}

          {/* Pending Requests Section */}
          <div style={{ marginBottom: '2rem' }}>
            <h4 style={{ margin: '0 0 .65rem', color: '#0f4028', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '.5rem' }}>
              📬 Pending Access Requests ({requests.filter(r => r.status === 'pending').length})
            </h4>

            {requests.length === 0 ? (
              <p style={{ color: '#64748b', fontSize: '.84rem' }}>No pending requests.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '.75rem' }}>
                {requests.map((req) => (
                  <div key={req.id} style={{
                    background: req.status === 'approved' ? '#f8fafc' : '#ffffff',
                    border: req.status === 'approved' ? '1px solid #e2e8f0' : '1.5px solid #276246',
                    borderRadius: '8px',
                    padding: '1rem',
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '.5rem', marginBottom: '.5rem' }}>
                      <div>
                        <div style={{ fontWeight: 800, fontSize: '.9rem', color: '#0f4028' }}>{req.name} ({req.email})</div>
                        <div style={{ fontSize: '.76rem', color: '#64748b' }}>{req.org} · Requested: <strong>{req.desiredRole.toUpperCase()}</strong> · Submitted: {req.submittedAt}</div>
                      </div>
                      {req.status === 'approved' && (
                        <span style={{ fontSize: '.72rem', fontWeight: 800, background: '#dcfce7', color: '#15803d', padding: '.2rem .5rem', borderRadius: '4px' }}>
                          Approved: {req.grantedRole.toUpperCase()}
                        </span>
                      )}
                    </div>

                    <div style={{ fontSize: '.8rem', color: '#334155', background: '#f8fafc', padding: '.5rem .75rem', borderRadius: '6px', marginBottom: '.75rem' }}>
                      <em>"{req.reason}"</em>
                    </div>

                    <div style={{ display: 'flex', gap: '.4rem', flexWrap: 'wrap' }}>
                      <span style={{ fontSize: '.75rem', fontWeight: 700, color: '#475569', alignSelf: 'center', marginRight: '.25rem' }}>Grant Role:</span>
                      <button
                        type="button"
                        onClick={() => handleGrant(req.email, 'view', req.name, req.org)}
                        style={{ padding: '.25rem .6rem', fontSize: '.74rem', fontWeight: 700, background: '#f1f5f9', border: '1px solid #cbd5e1', borderRadius: '4px', cursor: 'pointer' }}
                      >
                        👁️ View
                      </button>
                      <button
                        type="button"
                        onClick={() => handleGrant(req.email, 'suggest', req.name, req.org)}
                        style={{ padding: '.25rem .6rem', fontSize: '.74rem', fontWeight: 700, background: '#e0f2fe', border: '1px solid #7dd3fc', color: '#0369a1', borderRadius: '4px', cursor: 'pointer' }}
                      >
                        ✍️ Suggest
                      </button>
                      <button
                        type="button"
                        onClick={() => handleGrant(req.email, 'edit', req.name, req.org)}
                        style={{ padding: '.25rem .6rem', fontSize: '.74rem', fontWeight: 700, background: '#dcfce7', border: '1px solid #86efac', color: '#15803d', borderRadius: '4px', cursor: 'pointer' }}
                      >
                        🛠️ Edit
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Quick Direct Grant by Email Form */}
          <div style={{ background: '#f8faf9', border: '1px solid #cce5d5', borderRadius: '8px', padding: '1rem', marginBottom: '1.5rem' }}>
            <h4 style={{ margin: '0 0 .5rem', color: '#0f4028', fontSize: '.9rem' }}>
              ➕ Directly Grant Access to Email
            </h4>
            <form onSubmit={handleManualAdd} style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr 1fr auto', gap: '.65rem', alignItems: 'flex-end' }}>
              <div>
                <label style={{ display: 'block', fontSize: '.72rem', fontWeight: 700, color: '#133e2b' }}>Email</label>
                <input
                  type="email"
                  placeholder="colleague@institution.org"
                  value={manualEmail}
                  onChange={(e) => setManualEmail(e.target.value)}
                  required
                  style={{ width: '100%', padding: '.4rem .6rem', fontSize: '.82rem', borderRadius: '5px', border: '1px solid #cbd5e1', boxSizing: 'border-box' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '.72rem', fontWeight: 700, color: '#133e2b' }}>Name / Role</label>
                <input
                  type="text"
                  placeholder="e.g. Agronomist"
                  value={manualName}
                  onChange={(e) => setManualName(e.target.value)}
                  style={{ width: '100%', padding: '.4rem .6rem', fontSize: '.82rem', borderRadius: '5px', border: '1px solid #cbd5e1', boxSizing: 'border-box' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '.72rem', fontWeight: 700, color: '#133e2b' }}>Assign Role</label>
                <select
                  value={manualRole}
                  onChange={(e) => setManualRole(e.target.value)}
                  style={{ width: '100%', padding: '.4rem .6rem', fontSize: '.82rem', borderRadius: '5px', border: '1px solid #cbd5e1', background: '#fff', boxSizing: 'border-box' }}
                >
                  <option value="view">👁️ View</option>
                  <option value="suggest">✍️ Suggest</option>
                  <option value="edit">🛠️ Edit</option>
                </select>
              </div>
              <button
                type="submit"
                style={{ padding: '.45rem .85rem', background: '#0f4028', color: '#fff', border: 'none', borderRadius: '5px', fontSize: '.8rem', fontWeight: 700, cursor: 'pointer' }}
              >
                Grant
              </button>
            </form>
          </div>

          {/* Approved Users Registry Table */}
          <div>
            <h4 style={{ margin: '0 0 .5rem', color: '#0f4028', fontSize: '.9rem' }}>
              👥 Approved Users Registry ({Object.keys(registry).length})
            </h4>
            <div className="table-container" style={{ maxHeight: '220px', overflowY: 'auto' }}>
              <table className="data-table" style={{ fontSize: '.78rem' }}>
                <thead>
                  <tr style={{ background: '#eaf4ee', position: 'sticky', top: 0 }}>
                    <th>Email Address</th>
                    <th>User / Name</th>
                    <th>Active Role</th>
                    <th>Approved</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(registry).map(([em, u]) => (
                    <tr key={em}>
                      <td><strong>{em}</strong></td>
                      <td>{u.name || '—'}</td>
                      <td>
                        <span style={{
                          padding: '.15rem .45rem',
                          borderRadius: '4px',
                          fontSize: '.72rem',
                          fontWeight: 800,
                          background: ROLE_CONFIG[u.role]?.badgeBg || '#eee',
                          color: ROLE_CONFIG[u.role]?.badgeColor || '#333',
                        }}>
                          {u.role.toUpperCase()}
                        </span>
                      </td>
                      <td style={{ color: '#64748b' }}>{u.approvedAt || 'Active'}</td>
                      <td>
                        {em !== 'powellmponel@gmail.com' ? (
                          <button
                            type="button"
                            onClick={() => handleRevoke(em)}
                            style={{ background: 'none', border: 'none', color: '#b91c1c', fontSize: '.72rem', fontWeight: 700, cursor: 'pointer' }}
                          >
                            Revoke
                          </button>
                        ) : (
                          <span style={{ fontSize: '.72rem', color: '#166534', fontWeight: 700 }}>Primary Admin</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
