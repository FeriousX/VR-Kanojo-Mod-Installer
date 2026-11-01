"""Presentation-only checks; transaction behavior is covered by existing GUI bridge tests."""
import copy,json,sys,unittest
from pathlib import Path
from unittest import mock
w=Path(__file__).resolve().parents[1];sys.path.insert(0,str(w/'tools'))
from gui_presentation import presentation
import test_gui_install as existing
import gui_install as gui

class PresentationTests(unittest.TestCase):
 def meta(self):
  return dict(binding='7|vrkanojo-desktop|C:/Test Game',prepared=dict(synthetic_root='C:/Test Game',operations=[dict(action=a) for a in ('create','create','replace','preserve')]))
 def test_readable_plan_counts_and_selections(self):
  p=presentation(self.meta(),'Prepared');self.assertEqual((p['files_create'],p['files_replace'],p['files_preserve'],p['files_total']),('2','1','1','4'))
  self.assertEqual(p['display_target'],'C:/Test Game');self.assertIn('FeriousX',p['display_components']);self.assertIn('XUnity',p['display_components']);self.assertIn('Message Center',p['display_components'])
 def test_all_three_modes(self):
  for mode,name in [('neither','Standard VR'),('vrkanojo-desktop','FeriousX'),('play-without-vr','ManlyMarco')]:
   m=self.meta();m['binding']='1|'+mode+'|C:/Game';self.assertIn(name,presentation(m,'Prepared')['display_components'])
 def test_verified_success_only(self):
  with self.assertRaises(ValueError):presentation(self.meta(),'Completed')
  m=self.meta();m['ui_result']=dict(backups_verified=True)
  p=presentation(m,'Completed',True);self.assertEqual(p['display_title'],'Installation completed successfully!');self.assertEqual(p['files_applied'],'3')
  self.assertIn('Backups verified',p['display_message']);self.assertNotIn('CommittedSynthetic',str(p));self.assertIn('not been automatically tested',p['display_message'])
 def test_failed_and_uncertain_never_claim_success(self):
  for state in ('Failed','RecoveryRequired'):
   p=presentation(self.meta(),state);self.assertNotIn('successfully',str(p));self.assertIn('No successful installation',p['display_message'])
 def test_noop_is_not_new_installation(self):
  m=self.meta();m['prepared']['status']='AlreadyPresent';m['prepared']['summary']='No changes required.'
  p=presentation(m,'Blocked');self.assertIn('already installed',p['display_title']);self.assertEqual(p['display_message'],'No changes required.')
 def test_conflict_reason_preserved(self):
  m=self.meta();m['prepared']['summary']='Unknown existing BepInEx.cfg; replacement blocked.'
  self.assertIn('BepInEx.cfg',presentation(m,'Blocked')['display_message'])
 def test_actual_applied_count_not_fake_percent(self):
  m=self.meta();m['ui_applied']=1;p=presentation(m,'Applying')
  self.assertEqual(p['files_applied'],'1');self.assertEqual(p['files_to_apply'],'3');self.assertNotIn('percent',p)
 def test_source_consent_and_async_guards(self):
  source=(w/'src/installer/ui-prototype/preview.iss').read_text()
  self.assertNotIn('ewWaitUntilTerminated',source);self.assertIn('PollPreparation',source);self.assertIn('PreparationProgress.Style := npbstMarquee',source)
  self.assertIn('CreateCustomForm(ScaleX(600), ScaleY(360), True, True)',source)
  self.assertIn('CreateCustomForm(ScaleX(560), ScaleY(340), True, True)',source)
  self.assertIn('CancelButton.Default := True',source);self.assertIn('CancelButton.Cancel := True',source)
  self.assertIn('Result := Form.ShowModal = mrOk',source);self.assertIn('--approve-plan ',source)
  self.assertIn('ValidatedBinding = SelectionBinding()',source);self.assertIn('ReadPresentation(IniPath, State)',source)
  self.assertIn('TechnicalBody := PlanDetails',source);self.assertIn('Files applied:',source)
  self.assertNotIn('Review your preview.',source);self.assertIn('AppVersion=1.0.0-preview.8B1',source)

class FramePresentationTests(unittest.TestCase):
 setUp=existing.GUIInstallTests.setUp
 tearDown=existing.GUIInstallTests.tearDown
 prepare=existing.GUIInstallTests.prepare
 frame=existing.GUIInstallTests.frame
 # Reuse existing actual bridge test infrastructure without inheriting its whole suite.
 def test_presentation_is_in_hashed_response(self):
  m=self.prepare();p=self.frame(m);self.assertEqual(p['display_protocol'],'1')
  self.assertEqual(int(p['files_total']),len(m['prepared']['operations']));self.assertEqual(p['display_title'],'Ready to install')
  result=gui.run_job(m['job'],m['plan_digest']);p=self.frame(m)
  self.assertEqual(p['success'],'1');self.assertEqual(p['display_title'],'Installation completed successfully!')
  self.assertEqual(result['status'],'CommittedSynthetic');self.assertIn('response_sha256',(gui.folder_for(m['job'])/'frame.ini').read_text())
 def test_failure_keeps_technical_diagnostics(self):
  m=self.prepare()
  def fail(point,index):
   if point=='after_publish' and index==1:raise OSError('presentation regression failure')
  gui.run_job(m['job'],m['plan_digest'],extra_fault=fail);p=self.frame(m)
  self.assertEqual(p['success'],'0');self.assertNotIn('successfully',p['display_title'])
  self.assertTrue(any('Recovery:' in value for value in p.values()))
