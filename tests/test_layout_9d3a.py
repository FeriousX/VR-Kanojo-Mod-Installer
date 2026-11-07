"""Static UI contract and scaled-bound checks; no installer/GUI execution."""
import re,unittest
from pathlib import Path
D=Path(__file__).resolve().parents[1]
S=(D/'src/installer/ui-prototype/preview.iss').read_text()
class LayoutTests(unittest.TestCase):
 def test_component_viewport_reserves_footer_space(self):
  self.assertIn('ComponentList.Parent := ComponentsPage.Surface;',S)
  self.assertIn('ComponentsPage.SurfaceHeight - ScaleY(180)',S)
  self.assertIn('ComponentList.SetBounds(ScaleX(8), ScaleY(132)',S)
  self.assertIn('Notice.Top := Result.SurfaceHeight - ScaleY(24);',S)
  # Algebraic clearance at all requested scales, not visual DPI qualification.
  for scale in (1,1.25,1.5):
   for height in (360,400,480):
    top=round(132*scale);bottom=top+round(height*scale)-round(180*scale)
    footer=round(height*scale)-round(24*scale)
    self.assertGreaterEqual(footer-bottom,round(23*scale))
 def test_native_wrapping_scroll_and_keyboard(self):
  self.assertIn('ComponentList := TNewCheckListBox.Create(WizardForm);',S)
  self.assertIn("Title + #13#10 + Detail, '', 0,",S)
  self.assertIn('ComponentList.MinItemHeight := ScaleY(64);',S)
  self.assertIn('ComponentList.Font.Size := 10;',S)
  self.assertIn('ComponentList.Anchors := [akLeft, akTop, akRight, akBottom];',S)
  self.assertIn('ComponentList.WantTabs := False;',S)
  self.assertIn('ComponentList.TabStop := True;',S)
  self.assertNotIn('function CheckAt(',S)
 def test_all_four_defaults_and_independent_level_zero(self):
  real=S.split("  FrameworkChoice := AddComponentChoice('BepInEx",1)[1].split('#else',1)[0]
  self.assertIn('True, False);',real)
  for name in ('SettingsChoice','ToolsChoice','FPSChoice','GraphicsChoice'):
   block=real.split(name+' := AddComponentChoice(',1)[1].splitlines()[1]
   self.assertTrue(block.rstrip().endswith('False, True);'))
  self.assertIn('Selected, Enabled, False, False, nil);',S)
 def test_exact_masks_preserved(self):
  f=S.split('function SelectionMask()',1)[1].split('function DesktopSelection',1)[0]
  for name,bit in [('FrameworkChoice',1),('SettingsChoice',8),('ToolsChoice',16),('FPSChoice',32),('GraphicsChoice',64)]:
   self.assertIn('if ComponentList.Checked['+name+'] then Result := Result + '+str(bit)+';',f)
 def test_desktop_exclusion_and_wording(self):
  self.assertIn('Not included in this release.',S)
  self.assertNotIn('initial public profile',S)
  self.assertIn('DesktopOriginal.Enabled := False;',S)
 def test_no_new_native_import_or_worker_routing(self):
  self.assertEqual(re.findall(r"external '([^']+)'",S),['SetTimer@user32.dll stdcall','KillTimer@user32.dll stdcall','SystemParametersInfoW@user32.dll stdcall'])
  for text in ['ValidatedBinding = SelectionBinding()','Result := Result and BackendOK','and IsHex64(PlanDigest)','Result := ConfirmInstallation();','if CurPageID = wpReady then']:
   self.assertIn(text,S)
 def test_release_version_and_non_elevated_setup(self):
  for text in ['AppVersion={#ReleaseVersion}','VersionInfoVersion={#ReleaseNumericVersion}','OutputBaseFilename=VRK-Mod-Installer-v{#ReleaseVersion}','PrivilegesRequired=lowest']:
   self.assertIn(text,S)
if __name__=='__main__':unittest.main()

