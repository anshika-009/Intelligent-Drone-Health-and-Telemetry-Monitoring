import { FormEvent, useState } from 'react';
import { ArrowRight, Check, LockKeyhole, Radio, ShieldCheck } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Brand, Eyebrow } from '../../components/common';
import { authService } from '../../services/api';
import { useApp } from '../../store/AppStore';

export function AuthPage({ mode }: { mode: 'login' | 'register' }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { signIn } = useApp();
  const [email, setEmail] = useState('operator@idhtm.dev');
  const [password, setPassword] = useState('demo-flight');
  const [name, setName] = useState('Alex Morgan');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [ready, setReady] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    setLoading(true);
    if (!email || password.length < 6) { setError('Enter a valid email and a password with at least 6 characters.'); setLoading(false); return; }
    try {
      const result = mode === 'login' ? await authService.login(email, password) : await authService.register(email, password, name);
      signIn(result.user.email, result.user.name);
    } catch {
      // Demo mode remains usable when the local API is not running.
      signIn(email, name);
    }
    setLoading(false);
    setReady(true);
    window.setTimeout(() => navigate('/app/dashboard'), 1600);
  };

  if (ready) return <div className="system-online"><div className="system-ring"><Check size={28}/></div><Eyebrow>AUTHENTICATED</Eyebrow><h1>IDHTM system online</h1><div className="system-sequence"><span>DRONE-01 CONNECTED</span><span>HEALTH CHECK <Check size={13}/></span><span>MONITORING ACTIVE</span></div></div>;
  return <div className="auth-page"><div className="auth-visual"><div className="auth-visual-image"/><div className="auth-visual-copy"><Eyebrow>FLIGHT OPERATIONS / IDHTM</Eyebrow><h1>Understand the aircraft behind the data.</h1><p>One disciplined operating picture for the people responsible for every flight.</p><div className="auth-proof"><span><Radio size={15}/> Simulator ready</span><span><ShieldCheck size={15}/> Explainable rules</span><span><LockKeyhole size={15}/> Protected workspace</span></div></div></div><div className="auth-panel"><Brand/><div className="auth-form"><Eyebrow>{mode === 'login' ? 'RETURNING OPERATOR' : 'CREATE OPERATOR ACCESS'}</Eyebrow><h2>{mode === 'login' ? 'Welcome back.' : 'Open your flight desk.'}</h2><p>{mode === 'login' ? 'Resume monitoring with your saved operational context.' : 'Start with a simulator or connect a compatible flight source later.'}</p><form onSubmit={submit}>{mode === 'register' && <label>Full name<input value={name} onChange={e => setName(e.target.value)} placeholder="Alex Morgan"/></label>}<label>Work email<input value={email} onChange={e => setEmail(e.target.value)} type="email" placeholder="operator@company.com"/></label><label>Password<input value={password} onChange={e => setPassword(e.target.value)} type="password" placeholder="Minimum 6 characters"/></label>{error && <div className="form-error">{error}</div>}<button className="button full" disabled={loading}>{loading ? 'Initializing system…' : mode === 'login' ? 'Authenticate' : 'Create operator access'}<ArrowRight size={16}/></button></form><div className="auth-switch">{mode === 'login' ? <>New to IDHTM? <Link to="/register">Create access</Link></> : <>Already have access? <Link to="/login">Sign in</Link></>}</div><div className="auth-note">Demo access is available with any valid email and a six-character password. No hardware connection is implied.</div></div><Link className="back-home" to={(location.state as { from?: string } | null)?.from || '/'}>← Back to IDHTM</Link></div></div>;
}
