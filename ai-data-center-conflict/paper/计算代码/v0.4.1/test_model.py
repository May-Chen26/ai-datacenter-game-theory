import unittest,itertools,math,json,importlib.util,sys
from pathlib import Path
from dataclasses import replace
from model import P,solve,outcomes,scenarios,RULES,correction

def independent(T,p,rule):
 a=T if p.rho==0 else (1-math.exp(-p.rho*T))/p.rho;d=math.exp(-p.rho*T)
 v=[]
 for c in (0,1):
  row={}
  for m,n in enumerate(('continue','mitigate')):
   active=rule=='actionable';rate=((p.j1 if c else p.j0)*(1-m)+p.residual*m) if active else 0
   cost=c*p.fee+rate*a;damage=(p.h-p.reduction*m)*a
   if p.correction_enabled and active and c and T>p.correction_delay and min(p.forced_reduction,p.h-p.reduction*m)>0:
    tau=p.correction_delay;b=tau if p.rho==0 else (1-math.exp(-p.rho*tau))/p.rho
    cost+=(p.correction_cost_after if m else p.correction_cost_before)*math.exp(-p.rho*tau)
    damage-=min(p.forced_reduction,p.h-p.reduction*m)*(a-b)
   row[n]=((p.revenue-p.power-p.maintenance)*a+d*p.grid_value-p.C*m-cost,-damage-p.k*c)
  if p.pause_contract and p.pause_technical:row['pause']=(-p.stop-p.standby*a+d*(p.grid_value-p.restart)-c*p.fee,-p.k*c)
  if p.exit_allowed:row['exit']=(p.salvage-p.termination-p.cleanup-c*p.fee,-p.k*c)
  v.append(row)
 eq=[]
 for plan in itertools.product(v[0],v[1]):
  if any(v[c][plan[c]][0]<max(u[0] for u in v[c].values())-1e-9 for c in (0,1)):continue
  for c in (0,1):
   if v[c][plan[c]][1]>=v[1-c][plan[1-c]][1]-1e-9:eq.append((c,plan[c],*plan))
 return eq
class Tests(unittest.TestCase):
 def test_independent(self):
  for p,T,rule in itertools.product(scenarios().values(),(0,1,3,10,50),RULES):
   r=solve(T,p,rule);self.assertIn((r['complaint'],r['action'],r['if_silent'],r['if_complaint']),independent(T,p,rule))
 def test_cost_changes_response(self):
  p=replace(scenarios()['old_boundary'],rho=0,forced_reduction=1,correction_cost_before=1,correction_cost_after=16.9)
  self.assertEqual(solve(10,p)['if_complaint'],'mitigate')
  self.assertEqual(solve(10,replace(p,correction_cost_after=17))['if_complaint'],'continue')
  self.assertEqual(solve(10,replace(p,correction_cost_after=17.1))['if_complaint'],'continue')
 def test_synchronized(self):
  p=replace(P(),forced_reduction=1)
  for m in (0,1):
   on,cost,benefit=correction(10,1,m,p,'actionable');self.assertTrue(on);self.assertGreater(cost,0);self.assertGreater(benefit,0)
   for c,rule in [(0,'actionable')]+[(1,r) for r in RULES[1:]]:self.assertEqual(correction(10,c,m,p,rule),(False,0,0))
  self.assertEqual(correction(10,1,1,replace(p,forced_reduction=0), 'actionable'),(False,0,0))
 def test_timing(self):
  p=replace(P(),forced_reduction=1,correction_delay=10)
  for T in (0,9,10):self.assertEqual(correction(T,1,0,p,'actionable'),(False,0,0))
  _,cost,b=correction(11,1,0,p,'actionable');self.assertAlmostEqual(cost,math.exp(-.3));self.assertGreater(b,0)
 def test_m_pause_tie(self):
  p=replace(P(),rho=0,revenue=0,power=0,maintenance=0,grid_value=0,fee=0,j0=10,j1=10,C=4,stop=4,restart=0,standby=0,exit_allowed=False)
  self.assertEqual(outcomes(1,0,p)['mitigate'][0],outcomes(1,0,p)['pause'][0])
  self.assertEqual(solve(1,p)['if_silent'],'mitigate')
 def test_feasibility(self):
  p=scenarios()['pause_option'];self.assertEqual(solve(10,p)['action'],'pause')
  for kw in ({'pause_contract':False},{'pause_technical':False}):self.assertNotIn('pause',outcomes(10,0,replace(p,**kw)))
  self.assertNotIn('exit',outcomes(10,0,replace(p,exit_allowed=False)))
  self.assertEqual(solve(10,replace(p,salvage=100))['action'],'exit')
 def test_legacy(self):
  f=Path(__file__).parent.parent/'v0.4/model.py';sp=importlib.util.spec_from_file_location('legacy',f);old=importlib.util.module_from_spec(sp);sys.modules['legacy']=old;sp.loader.exec_module(old)
  for T,rho,rule in itertools.product((0,1,2,3,10,20,50),(0,.03),RULES):
   p=replace(P(),rho=rho,forced_reduction=0);o=old.solve(T,old.P(rho=rho),rule);r=solve(T,p,rule)
   self.assertEqual((r['complaint'],r['action']),(o['complaint'],o['action']));self.assertAlmostEqual(r['D'],o['D']);self.assertAlmostEqual(r['N'],o['N'])
 def test_disabled(self):
  p=replace(P(),forced_reduction=1,correction_enabled=False)
  self.assertEqual(outcomes(10,1,p),outcomes(10,1,replace(p,forced_reduction=0)))
 def test_zero_and_ties(self):
  p=replace(P(),rho=0,grid_value=0,stop=0,restart=0,termination=0)
  self.assertEqual((solve(0,p)['action'],solve(0,p)['complaint']),('continue',0))
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
 Path(__file__).with_name('test_results.json').write_text(json.dumps(dict(tests=r.testsRun,failures=len(r.failures),errors=len(r.errors),independent_cases=150,legacy_comparisons=70),indent=2));raise SystemExit(not r.wasSuccessful())
