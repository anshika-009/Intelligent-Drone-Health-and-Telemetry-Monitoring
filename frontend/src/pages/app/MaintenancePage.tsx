import { useState,useEffect } from 'react';
import { ArrowRight, Plus, Wrench, X } from 'lucide-react';
import { Link, useLocation} from 'react-router-dom';
import { Eyebrow, SectionHeading, StatusPill } from '../../components/common';
import { useApp, type MaintenanceTask } from '../../store/AppStore';
// export function MaintenancePage() { const [tasks,setTasks]=useState([{component:'Motor 2',issue:'Potential bearing wear',recommendation:'Inspect motor bearing before next extended flight.',severity:'Medium',status:'Pending',created:'21 Aug 2026'}]); return <div className="page"><SectionHeading eyebrow="MAINTENANCE / ACTIONS" title="Keep the aircraft ready." copy="Convert health recommendations into accountable maintenance work." action={<button className="button" onClick={()=>setTasks([...tasks,{component:'Battery',issue:'Discharge curve review',recommendation:'Review capacity after next flight.',severity:'Low',status:'Pending',created:'Today'}])}><Plus size={15}/> Create task</button>}/><div className="maintenance-hero"><img src="/assets/images/maintenance/maintenance-workshop.webp" alt="Drone maintenance workshop"/><div><Eyebrow>RECOMMENDATION QUEUE</Eyebrow><h3>1 task needs an operator.</h3><p>The rule engine has connected a motor vibration trend to a specific inspection recommendation.</p><Link to="/app/health" className="inline-link">Review component evidence <ArrowRight size={14}/></Link></div></div><div className="maintenance-list">{tasks.map((t,i)=><div className="maintenance-row" key={i}><div className="maintenance-check"><Wrench size={17}/></div><div className="maintenance-main"><div><span>{t.component}</span><StatusPill label={t.status} tone={t.status==='Completed'?'green':'amber'}/></div><strong>{t.issue}</strong><p>{t.recommendation}</p></div><div className="maintenance-meta"><span>{t.severity}</span><small>{t.created}</small></div><button className="text-button" onClick={()=>setTasks(tasks.map((x,j)=>j===i?{...x,status:x.status==='Pending'?'In Progress':'Completed'}:x))}>{t.status==='Pending'?'Start task':t.status==='In Progress'?'Complete':'Completed'}</button></div>)}</div></div>; }
export function MaintenancePage() {
  const { tasks, addTask, updateTaskStatus } = useApp();
  const location = useLocation();
  const incoming = location.state?.prefill as Partial<MaintenanceTask> | undefined;

  const [modalOpen, setModalOpen] = useState(false);
  const [formData, setFormData] = useState({
    component: 'Motor 1',
    issue: 'Excessive vibration detected',
    recommendation: 'Perform physical rotor balance check.',
    severity: 'Medium' as MaintenanceTask['severity']
  });

  // Automatically open modal prefilled if navigated from HealthPage
  useEffect(() => {
    if (incoming) {
      setFormData({
        component: incoming.component || 'General Airframe',
        issue: incoming.issue || 'Diagnostic trigger',
        recommendation: incoming.recommendation || 'Inspect component.',
        severity: incoming.severity || 'Medium'
      });
      setModalOpen(true);
    }
  }, [incoming]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    addTask(formData);
    setModalOpen(false);
  };

  return (
    <div className="page">
      <SectionHeading 
        eyebrow="MAINTENANCE / ACTIONS" 
        title="Keep the aircraft ready." 
        copy="Convert health recommendations into accountable maintenance work." 
        action={
          <button className="button" onClick={() => setModalOpen(true)}>
            <Plus size={15}/> Create task
          </button>
        }
      />

      {/* Task Creation Modal */}
      {modalOpen && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 50, background: 'rgba(0,0,0,0.45)',
          display: 'grid', placeItems: 'center', padding: 20
        }}>
          <form 
            onSubmit={handleSubmit} 
            className="panel" 
            style={{ width: '100%', maxWidth: 480, display: 'flex', flexDirection: 'column', gap: 14 }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <strong>New Maintenance Task</strong>
              <button type="button" className="icon-button" onClick={() => setModalOpen(false)}>
                <X size={16}/>
              </button>
            </div>

            <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 12 }}>
              Component
              <input 
                value={formData.component}
                onChange={e => setFormData({ ...formData, component: e.target.value })}
                style={{ padding: '8px 10px', border: '1px solid var(--line)', background: 'var(--surface)', color: 'var(--ink)' }}
                required 
              />
            </label>

            <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 12 }}>
              Reported Issue
              <input 
                value={formData.issue}
                onChange={e => setFormData({ ...formData, issue: e.target.value })}
                style={{ padding: '8px 10px', border: '1px solid var(--line)', background: 'var(--surface)', color: 'var(--ink)' }}
                required 
              />
            </label>

            <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 12 }}>
              Recommendation
              <textarea 
                value={formData.recommendation}
                onChange={e => setFormData({ ...formData, recommendation: e.target.value })}
                rows={3}
                style={{ padding: '8px 10px', border: '1px solid var(--line)', background: 'var(--surface)', color: 'var(--ink)', resize: 'none' }}
                required 
              />
            </label>

            <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 12 }}>
              Severity
              <select 
                value={formData.severity}
                onChange={e => setFormData({ ...formData, severity: e.target.value as MaintenanceTask['severity'] })}
                style={{ padding: '8px 10px', border: '1px solid var(--line)', background: 'var(--surface)', color: 'var(--ink)' }}
              >
                <option value="Low">Low</option>
                <option value="Medium">Medium</option>
                <option value="High">High</option>
                <option value="Critical">Critical</option>
              </select>
            </label>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 10 }}>
              <button type="button" className="button ghost" onClick={() => setModalOpen(false)}>Cancel</button>
              <button type="submit" className="button">Save Task</button>
            </div>
          </form>
        </div>
      )}

      <div className="maintenance-hero">
        <img src="/assets/images/maintenance/maintenance-workshop.webp" alt="Drone maintenance workshop"/>
        <div>
          <Eyebrow>RECOMMENDATION QUEUE</Eyebrow>
          <h3>{tasks.filter(t => t.status === 'Pending').length} tasks need an operator.</h3>
          <p>The rule engine has connected active component trends to specific inspection recommendations.</p>
          <Link to="/app/health" className="inline-link">Review component evidence <ArrowRight size={14}/></Link>
        </div>
      </div>

      <div className="maintenance-list">
        {tasks.map(t => (
          <div className="maintenance-row" key={t.id}>
            <div className="maintenance-check"><Wrench size={17}/></div>
            <div className="maintenance-main">
              <div>
                <span>{t.component}</span>
                <StatusPill label={t.status} tone={t.status === 'Completed' ? 'green' : 'amber'}/>
              </div>
              <strong>{t.issue}</strong>
              <p>{t.recommendation}</p>
            </div>
            <div className="maintenance-meta">
              <span>{t.severity}</span>
              <small>{t.created}</small>
            </div>
            <button 
              className="text-button" 
              onClick={() => updateTaskStatus(t.id, t.status === 'Pending' ? 'In Progress' : 'Completed')}
            >
              {t.status === 'Pending' ? 'Start task' : t.status === 'In Progress' ? 'Complete' : 'Completed'}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}