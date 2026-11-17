from dataclasses import dataclass,replace
from math import exp,expm1
from pathlib import Path
import csv
@dataclass(frozen=True)
class P:
 rho:float=.03
 C:float=4
 k:float=1
 j0:float=.2
 j1:float=2
 residual:float=0
 h:float=3
 reduction:float=2.5
 fee:float=.2
 revenue:float=2
 power:float=1
 maintenance:float=.2
 grid_value:float=10
 pause_contract:bool=True
 pause_technical:bool=True
 exit_allowed:bool=True
 stop:float=1
 restart:float=1
 standby:float=.2
 salvage:float=0
 termination:float=1
 cleanup:float=0
 forced_reduction:float=0
 correction_delay:float=1
 correction_enabled:bool=True
 correction_cost_before:float=1
 correction_cost_after:float=1
RULES=('actionable','no_duty','invalid_evidence','valid_compliant','no_authority')
ORDER=('continue','mitigate','pause','exit')
def A(T,r):
 if T<0 or r<0:raise ValueError('negative time/rate')
 return T if r==0 else -expm1(-r*T)/r

def correction(T,c,m,p,rule):
 # One technical action at tau; no action at/after grid arrival.
 reduction=min(p.forced_reduction,p.h-p.reduction*m)
 trigger=p.correction_enabled and rule=='actionable' and c==1 and T>p.correction_delay and reduction>0
 if not trigger:return (False,0.0,0.0)
 cost=[p.correction_cost_before,p.correction_cost_after][m]*exp(-p.rho*p.correction_delay)
 benefit=reduction*(A(T,p.rho)-A(p.correction_delay,p.rho))
 return (True,cost,benefit)

def outcomes(T,c,p=P(),rule='actionable'):
 if rule not in RULES:raise ValueError(rule)
 a=A(T,p.rho);disc=exp(-p.rho*T);active=rule=='actionable'
 pi=(p.revenue-p.power-p.maintenance)*a+disc*p.grid_value
 tail=max(0,a-A(min(T,p.correction_delay),p.rho))
 out={}
 for name,m in [('continue',0),('mitigate',1)]:
  J=c*p.fee+(((p.j1 if c else p.j0)*(1-m)+p.residual*m)*a if active else 0)
  H=(p.h-p.reduction*m)*a
  _,technical_cost,benefit=correction(T,c,m,p,rule)
  J+=technical_cost
  H-=benefit
  out[name]=(pi-p.C*m-J,-H-p.k*c)
 if p.pause_contract and p.pause_technical:
  out['pause']=(-p.stop-p.standby*a+disc*(p.grid_value-p.restart)-c*p.fee,-p.k*c)
 if p.exit_allowed:
  out['exit']=(p.salvage-p.termination-p.cleanup-c*p.fee,-p.k*c)
 return out

def solve(T,p=P(),rule='actionable'):
 branches=[outcomes(T,c,p,rule) for c in (0,1)]
 best=[max(b,key=lambda x:b[x][0]) for b in branches] # insertion order breaks ties
 c=int(branches[1][best[1]][1]>branches[0][best[0]][1])
 action=best[c];u=branches[c][action]
 return dict(T=T,rule=rule,complaint=c,action=action,if_silent=best[0],if_complaint=best[1],D=u[0],N=u[1],status='Assumed')

def scenarios():
 base=P(pause_contract=False,exit_allowed=False,revenue=0,power=0,maintenance=0,grid_value=0)
 return {'old_boundary':base,'outside_choices':replace(base,pause_contract=True,salvage=0,exit_allowed=True), 'pause_option':P(revenue=.1,power=1,maintenance=.2,termination=20), 'forced_effect':replace(base,forced_reduction=1), 'high_after_cost':replace(base,forced_reduction=1,correction_cost_after=30), 'high_exit_value':P(salvage=30)}
if __name__=='__main__':
 rows=[]
 for name,p in scenarios().items():
  for T in (0,1,2,3,10,20,31,50):rows.append(dict(scenario=name,**solve(T,p)))
 root=Path(__file__).parent
 with (root/'scenarios.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 lines=['# v0.4.1策略表（Assumed）','','|情景|T|投诉|D选择|沉默后D|投诉后D|','|---|---:|---:|---|---|---|']
 for r in rows:lines.append('|'+ '|'.join(str(r[k]) for k in ('scenario','T','complaint','action','if_silent','if_complaint'))+'|')
 (root/'策略表.md').write_text('\n'.join(lines)+'\n');print('saved',len(rows),'scenarios')
