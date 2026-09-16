import { useLocation, Link } from 'react-router-dom';
import { LockKeyhole, Radio, ShieldCheck, Loader2 } from 'lucide-react';
import { Brand, Eyebrow } from '../../components/common';
import { SignIn, SignUp, ClerkLoaded, ClerkLoading } from '@clerk/react';

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
        <div className="auth-form" style={{ minHeight: '450px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <ClerkLoading>
            <div style={{ textAlign: 'center', color: '#687680', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '15px' }}>
              <Loader2 size={32} className="spin-anim" />
              <div>
                <p style={{ margin: 0, fontWeight: 500, color: '#1b2530' }}>Loading secure connection...</p>
                <p style={{ fontSize: '13px', margin: '8px 0 0 0' }}>If this takes too long, check if an ad-blocker is blocking Clerk.</p>
              </div>
            </div>
          </ClerkLoading>
          
          <ClerkLoaded>
            {mode === 'login' ? (
              <SignIn routing="path" path="/login" signUpUrl="/register" fallbackRedirectUrl="/app/dashboard" />
              ) : (
              <SignUp routing="path" path="/register" signInUrl="/login" fallbackRedirectUrl="/app/dashboard" />
            )}
          </ClerkLoaded>
        </div>
        <Link className="back-home" to={(location.state as { from?: string } | null)?.from || '/'}>← Back to IDHTM</Link>
      </div>
    </div>
  );
}