import json
import subprocess
import sys
import threading
import time
import unittest
from urllib.error import HTTPError
import urllib.request
from test_core import Base
from continuum.runtime.contracts import empty_proposal,validate,PROPOSAL
from continuum.runtime.providers import CLIProvider,FixtureProvider,ProviderError,Response
from continuum.runtime.web import Dashboard
from continuum.runtime.common import canonical


class ReviewRegressions(Base):
    def test_stop_survives_unknown_provider_outcome(self):
        class Stop(FixtureProvider):
            def propose(inner,*args):
                r.control('stopped');raise ProviderError('cancelled','outcome-unknown')
        r=self.runtime(Stop());r.goal('Goal');r.tick();self.assertEqual(r.db.get('control'),'stopped')
    def test_forget_same_topic_and_cached_source(self):
        r=self.runtime();mid=r.memory.add('fact','x','CANARY',100,['owner'],confirmed=True)
        r.notifications.offer('CANARY one','g','reply',[],100,reply=True)
        r.notifications.offer('CANARY two','g','reply',[],101,reply=True)
        r.memory.forget(mid);self.assertNotIn('CANARY',canonical(r.status()))
        self.assertEqual(r.db.get('retention_generation'),1)
    def test_historical_message_not_reply_exemption(self):
        r=self.runtime();r.observe('user.message',{'text':'old'},event_id='old')
        p=empty_proposal();p['message']={'text':'Unsolicited old reply','reason':'reply','topic':'g','evidence_ids':['old']}
        r.apply(p,r.context(100),'t',100,reply_ids=set())
        self.assertEqual(r.db.rows('SELECT suppressed_reason FROM outbox')[0]['suppressed_reason'],'no_usefulness_criterion')
    def test_nonfinite_proposal_denied(self):
        for val in (float('nan'),float('inf')):
            p=empty_proposal();p['next_delay']=val
            with self.assertRaises(ValueError):validate(PROPOSAL,p)
    def test_derived_events_affect_state(self):
        r=self.runtime();r.db.event('memory.conflict',{});r.tick()
        self.assertGreater(r.db.get('state')['uncertainty'],0)
    def test_newest_document_version_wins(self):
        r=self.runtime();r.goal('Brief',goal_id='g');file=self.docs/'a.md';file.write_text('old')
        r.observe('document.available',{'path':'a.md'},event_id='old-doc');r.tick()
        file.write_text('new');r.observe('document.available',{'path':'a.md'},event_id='new-doc')
        context=r.context(100);self.assertNotIn('content',context['documents'][0])
        oid=r.capabilities.queue({'capability':'read_document','args':{'path':'a.md'}},'new-trace',100)
        r.capabilities.execute(oid,100,r.evidence(context))
        self.assertEqual(r.context(100)['documents'][0]['content'],'new')
    def test_private_fact_api_and_forged_control(self):
        r=self.runtime();web=Dashboard(r,port=0);t=threading.Thread(target=web.serve);t.start()
        self.addCleanup(lambda:(web.close(),t.join(2)))
        url=f'http://127.0.0.1:{web.server.server_port}'
        def request(body,token=None,origin=None):
            req=urllib.request.Request(url+'/api/fact',json.dumps(body).encode(),headers={'Authorization':'Bearer '+(token or web.token),'Origin':origin or url,'Content-Type':'application/json'})
            return urllib.request.urlopen(req,timeout=2)
        with request({'subject':'private','content':'PRIVATE_CANARY','private':True}) as response:self.assertEqual(response.status,200)
        self.assertNotIn('PRIVATE_CANARY',canonical(r.context(100)))
        for token,origin in [('wrong',url),(web.token,'http://attacker.invalid')]:
            with self.assertRaises(HTTPError) as err:request({'subject':'x','content':'x'},token,origin)
            self.assertEqual(err.exception.code,403)
    def test_blocked_stdin_deadline(self):
        provider=CLIProvider('claude','test-model',self.path/'provider',timeout=.1)
        proc=subprocess.Popen([sys.executable,'-c','import time; time.sleep(2)'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        start=time.monotonic()
        try:
            with self.assertRaises(ProviderError):list(provider.lines(proc,'x'*1000000,threading.Event()))
            self.assertLess(time.monotonic()-start,.7)
        finally:
            provider.terminate(proc)
            for stream in (proc.stdin,proc.stdout,proc.stderr):stream.close()
    def test_output_bound_and_eof(self):
        provider=CLIProvider('claude','test-model',self.path/'provider',max_bytes=10)
        for payload,expected in [('12345',False),('x'*100,True)]:
            proc=subprocess.Popen([sys.executable,'-c',f'import sys; sys.stdout.write({payload!r})'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
            try:
                if expected:
                    with self.assertRaises(ProviderError):list(provider.lines(proc,'',threading.Event()))
                else:self.assertEqual(list(provider.lines(proc,'',threading.Event())),[('stdout',b'12345')])
            finally:
                provider.terminate(proc)
                for stream in (proc.stdin,proc.stdout,proc.stderr):
                    if not stream.closed:stream.close()
    def test_codex_fails_closed_before_inference(self):
        p=CLIProvider('codex','gpt-6-luna',self.path/'provider')
        with self.assertRaises(ProviderError) as e:p.propose({},threading.Event(),lambda e:None)
        self.assertTrue(e.exception.known_unsent)

class CheckpointRegressions(Base):
    def test_completed_activation_not_recalled(self):
        r=self.runtime(schedule=[100]);r.goal('Goal');r.tick()
        before=len(r.db.rows('SELECT * FROM calls'));r.tick()
        self.assertEqual(len(r.db.rows('SELECT * FROM calls')),before)
    def test_interrupted_call_recovery_pauses(self):
        r=self.runtime();r.goal('Goal')
        with r.db.transaction() as tx:tx.execute("INSERT INTO calls VALUES ('lost','fixture','rules-v2',NULL,'running','hash',NULL,NULL,NULL,NULL,100)")
        r.close();from continuum.runtime.engine import Runtime
        second=Runtime(self.path/'run',FixtureProvider(),clock=self.clock,fixtures=self.docs);self.addCleanup(second.close)
        self.assertEqual(second.db.get('control'),'paused')
    def test_tool_receipt_wakes_waiting_goal(self):
        r=self.runtime(schedule=[100,106]);r.goal('Goal',goal_id='g')
        with r.db.transaction() as tx:tx.execute("UPDATE goals SET status='waiting-for-input'")
        (self.docs/'a.md').write_text('Status: calibration ready\nRisk: field evidence missing')
        r.observe('document.available',{'path':'a.md'},event_id='source');r.tick()
        self.clock.advance(106);r.tick()
        self.assertTrue(r.db.rows('SELECT * FROM artifacts'))
    def test_database_write_failure_is_not_success(self):
        r=self.runtime();r.db.db.execute('PRAGMA query_only=ON')
        import sqlite3
        with self.assertRaises(sqlite3.OperationalError):r.observe('user.message',{'text':'not persisted'})
        r.db.db.execute('PRAGMA query_only=OFF')
        self.assertEqual(r.db.rows('SELECT * FROM observations'),[])

class FinalAdapterRegressions(Base):
    def test_subscription_checked_before_inference(self):
        from unittest.mock import patch
        p=CLIProvider('claude','test-model',self.path/'provider')
        with patch.object(p,'auth',side_effect=ProviderError('subscription required',known_unsent=True)),patch.object(p,'_propose') as inference:
            with self.assertRaises(ProviderError) as caught:p.propose({},threading.Event(),lambda e:None)
            self.assertTrue(caught.exception.known_unsent);inference.assert_not_called()
    def test_per_model_usage_without_primary_usage(self):
        from unittest.mock import patch
        p=CLIProvider('claude','test-model',self.path/'provider')
        events=[{'type':'system','subtype':'init','model':'test-model','tools':['StructuredOutput']},
                {'type':'assistant','message':{'model':'test-model','content':[]}},
                {'type':'result','structured_output':empty_proposal(),'modelUsage':{'test-model':{'inputTokens':2,'outputTokens':3,'cacheReadInputTokens':4,'cacheCreationInputTokens':5,'costUSD':.01}}}]
        proc=subprocess.Popen([sys.executable,'-c','pass'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        def stream(*args):
            p.output_bytes=1
            yield from [('stdout',json.dumps(e).encode()) for e in events]
        with patch('continuum.runtime.providers.subprocess.Popen',return_value=proc),patch.object(p,'lines',side_effect=stream):
            result=p._propose({},threading.Event(),lambda e:None)
        self.assertEqual(result.usage['output'],3);self.assertEqual(result.usage['cached_read'],4)
        self.assertIsNone(result.usage['primary_usage']['output'])
    def test_cleanup_permission_error_does_not_mask_result(self):
        from unittest.mock import patch,MagicMock
        proc=MagicMock();proc.pid=999999
        with patch('continuum.runtime.providers.os.killpg',side_effect=PermissionError(1,'mock denial')):
            warnings=CLIProvider.terminate(proc)
        self.assertEqual(len(warnings),2)
    def test_forget_duplicate_assertion_and_purged_read(self):
        r=self.runtime();r.goal('Brief',goal_id='g')
        (self.docs/'a.md').write_text('CANARY')
        r.observe('document.available',{'path':'a.md'},event_id='source');r.tick()
        a=r.memory.add('fact','x','CANARY',100,['owner'],confirmed=True)
        r.memory.add('fact','another','CANARY',100,['source'],confirmed=True)
        r.memory.forget(a)
        self.assertNotIn('CANARY',canonical(r.context(100)))
        self.assertEqual(r.memory.retrieve('CANARY',100),[])

class FinalBoundaryRegressions(Base):
    def test_repository_and_goal_bounds(self):
        from continuum.runtime.engine import Runtime
        with self.assertRaises(ValueError):Runtime(self.path/'run',FixtureProvider(),fixtures=__import__('pathlib').Path('/'))
        r=self.runtime()
        for title,deadline in [('',None),('x',float('nan')),('x',float('inf'))]:
            with self.assertRaises(ValueError):r.goal(title,deadline)
    def test_secrets_not_persisted_in_goal_proposal_or_effect(self):
        secret='sk-'+'Z'*24
        class Secret(FixtureProvider):
            def propose(inner,*args):
                p=empty_proposal();p['summary']=secret;p['message']={'text':secret,'topic':secret,'reason':'reply','evidence_ids':[]}
                return Response(p,'fixture',None,0,1)
        r=self.runtime(Secret());r.goal(secret);r.tick()
        dump='\n'.join(r.db.db.iterdump())
        self.assertNotIn(secret,dump)
    def test_auth_cache_has_finite_revalidation(self):
        from unittest.mock import patch,MagicMock
        p=CLIProvider('claude','test-model',self.path/'provider');p._subscription_verified_at=0
        with patch.object(p,'auth',side_effect=ProviderError('revoked',known_unsent=True)),patch('continuum.runtime.providers.time.monotonic',return_value=61):
            with self.assertRaises(ProviderError):p.propose({},threading.Event(),lambda e:None)

class ScheduleIsolationRegressions(Base):
    def test_explicit_schedule_not_changed_by_model_waiting(self):
        r=self.runtime(schedule=[100,106]);r.goal('Goal');r.tick()
        with r.db.transaction() as tx:tx.execute("UPDATE goals SET status='waiting-for-input'")
        self.clock.advance(106);r.tick()
        self.assertEqual(len(r.db.rows('SELECT * FROM calls')),2)
    def test_explicit_schedule_not_changed_by_goal_completion(self):
        r=self.runtime(schedule=[100,106]);r.goal('Goal');r.tick()
        with r.db.transaction() as tx:tx.execute("UPDATE goals SET status='succeeded'")
        self.clock.advance(106);r.tick()
        self.assertEqual(len(r.db.rows('SELECT * FROM calls')),2)

class RecoveryAndStressRegressions(Base):
    def test_persisted_proposal_restarts_without_duplicate_artifact(self):
        from continuum.runtime.engine import Runtime
        r=self.runtime();r.goal('Goal',goal_id='g');r.observe('status',{'text':'Public evidence'},event_id='source')
        p=empty_proposal();p['actions']=[{'capability':'create_artifact','args':{'path':'brief.md','content':'Evidence-backed brief','sources':['source'],'goal_id':'g'}}]
        r.db.set('pending_proposal',{'proposal':p,'context':r.context(100),'trace':'saved','at':100,'epoch':r.db.get('epoch'),'reply_ids':[]})
        r.close();second=Runtime(self.path/'run',FixtureProvider(),clock=self.clock,fixtures=self.docs);self.addCleanup(second.close)
        second.tick();self.clock.advance(160);second.tick()
        self.assertEqual(len(second.db.rows('SELECT * FROM artifacts')),1)
        self.assertEqual(len(second.db.rows("SELECT * FROM operations WHERE kind='create_artifact'")),1)
        self.assertIsNone(second.db.get('pending_proposal'))
    def test_context_compression_records_exclusions(self):
        r=self.runtime(context_budget=7000);r.goal('Goal')
        for i in range(8):r.observe('distractor',{'text':'noise '*1000},event_id=str(i))
        context=r.context(100)
        self.assertLessEqual(len(canonical(context)),7000)
        events=r.db.rows("SELECT data FROM events WHERE kind='context.selected'")
        self.assertTrue(json.loads(events[-1]['data'])['payload']['excluded'])
    def test_wall_clock_restart_clamps_forward_and_backward(self):
        from unittest.mock import patch
        from continuum.runtime.common import WallClock
        for previous,wall,gap in [(100,90,0),(100,1000000,86400),(100,110,10)]:
            with patch('continuum.runtime.common.time.time',return_value=wall),patch('continuum.runtime.common.time.monotonic',return_value=42):
                clock=WallClock(previous);self.assertEqual(clock.gap,gap);self.assertEqual(clock.now(),previous+gap)
    def test_artifact_disk_failure_is_audited(self):
        from unittest.mock import patch
        r=self.runtime();r.goal('Goal',goal_id='g');r.observe('status',{'text':'Evidence'},event_id='source')
        oid=r.capabilities.queue({'capability':'create_artifact','args':{'path':'brief.md','content':'Brief','sources':['source'],'goal_id':'g'}},'t',100)
        with patch('continuum.runtime.capabilities.os.open',side_effect=OSError('simulated disk full')):r.capabilities.execute(oid,100,{'source'})
        self.assertEqual(r.db.rows('SELECT status FROM operations')[0]['status'],'failed')
        self.assertEqual(r.db.rows('SELECT * FROM artifacts'),[])
    def test_invalid_provider_stream_object(self):
        from unittest.mock import patch
        p=CLIProvider('claude','test-model',self.path/'provider')
        proc=subprocess.Popen([sys.executable,'-c','pass'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        with patch('continuum.runtime.providers.subprocess.Popen',return_value=proc),patch.object(p,'lines',return_value=iter([('stdout',b'[]')])):
            with self.assertRaises(ProviderError):p._propose({},threading.Event(),lambda e:None)
