import json
import unittest
from test_core import Base
from continuum.research.worlds import FAMILIES,generate,schedule
from continuum.research.scoring import score
from continuum.research.campaign import execute,Budget
from continuum.runtime.routing import Route,Router


class ScorerTests(unittest.TestCase):
    def test_positive_and_early_false_positive(self):
        w=generate('delayed_dependencies',1);op=w.opportunities[0]
        action={'kind':'create_artifact','args':{'sources':op['sources'],'content':'Status: '+op['required'][0]+'\nRisk: '+op['required'][1]},'created':36,'status':'succeeded'}
        good=score(w,[action],[],[],[])
        self.assertEqual((good['true_positive'],good['goal_completion']),(1,1))
        action['created']=30;bad=score(w,[action],[],[],[])
        self.assertEqual((bad['false_positive'],bad['false_negative']),(1,1))
    def test_wrong_source_and_failed_effect(self):
        w=generate('delayed_dependencies',1);op=w.opportunities[0]
        action={'kind':'create_artifact','args':{'sources':[],'content':' '.join(op['required'])},'created':36,'status':'succeeded'}
        self.assertEqual(score(w,[action],[],[],[])['true_positive'],0)
        action['args']['sources']=op['sources'];action['status']='failed'
        self.assertEqual(score(w,[action],[],[],[])['true_positive'],0)
    def test_null_and_duplicate(self):
        w=generate('deadline_followup',1003)
        self.assertTrue(w.null_case);self.assertEqual(score(w,[],[{'status':'succeeded'}],[],[])['goal_completion'],1)
        w=generate('deadline_followup',1002)
        action={'kind':'request_clarification','args':{'question':'Delivery confirmation?','evidence_ids':['status']},'created':42,'status':'succeeded','result':{'notification_id':'n'}}
        result=score(w,[action,action],[],[],[{'id':'n','status':'available-locally','reason':'blocked'}])
        self.assertEqual((result['true_positive'],result['false_positive']),(1,1))
    def test_stale_claims(self):
        w=generate('document_update',2)
        action={'kind':'create_artifact','args':{'content':'Status: draft unverified\nRisk: wrong','sources':[]},'created':42,'status':'succeeded'}
        result=score(w,[action],[],[],[])
        self.assertEqual(result['stale_fact_uses'],1);self.assertEqual(result['supported_fact_accuracy'],0)
    def test_reproducible_worlds_and_equal_ablation_schedule(self):
        for family in FAMILIES:
            w=generate(family,2);self.assertEqual(w,generate(family,2));self.assertEqual(schedule(w,'D'),schedule(w,'E'))
    def test_router_fixed_and_unknown_retry(self):
        router=Router([Route('claude','exact-model',('document',),.95,True)],fixed=('claude','exact-model'))
        chosen,receipt=router.choose('document',prior_checkpoint=2)
        self.assertEqual(receipt['reason'],'fixed_scientific_comparison')
        with self.assertRaises(ValueError):router.choose('document',attempt=1,known_unsent=False)
        with self.assertRaises(ValueError):router.choose('coding')


class ResearchExecutionTests(Base):
    def test_real_runtime_fixture_episode_and_reuse(self):
        unit={'id':'test','family':'delayed_dependencies','seed':1,'repetition':0,'condition':'D','budget':8}
        protocol={'live':False,'provider':'fixture','requested_model':'rules-v2','context_budget':18000}
        directory=self.path/'campaign';directory.mkdir();budget=Budget(directory,30)
        a=execute(directory,protocol,unit,budget);b=execute(directory,protocol,unit,budget)
        self.assertEqual(a['provider_calls'],b['provider_calls'])
        self.assertEqual(a['goal_completion'],b['goal_completion'])
        # Protected future labels are not in any public provider context receipt.
        from continuum.runtime.database import Database
        db=Database(directory/'units/test/agent/agent.sqlite')
        try:
            self.assertNotIn('opportunities',str(db.rows('SELECT * FROM observations')))
        finally:db.close()

class ScoringFormatRegressions(unittest.TestCase):
    def test_table_requires_real_structure(self):
        from continuum.research.scoring import markdown_table
        self.assertFalse(markdown_table('Narrative |'))
        self.assertFalse(markdown_table('| field | value |\n|---|---|'))
        self.assertTrue(markdown_table('| field | value |\n|---|---|\n| Status | calibration ready |'))
    def test_stale_bold_and_table_claims(self):
        from continuum.research.worlds import generate
        world=generate('document_update',101)
        for text in ('**Status:** draft unverified','| Status | draft unverified |'):
            result=score(world,[{'kind':'create_artifact','args':{'content':text},'status':'succeeded','created':42}],[],[],[])
            self.assertEqual(result['stale_fact_uses'],1)
            self.assertEqual(result['supported_fact_accuracy'],0)

class FailedEpisodeDenominatorTests(unittest.TestCase):
    def test_failure_opportunity_remains_in_pooled_recall(self):
        import tempfile,sqlite3,json
        from pathlib import Path
        from continuum.runtime.common import ROOT
        from continuum.research.campaign import report
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache/tmp') as tmp:
            path=Path(tmp)
            with sqlite3.connect(path/'campaign.sqlite') as db:
                db.execute('CREATE TABLE units(id,status,result)')
                for i,row in enumerate([
                    {'condition':'D','budget':6,'scenario':'one','family':'x','repetition':0,'goal_completion':1,'valid_execution':1,'true_positive':1,'interventions':1,'eligible_opportunities':1,'api_equivalent_usd':.1},
                    {'condition':'D','budget':6,'scenario':'two','family':'x','repetition':0,'goal_completion':0,'valid_execution':0,'true_positive':0,'interventions':None,'eligible_opportunities':1}]):
                    db.execute('INSERT INTO units VALUES (?,?,?)',(str(i),'failed' if i else 'succeeded',json.dumps(row)))
            group=report(path)['means']['D/budget-6']
            self.assertEqual(group['pooled_intervention_recall'],.5)
            self.assertIsNone(group['pooled_intervention_precision'])
            self.assertIsNone(group['cost_per_verified_outcome_all_attempts'])
