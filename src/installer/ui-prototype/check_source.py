"""Limited source-only checks. Does not compile or execute the preview installer."""
from pathlib import Path
import re
import unittest

SOURCE = Path(__file__).with_name('preview.iss').read_text(encoding='utf-8')


class PreviewSourceTests(unittest.TestCase):
    def test_portable_launch_has_no_python_fallback(self):
        # Stop at the outer portable #else, not a nested profile selector.
        rows=[];depth=0
        for line in SOURCE.split('procedure InitializeWizard;',1)[1].split('#ifdef PORTABLE_BACKEND',1)[1].splitlines():
            token=line.strip()
            if token.startswith(('#ifdef ', '#ifndef ')):depth+=1
            elif token=='#endif':
                if depth==0:break
                depth-=1
            elif token=='#else' and depth==0:break
            rows.append(line)
        branch='\n'.join(rows)
        self.assertIn("{src}\\Backend\\HFBackend.exe",branch)
        self.assertIn("BackendPrefix := 'gui ';",branch)
        self.assertNotIn('python.exe',branch)
        self.assertNotIn('C:\\Users',branch)
    def test_datetime_char_argument_regression(self):
        self.assertIn("GetDateTimeString('yyyymmddhhnnss', #0, #0)", SOURCE)
        self.assertNotRegex(SOURCE, r"GetDateTimeString\([^\n]*, '', ''\)")
        wrapper = SOURCE.split('procedure RefreshSummary;', 1)[1].split('procedure InitializeWizard;', 1)[0]
        self.assertLess(wrapper.index('NextButton.Enabled := False'), wrapper.index('ValidateSummary;'))
        self.assertIn('except', wrapper)
        self.assertIn('GetExceptionMessage', wrapper)

    def test_build_wrapper_qualification(self):
        wrapper = Path(__file__).with_name('build-preview.ps1').read_text(encoding='utf-8')
        for text in ("'out\\Preview'", "'Valid'", 'CN=Pyrsys', "$engineVersion -ne '7.1.1'", '/ni /ns /DDEBUG /DUI_PROTOTYPE'):
            self.assertIn(text, wrapper)

    def test_only_non_payload_sections(self):
        self.assertEqual(re.findall(r'^\[([^]]+)\]', SOURCE, re.M), ['Setup', 'Languages', 'Messages', 'Files', 'Code'])

    def test_no_helper_or_mutator(self):
        imports=re.findall(r"external '([^']+)'",SOURCE)
        self.assertEqual(imports,['SetTimer@user32.dll stdcall','KillTimer@user32.dll stdcall'])
        self.assertIn('#include "embedded_cache.iss"',SOURCE)
        self.assertNotRegex(SOURCE.lower(), r'\bshellexec\s*\(|\bdeletefile\s*\(|\bdeltree\s*\(|\bsavestringtofile\s*\(|\bregwrite\w*\s*\(|\b(?:direxists|findfirst|forcedirectories|filecopy|sleep)\s*\(')
        self.assertEqual(len(re.findall(r'\bExec\(', SOURCE)), 2)
        self.assertNotIn('ewWaitUntilTerminated',SOURCE)
        self.assertIn("Exec(DevPython, Params, '', SW_HIDE, ewNoWait, Code)",SOURCE)

    def test_private_browse_is_explicit_and_scoped(self):
        browse=SOURCE.split('procedure BrowseGameClick',1)[1].split('#endif',1)[0]
        self.assertIn('BrowseForFolder',browse)
        self.assertNotIn('DisposableAck',SOURCE)
        self.assertIn("BackendPrefix := 'private-gui ';",SOURCE)
        self.assertNotIn('--disposable-copy',SOURCE)
        self.assertIn('Select your game folder.',SOURCE)
        self.assertIn('private-game-gui-v1',SOURCE)
        self.assertIn('only',SOURCE.lower())

    def test_specific_backend_diagnostics(self):
        self.assertNotIn('Backend unavailable, preparation failed or response invalid.', SOURCE)
        for text in ('ReadStartupFailure', '--startup-error-file', 'projected transaction path', 'Backend executable is missing',
                     'Windows could not launch backend', 'Preparation did not return a verified response', 'FrameError', 'No execution is authorized'):
            self.assertIn(text, SOURCE)
        self.assertEqual(len(re.findall(r'LoadStringFromFile\(', SOURCE)),1)
        self.assertIn('LoadStringFromFile(StartupErrorFile, Raw)',SOURCE)

    def test_single_exe_storage_and_integrity(self):
        cache=Path(__file__).with_name('embedded_cache.iss').read_text(encoding='utf-8-sig')
        for text in ('VerifyResourceCache','RequireSafeDirectory','CheckResourceInventory','ExtractTemporaryFiles','GetSHA256OfFile','ResourceHashes','RenameFile','PersistentSuffix'):
            self.assertIn(text,cache)
        self.assertNotRegex(cache.lower(),r'deltree|deletefile|shellexec|regwrite')
        self.assertIn('Flags: dontcopy', (Path(__file__).parents[3]/'tools/build_single_exe.py').read_text())
        self.assertIn("DevExchange := PersistentBase + '\\state\\out\\gui-install\\';",SOURCE)
        self.assertIn('AppPublisher=FeriousX',SOURCE)

    def test_real_backend_gate(self):
        for text in ('--mask ', '--desktop ', '--library ', 'GetSHA256OfFile', 'BackendOK := False;',
                     'WizardForm.NextButton.Enabled := BackendOK;', 'ValidatedBinding = SelectionBinding()',
                     "'real_installation_allowed'", "'response_sha256'", "'job'", '--approve-plan '):
            self.assertIn(text, SOURCE)

    def test_seven_simulated_pages(self):
        for flags in ({'DEBUG','UI_PROTOTYPE'}, {'DEBUG','UI_PROTOTYPE','PORTABLE_BACKEND','REAL_COMPONENTS','PRIVATE_GAME'}):
            enabled=True;stack=[];lines=[]
            for line in SOURCE.splitlines():
                token=line.strip()
                if token.startswith(('#ifdef ', '#ifndef ')):
                    condition=token.split()[1] in flags
                    if token.startswith('#ifndef '):condition=not condition
                    stack.append((enabled,condition));enabled=enabled and condition
                elif token=='#else':
                    parent,condition=stack[-1];enabled=parent and not condition
                elif token=='#endif':enabled=stack.pop()[0]
                elif enabled:lines.append(line)
            self.assertEqual(len(re.findall(r':= Chapter\(', '\n'.join(lines))), 7)
        self.assertIn("'Demo library A / VR Kanojo (2018)'", SOURCE)
        self.assertIn('Location.Style := csDropDownList;', SOURCE)
        self.assertIn("'SYNTHETIC TEST ONLY  /  NO GAME INSTALLATION'", SOURCE)
        self.assertIn('WizardStyle=modern dark windows11 hidebevels includetitlebar', SOURCE)

    def test_exclusive_desktop_options(self):
        self.assertIn('Result.Parent := DesktopPage.Surface;', SOURCE)
        self.assertEqual(len(re.findall(r':= RadioAt\(', SOURCE)), 3)
        self.assertIn('DesktopNeither.Checked := True;', SOURCE)
        for name in ('FeriousX', 'ManlyMarco', 'Neither'):
            self.assertIn(name, SOURCE)

    def test_actual_transaction_and_guarded_success(self):
        self.assertNotIn('SimulatedStep',SOURCE)
        self.assertIn('if Succeeded then Progress.Position := 100 else Progress.Position := 0;',SOURCE)
        self.assertIn('Progress.Style := npbstMarquee;',SOURCE)
        self.assertIn('CreateCallback(@PollBackend)',SOURCE)
        self.assertIn('if ExecutionStarted then Exit;',SOURCE)
        self.assertIn('mbConfirmation, MB_YESNO',SOURCE)
        self.assertIn('WorkerMayRun',SOURCE)
        self.assertIn('StopPolling;',SOURCE)
        self.assertIn('if CurPageID = CompletePage.ID then Result := False;', SOURCE)
        self.assertIn('WizardForm.NextButton.Visible := False;', SOURCE)
        self.assertIn('(PageID = wpReady)', SOURCE)
        self.assertNotRegex(SOURCE.lower(), r'click install|ready to install|install now')

    def test_scaled_native_layout(self):
        self.assertIn('ScaleX(', SOURCE)
        self.assertIn('ScaleY(', SOURCE)
        self.assertIn('Summary.ReadOnly := True;', SOURCE)
        self.assertIn('Summary.ScrollBars := ssVertical;', SOURCE)

    def test_refined_header_and_notices(self):
        self.assertIn("CreateCustomPage(AfterID, 'VR Kanojo Mod Installer', '')", SOURCE)
        self.assertIn('WizardForm.PageDescriptionLabel.Visible := False;', SOURCE)
        self.assertEqual(SOURCE.count("'SYNTHETIC TEST ONLY  /  NO GAME INSTALLATION'"), 1)
        self.assertIn("WizardForm.BeveledLabel.Caption := '';", SOURCE)
        self.assertIn('Description.Left := ScaleX(28);', SOURCE)

    def test_concise_keyboard_navigation(self):
        captions = re.findall(r"NextButton.Caption := '([^']+)'", SOURCE)
        self.assertTrue(all(len(c.replace('&', '')) <= 11 for c in captions))
        self.assertTrue(all('&' in c for c in captions))
        self.assertNotIn('WizardResizable=', SOURCE)

    def test_compile_gates(self):
        for flag in ('DEBUG', 'UI_PROTOTYPE'):
            self.assertIn('#ifndef ' + flag, SOURCE)
        self.assertEqual(SOURCE.count('#error'), 2)

    def test_runtime_defenses(self):
        for text in ('PrivilegesRequired=lowest', 'CreateAppDir=no', 'Uninstallable=no',
                     'CreateUninstallRegKey=no', 'CloseApplications=no', 'RestartApplications=no',
                     'Result := not WizardSilent;', 'Result := CurPageID <> wpReady;',
                     'WizardForm.NextButton.Enabled := False;',
                     "Result := 'NONFUNCTIONAL PROTOTYPE: installation is disabled.';"):
            self.assertIn(text, SOURCE)


if __name__ == '__main__':
    unittest.main(verbosity=2)
