import { scenarioDescriptions, scenarioLabels } from '../../../data/mock';
import type { Scenario } from '../../../types';

export function ScenarioPicker({value,onChange}:{value:Scenario;onChange:(s:Scenario)=>void}) { return <div className="scenario-picker"><div><strong>Choose a telemetry scenario</strong><span>Scenario changes flow through the same health and alert pipeline.</span></div><div className="scenario-options">{(Object.keys(scenarioLabels) as Scenario[]).map(s=><button key={s} className={value===s?'selected':''} onClick={()=>onChange(s)}><span>{scenarioLabels[s]}</span><small>{scenarioDescriptions[s]}</small></button>)}</div></div>; }
