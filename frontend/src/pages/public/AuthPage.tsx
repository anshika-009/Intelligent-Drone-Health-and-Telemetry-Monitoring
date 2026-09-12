import { useLocation, Link } from 'react-router-dom';
import { LockKeyhole, Radio, ShieldCheck } from 'lucide-react';
import { Brand, Eyebrow } from '../../components/common';
import { SignIn, SignUp } from '@clerk/react';

export function AuthPage({ mode }: { mode: 'login' | 'register' }) {
  const location = useLocation();
  return (
    <div className="auth-page">
      <div className="auth-visual">
        <div className="auth-visual-image" />
        <div className="auth-visual-copy">
          <Eyebrow>FLIGHT OPERATIONS / IDHTM</Eyebrow>
          <h1>Understand the aircraft behind the data.</h1>
          <p>One disciplined operating picture for the people responsible for every flight.</p>
          <div className="auth-proof">
            <span><Radio size={15} /> Simulator ready</span>
            <span><ShieldCheck size={15} /> Explainable rules</span>
            <span><LockKeyhole size={15} /> Protected workspace</span>
          </div>
        </div>
      </div>
      <div className="auth-panel">
        <Brand />
        <div className="auth-form">
          {mode === 'login' ? (
            <SignIn routing="path" path="/login" signUpUrl="/register" fallbackRedirectUrl="/app/dashboard" />
            ) : (
            <SignUp routing="path" path="/register" signInUrl="/login" fallbackRedirectUrl="/app/dashboard" />
          )}
        </div>
        <Link className="back-home" to={(location.state as { from?: string } | null)?.from || '/'}>← Back to IDHTM</Link>
      </div>
    </div>
  );
}