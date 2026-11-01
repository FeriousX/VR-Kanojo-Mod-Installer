; Newly written asset-free development shell. NOT the original HF Patch installer.
; Authored synthetic .txt transactions only. No game detection or genuine payload.
#ifndef DEBUG
  #error Asset-free prototype requires /DDEBUG
#endif
#ifndef UI_PROTOTYPE
  #error Asset-free prototype requires /DUI_PROTOTYPE
#endif

[Setup]
AppId=FeriousX.VRKanojoModInstaller.Preview
#ifdef PRIVATE_GAME
AppName=VR Kanojo Mod Installer
#else
AppName=VR Kanojo Mod Installer
#endif
AppVersion=1.0.0-rc.8C3
AppPublisher=FeriousX
AppPublisherURL=https://github.com/FeriousX/VR-Kanojo-Mod-Installer
VersionInfoDescription=VR Kanojo Mod Installer - Private Runtime RC 8C.3
VersionInfoProductName=VR Kanojo Mod Installer
VersionInfoCompany=FeriousX
VersionInfoVersion=0.9.8.3
OutputBaseFilename=HF_UI_PREVIEW_PHASE5E4_SYNTHETIC
OutputDir=..\..\..\out\Preview
PrivilegesRequired=lowest
CreateAppDir=no
Uninstallable=no
CreateUninstallRegKey=no
DisableProgramGroupPage=yes
DisableWelcomePage=yes
DisableReadyPage=no
UsePreviousAppDir=no
UsePreviousTasks=no
UsePreviousSetupType=no
CloseApplications=no
RestartApplications=no
RestartIfNeededByRun=no
ChangesAssociations=no
ChangesEnvironment=no
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern dark windows11 hidebevels includetitlebar
WizardSizePercent=140,150

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"

[Messages]
WelcomeLabel1=NONFUNCTIONAL UI PROTOTYPE
WelcomeLabel2=Synthetic text-file installation only. No game files are included or changed.
ReadyLabel1=Preview stops here. Installation is disabled.
ButtonInstall=&Start
ButtonNext=&Continue
ButtonCancel=&Close
FinishedHeadingLabel=Preview complete
FinishedLabelNoIcons=See the verified synthetic transaction result. No game installation is supported.
ExitSetupMessage=Close VR Kanojo Mod Installer?

#ifdef SINGLE_EXE
[Files]
#include EmbeddedFiles
#endif

[Code]
var
  WelcomePage, LocationPage, ComponentsPage, DesktopPage: TWizardPage;
  SummaryPage, SimulationPage, CompletePage: TWizardPage;
#ifndef PRIVATE_GAME
  Location: TNewComboBox;
#endif
#ifdef PRIVATE_GAME
  GameDirectory: TNewEdit;
  BrowseGame: TNewButton;
#endif
  FrameworkChoice, SettingsChoice, ToolsChoice: TNewCheckBox;
  DesktopFerious, DesktopOriginal, DesktopNeither: TNewRadioButton;
  Summary: TNewMemo;
  PreparationProgress: TNewProgressBar;
  SummaryDetailsButton, ProgressDetailsButton, CompletionDetailsButton: TNewButton;
  Preparing: Boolean;
  DisplayTitle, DisplayTarget, DisplayComponents, DisplayMessage: String;
  PrimaryText, TechnicalBody, PlanDetails: String;
  FilesCreate, FilesReplace, FilesPreserve, FilesRemove, FilesTotal, FilesApplied, FilesToApply: Integer;
  Progress: TNewProgressBar;
  ProgressText: TNewStaticText;
  BackendOK: Boolean;
  FrameError, StartupErrorFile: String;
  PersistentBase, CacheRoot, ResourceError: String;
  ValidatedBinding: String;
  CurrentJob, JobFolder, PlanDigest, LastSequence: String;
  ExecutionStarted, ActiveWorker, WorkerMayRun, Terminal, Polling: Boolean;
  TimerID: UINT_PTR;
  IdleTicks: Integer;
  CompletionMemo, ProgressDetails: TNewMemo;
  DevPython, DevAdapter, DevExchange, BackendPrefix: String;

#ifdef SINGLE_EXE
#include EmbeddedResources
#include "embedded_cache.iss"
#endif

function SetTimer(hWnd: HWND; nIDEvent: UINT_PTR; uElapse: UINT; lpTimerFunc: NativeInt): UINT_PTR;
  external 'SetTimer@user32.dll stdcall';
function KillTimer(hWnd: HWND; uIDEvent: UINT_PTR): Boolean;
  external 'KillTimer@user32.dll stdcall';

function LabelAt(Page: TWizardPage; Y, Height, Size: Integer; Text: String): TNewStaticText;
begin
  Result := TNewStaticText.Create(WizardForm);
  Result.Parent := Page.Surface;
  Result.Left := ScaleX(8);
  Result.Top := ScaleY(Y);
  Result.Width := Page.SurfaceWidth - ScaleX(16);
  Result.Height := ScaleY(Height);
  Result.AutoSize := False;
  Result.WordWrap := True;
  Result.Font.Name := 'Segoe UI';
  Result.Font.Size := Size;
  Result.Caption := Text;
end;

function Chapter(AfterID: Integer; Step, Title, Subtitle: String): TWizardPage;
var Notice: TNewStaticText;
begin
  Result := CreateCustomPage(AfterID, 'VR Kanojo Mod Installer', '');
  LabelAt(Result, 2, 20, 9, 'STEP ' + Step);
  LabelAt(Result, 30, 44, 22, Title);
  LabelAt(Result, 84, 38, 10, Subtitle);
  Notice := LabelAt(Result, 0, 24, 9,
#ifdef PRIVATE_GAME
    'PRE-RELEASE  /  Maintained by FeriousX');
#else
#ifdef REAL_COMPONENTS
    'PRIVATE REAL-FILE TEST  /  NO GAME INSTALLATION');
#else
    'SYNTHETIC TEST ONLY  /  NO GAME INSTALLATION');
#endif
#endif
  Notice.Top := Result.SurfaceHeight - ScaleY(24);
end;

function CheckAt(Page: TWizardPage; Y: Integer; Title, Detail: String; Selected: Boolean): TNewCheckBox;
var Description: TNewStaticText;
begin
  Result := TNewCheckBox.Create(WizardForm);
  Result.Parent := Page.Surface;
  Result.SetBounds(ScaleX(8), ScaleY(Y), Page.SurfaceWidth - ScaleX(16), ScaleY(26));
  Result.Caption := Title;
  Result.Font.Style := [fsBold];
  Result.Checked := Selected;
  Description := LabelAt(Page, Y + 29, 32, 10, Detail);
  Description.Left := ScaleX(28);
  Description.Width := Page.SurfaceWidth - ScaleX(36);
end;

function RadioAt(Y: Integer; Title, Detail: String): TNewRadioButton;
var Description: TNewStaticText;
begin
  Result := TNewRadioButton.Create(WizardForm);
  Result.Parent := DesktopPage.Surface;
  Result.SetBounds(ScaleX(8), ScaleY(Y), DesktopPage.SurfaceWidth - ScaleX(16), ScaleY(26));
  Result.Caption := Title;
  Result.Font.Style := [fsBold];
  Description := LabelAt(DesktopPage, Y + 29, 32, 10, Detail);
  Description.Left := ScaleX(28);
  Description.Width := DesktopPage.SurfaceWidth - ScaleX(36);
end;

function SelectionMask(): Integer;
begin
  Result := 0;
  if FrameworkChoice.Checked then Result := Result + 1;
  if SettingsChoice.Checked then Result := Result + 2;
  if ToolsChoice.Checked then Result := Result + 4;
end;

function DesktopSelection(): String;
begin
  Result := 'neither';
  if DesktopFerious.Checked then Result := 'vrkanojo-desktop';
  if DesktopOriginal.Checked then Result := 'play-without-vr';
end;

function DemoLibrary(): String;
begin
#ifdef PRIVATE_GAME
  Result := Trim(GameDirectory.Text);
  while (Length(Result) > 3) and (Copy(Result, Length(Result), 1) = '\') do
    Delete(Result, Length(Result), 1);
#else
  Result := 'demo-a';
  if Location.ItemIndex = 1 then Result := 'demo-b';
#endif
end;

#ifdef PRIVATE_GAME
procedure BrowseGameClick(Sender: TObject);
var Selected: String;
begin
  Selected := DemoLibrary();
  if BrowseForFolder('Select the original VR Kanojo game directory', Selected, False) then
  begin
    GameDirectory.Text := Selected;
  end;
end;
#endif

function SelectionBinding(): String;
begin
  Result := IntToStr(SelectionMask()) + '|' + DesktopSelection() + '|' + DemoLibrary();
end;

function IsHex64(Value: String): Boolean;
var I: Integer;
begin
  Result := False;
  if Length(Value) <> 64 then Exit;
  for I := 1 to Length(Value) do
    if Pos(Copy(Value, I, 1), '0123456789abcdef') = 0 then Exit;
  Result := True;
end;

function ComponentLines(): String;
begin
  Result := DisplayComponents;
  StringChangeEx(Result, '; ', #13#10, True);
end;

procedure ShowTechnicalDetails(Sender: TObject);
var Form: TSetupForm; Memo: TNewMemo; CloseButton: TNewButton;
begin
  Form := CreateCustomForm(ScaleX(600), ScaleY(360), True, True);
  try
    Form.Caption := 'Installation technical details';
    Form.Font.Name := 'Segoe UI'; Form.Font.Size := 10;
    Memo := TNewMemo.Create(Form);
    Memo.Parent := Form;
    Memo.SetBounds(ScaleX(16), ScaleY(16), Form.ClientWidth - ScaleX(32), Form.ClientHeight - ScaleY(74));
    Memo.ReadOnly := True;
    Memo.ScrollBars := ssVertical;
    Memo.WordWrap := True;
    Memo.Text := TechnicalBody + #13#10 + 'Plan identifier: ' + PlanDigest + #13#10 +
      'Job: ' + CurrentJob + #13#10 + 'Persistent records: ' + JobFolder + #13#10 +
      'Keep recovery records. After the worker exits, use the retained runtime Recover.ps1 -Job <job ID>.';
    CloseButton := TNewButton.Create(Form);
    CloseButton.Parent := Form;
    CloseButton.SetBounds(Form.ClientWidth - ScaleX(116), Form.ClientHeight - ScaleY(44), ScaleX(100), ScaleY(28));
    CloseButton.Caption := '&Close';
    CloseButton.ModalResult := mrCancel;
    CloseButton.Default := True;
    CloseButton.Cancel := True;
    Form.ShowModal;
  finally
    Form.Free;
  end;
end;

function ConfirmInstallation(): Boolean;
var Form: TSetupForm; Memo: TNewMemo; InstallButton, CancelButton, DetailsButton: TNewButton;
begin
  Form := CreateCustomForm(ScaleX(560), ScaleY(340), True, True);
  try
    Form.Caption := 'Confirm installation';
    Form.Font.Name := 'Segoe UI'; Form.Font.Size := 10;
    Memo := TNewMemo.Create(Form);
    Memo.Parent := Form;
    Memo.SetBounds(ScaleX(16), ScaleY(16), Form.ClientWidth - ScaleX(32), Form.ClientHeight - ScaleY(80));
    Memo.ReadOnly := True;
    Memo.ScrollBars := ssVertical;
    Memo.WordWrap := True;
    Memo.Text := 'Install the selected components into the following game directory?' + #13#10 + #13#10 +
      DisplayTarget + #13#10 + #13#10 + ComponentLines() + #13#10 + #13#10 +
      'Files will be installed according to the reviewed plan. The game will not be launched.';
    DetailsButton := TNewButton.Create(Form);
    DetailsButton.Parent := Form;
    DetailsButton.SetBounds(ScaleX(16), Form.ClientHeight - ScaleY(44), ScaleX(160), ScaleY(28));
    DetailsButton.Caption := '&Technical details';
    DetailsButton.OnClick := @ShowTechnicalDetails;
    InstallButton := TNewButton.Create(Form);
    InstallButton.Parent := Form;
    InstallButton.SetBounds(Form.ClientWidth - ScaleX(232), Form.ClientHeight - ScaleY(44), ScaleX(100), ScaleY(28));
    InstallButton.Caption := '&Install';
    InstallButton.ModalResult := mrOk;
    CancelButton := TNewButton.Create(Form);
    CancelButton.Parent := Form;
    CancelButton.SetBounds(Form.ClientWidth - ScaleX(116), Form.ClientHeight - ScaleY(44), ScaleX(100), ScaleY(28));
    CancelButton.Caption := '&Cancel';
    CancelButton.ModalResult := mrCancel;
    CancelButton.Default := True;
    CancelButton.Cancel := True;
    Result := Form.ShowModal = mrOk;
  finally
    Form.Free;
  end;
end;

function DetailsAt(Page: TWizardPage): TNewButton;
begin
  Result := TNewButton.Create(WizardForm);
  Result.Parent := Page.Surface;
  Result.SetBounds(ScaleX(8), Page.SurfaceHeight - ScaleY(72), ScaleX(160), ScaleY(28));
  Result.Caption := '&Technical details';
  Result.OnClick := @ShowTechnicalDetails;
end;

function ReadPresentation(IniPath, State: String): Boolean;
var I: Integer; Values: array[0..6] of Integer; Names: array[0..6] of String;
begin
  Result := False;
  if GetIniString('transaction', 'display_protocol', '', IniPath) <> '1' then Exit;
  DisplayTitle := GetIniString('transaction', 'display_title', '', IniPath);
  DisplayTarget := GetIniString('transaction', 'display_target', '', IniPath);
  DisplayComponents := GetIniString('transaction', 'display_components', '', IniPath);
  DisplayMessage := GetIniString('transaction', 'display_message', '', IniPath);
  if (DisplayTitle = '') or (DisplayComponents = '') or (Length(DisplayTitle) > 2000) or
    (Length(DisplayTarget) > 2000) or (Length(DisplayComponents) > 2000) or (Length(DisplayMessage) > 2000) then Exit;
  Names[0] := 'files_create'; Names[1] := 'files_replace'; Names[2] := 'files_preserve';
  Names[3] := 'files_remove'; Names[4] := 'files_total'; Names[5] := 'files_applied'; Names[6] := 'files_to_apply';
  for I := 0 to 6 do
  begin
    Values[I] := StrToIntDef(GetIniString('transaction', Names[I], '', IniPath), -1);
    if (Values[I] < 0) or (Values[I] > 1000) then Exit;
  end;
  if (Values[4] <> Values[0] + Values[1] + Values[2] + Values[3]) or
     (Values[6] <> Values[0] + Values[1] + Values[3]) or (Values[5] > Values[6]) then Exit;
  FilesCreate := Values[0]; FilesReplace := Values[1]; FilesPreserve := Values[2]; FilesRemove := Values[3];
  FilesTotal := Values[4]; FilesApplied := Values[5]; FilesToApply := Values[6];
  PrimaryText := DisplayTitle + #13#10;
  if State = 'Completed' then
    PrimaryText := PrimaryText + 'Installed files: ' + IntToStr(FilesCreate + FilesReplace) +
      '   |   Preserved: ' + IntToStr(FilesPreserve) + #13#10
  else if (State = 'Prepared') or (State = 'Blocked') then
    PrimaryText := PrimaryText + 'Files: ' + IntToStr(FilesTotal) + ' total   |   Create: ' + IntToStr(FilesCreate) +
      '   |   Modify: ' + IntToStr(FilesReplace) + '   |   Preserve: ' + IntToStr(FilesPreserve) +
      '   |   Remove: ' + IntToStr(FilesRemove) + #13#10
  else if State = 'Applying' then
    PrimaryText := PrimaryText + 'Files applied: ' + IntToStr(FilesApplied) + ' of ' + IntToStr(FilesToApply) + #13#10;
  PrimaryText := PrimaryText + #13#10 + 'Game directory' + #13#10 + DisplayTarget + #13#10 + #13#10 +
    'Selected components' + #13#10 + ComponentLines() + #13#10 + #13#10 + DisplayMessage;
  Result := True;
end;

function ReadFrame(var State, Body: String; var IsFinal, Succeeded: Boolean): Boolean;
var IniPath, Sequence, Flag, Line, Digest: String;
    I, Count: Integer;
begin
  Result := False;
  FrameError := 'Response rejected: protocol, selection binding, integrity or terminal-state check failed. Revalidate the plan; do not edit response files.';
  IniPath := JobFolder + 'frame.ini';
  if not FileExists(IniPath) or not FileExists(JobFolder + 'frame.json') then
  begin
    FrameError := 'Backend response files are missing: ' + JobFolder + 'frame.ini / frame.json. Check that the complete package is writable.';
    Exit;
  end;
  Sequence := GetIniString('transaction', 'sequence', '', IniPath);
  if GetIniString('transaction', 'protocol', '', IniPath) <> '1' then begin FrameError := 'Unsupported response protocol; use the matching wizard and Backend.'; Exit; end;
#ifdef PRIVATE_GAME
  if GetIniString('transaction', 'profile', '', IniPath) <> 'private-disposable-game-v1' then begin FrameError := 'Unexpected private profile; restore the matching package.'; Exit; end;
  if GetIniString('transaction', 'scope', '', IniPath) <> 'private-game-gui-v1' then begin FrameError := 'Unexpected private response scope; revalidate using the matching Backend.'; Exit; end;
#else
#ifdef REAL_COMPONENTS
  if GetIniString('transaction', 'profile', '', IniPath) <> 'real-component-fixture-v1' then begin FrameError := 'Unexpected real-component profile; restore the matching package.'; Exit; end;
#endif
  if GetIniString('transaction', 'scope', '', IniPath) <> 'synthetic-gui-bridge' then begin FrameError := 'Unexpected synthetic response scope; restore the matching package.'; Exit; end;
#endif
  if GetIniString('transaction', 'job', '', IniPath) <> CurrentJob then begin FrameError := 'Response belongs to another job; revalidate selections.'; Exit; end;
  if GetIniString('transaction', 'binding', '', IniPath) <> SelectionBinding() then begin FrameError := 'Selections changed or response binding differs; revalidate before continuing.'; Exit; end;
#ifdef PRIVATE_GAME
  if GetIniString('transaction', 'real_installation_allowed', '', IniPath) <> '1' then begin FrameError := 'Private execution-scope flag is invalid; no execution authorized.'; Exit; end;
#else
  if GetIniString('transaction', 'real_installation_allowed', '', IniPath) <> '0' then begin FrameError := 'Synthetic execution-scope flag is invalid; no execution authorized.'; Exit; end;
#endif
  if GetIniString('transaction', 'response_sha256', '', IniPath) <> Lowercase(GetSHA256OfFile(JobFolder + 'frame.json')) then
  begin
    FrameError := 'Response integrity check failed. No execution is authorized. Revalidate; keep the complete Backend folder unchanged.';
    Exit;
  end;
  Digest := GetIniString('transaction', 'plan_digest', '', IniPath);
  if (PlanDigest <> '') and (Digest <> PlanDigest) then begin FrameError := 'Response plan digest changed; revalidate and approve the new exact plan.'; Exit; end;
  State := GetIniString('transaction', 'state', '', IniPath);
  if (State <> 'Prepared') and (State <> 'Blocked') and (State <> 'Validating') and
    (State <> 'BackingUp') and (State <> 'Applying') and (State <> 'Verifying') and
    (State <> 'Completed') and (State <> 'Failed') and (State <> 'RecoveryRequired') then begin FrameError := 'Response contains an unsupported transaction state.'; Exit; end;
  Flag := GetIniString('transaction', 'final', '', IniPath);
  if (Flag <> '0') and (Flag <> '1') then begin FrameError := 'Response final-state flag is malformed.'; Exit; end;
  IsFinal := Flag = '1';
  if IsFinal and (State <> 'Blocked') and (State <> 'Completed') and (State <> 'Failed') and (State <> 'RecoveryRequired') then begin FrameError := 'Response claims a terminal flag for a nonterminal state.'; Exit; end;
  Flag := GetIniString('transaction', 'success', '', IniPath);
  if (Flag <> '0') and (Flag <> '1') then begin FrameError := 'Response success flag is malformed.'; Exit; end;
  Succeeded := Flag = '1';
  if Succeeded and ((not IsFinal) or (State <> 'Completed') or
    (GetIniString('transaction', 'percent', '', IniPath) <> '100')) then begin FrameError := 'Response success acknowledgement is inconsistent; no success claimed.'; Exit; end;
  if (State = 'Completed') and (not Succeeded) then begin FrameError := 'Response completion lacks a verified success acknowledgement.'; Exit; end;
  Count := StrToIntDef(GetIniString('transaction', 'count', '', IniPath), -1);
  if (Count < 1) or (Count > 40) then begin FrameError := 'Response display-line count is invalid.'; Exit; end;
  Body := '';
  for I := 0 to Count - 1 do
  begin
    Line := GetIniString('transaction', 'line' + IntToStr(I), '<missing>', IniPath);
    if (Line = '<missing>') or (Length(Line) > 2000) then begin FrameError := 'Response text is missing or exceeds its allowed size.'; Exit; end;
    Body := Body + Line + #13#10;
  end;
  if not ReadPresentation(IniPath, State) then begin FrameError := 'Backend presentation is missing or invalid. No execution is authorized.'; Exit; end;
  if Sequence <> GetIniString('transaction', 'sequence', '', IniPath) then begin FrameError := 'Response changed while being read; retry validation.'; Exit; end;
  if Sequence <> LastSequence then IdleTicks := 0;
  LastSequence := Sequence;
  Result := True;
end;

function ReadStartupFailure(): String;
var Raw: AnsiString;
begin
  Result := '';
  if (StartupErrorFile <> '') and FileExists(StartupErrorFile) then
    if LoadStringFromFile(StartupErrorFile, Raw) then Result := Raw;
end;

procedure StopPolling;
begin
  if TimerID <> 0 then KillTimer(0, TimerID);
  TimerID := 0;
end;

procedure PreparationFailed(Body: String);
begin
  Preparing := False;
  StopPolling;
  PreparationProgress.Visible := False;
  BackendOK := False;
  ValidatedBinding := '';
  Summary.Text := Body;
  TechnicalBody := Body;
  SummaryDetailsButton.Enabled := True;
  WizardForm.NextButton.Enabled := False;
  WizardForm.BackButton.Enabled := True;
end;

procedure PollPreparation(Arg1: HWND; Arg2: UINT; Arg3: UINT_PTR; Arg4: DWORD);
var State, Body: String; IsFinal, Succeeded: Boolean;
begin
  if Polling or not Preparing then Exit;
  Polling := True;
  try
    try
      IdleTicks := IdleTicks + 1;
      Body := ReadStartupFailure();
      if Body <> '' then begin PreparationFailed(Body); Exit; end;
      if FileExists(JobFolder + 'frame.ini') and FileExists(JobFolder + 'frame.json') then
        if ReadFrame(State, Body, IsFinal, Succeeded) then
        begin
          if (State <> 'Prepared') and (State <> 'Blocked') and (State <> 'Failed') and (State <> 'RecoveryRequired') then
          begin PreparationFailed('Unexpected preparation state. No installation is authorized.'); Exit; end;
          Preparing := False;
          StopPolling;
          PreparationProgress.Visible := False;
          PlanDigest := GetIniString('transaction', 'plan_digest', '', JobFolder + 'frame.ini');
          BackendOK := (State = 'Prepared') and IsHex64(PlanDigest) and (not IsFinal) and (not Succeeded);
          if BackendOK then ValidatedBinding := SelectionBinding();
          PlanDetails := Body;
          TechnicalBody := Body;
          Summary.Text := PrimaryText;
          SummaryDetailsButton.Enabled := True;
          WizardForm.NextButton.Enabled := BackendOK;
          WizardForm.BackButton.Enabled := True;
          Exit;
        end;
      if Preparing and (IdleTicks > 120) then
        PreparationFailed('Preparation did not return a verified response within 60 seconds. No installation is authorized.' + #13#10 +
          FrameError + #13#10 + 'The preparation process was not terminated. Go Back and retry after it exits, or retain job: ' + CurrentJob);
    except
      PreparationFailed('Preparation failed: ' + GetExceptionMessage + #13#10 + 'No installation is authorized.');
    end;
  finally
    Polling := False;
  end;
end;

procedure ValidateSummary;
var Params, Body: String;
    Code: Integer;
begin
  BackendOK := False;
  ValidatedBinding := '';
  PlanDigest := '';
  Summary.Text := 'Preparing installation plan...' + #13#10 + #13#10 +
    'Checking the selected game folder, component hashes, existing files and configuration. Nothing is installed during preparation.';
  TechnicalBody := ''; PlanDetails := ''; LastSequence := ''; FrameError := 'No readable backend response.';
  Preparing := False;
  SummaryDetailsButton.Enabled := False;
  PreparationProgress.Visible := True;
  PreparationProgress.Style := npbstMarquee;
  WizardForm.Repaint;
#ifdef SINGLE_EXE
  if ResourceError <> '' then begin Summary.Text := ResourceError; Exit; end;
  try
    VerifyResourceCache(CacheRoot);
  except
    Summary.Text := GetExceptionMessage;
    Exit;
  end;
#endif
#ifdef PORTABLE_BACKEND
#ifdef SINGLE_EXE
  Body := PersistentBase + '\state\out\external-transactions\' +
#else
  Body := ExpandConstant('{src}\Backend\state\out\external-transactions\') +
#endif
    '00000000-0000-0000-0000-000000000000\sessions\00000000-0000-0000-0000-000000000000\blobs\' +
    '0000000000000000000000000000000000000000000000000000000000000000';
  if Length(Body) >= 260 then
  begin
#ifdef SINGLE_EXE
    Summary.Text := 'Persistent per-user directory exceeds the qualified path budget (' + IntToStr(Length(Body)) +
      ' characters; maximum 259). Keep recovery state unchanged and contact the maintainer for a profile-specific build. Moving the installer alone will not fix this. No installation is authorized.';
#else
    Summary.Text := 'Package directory is too deeply nested (' + IntToStr(Length(Body)) +
      '-character projected transaction path; supported maximum 259).' + #13#10 +
      'Move/re-extract the COMPLETE package to a short writable C: folder such as Downloads\HFPrivate. ' +
      'Preserve any existing transaction state. No installation is authorized.';
#endif
    Exit;
  end;
#endif
  if not FileExists(DevPython) then
  begin
    Summary.Text := 'Backend executable is missing: ' + DevPython + #13#10 + 'Re-extract the COMPLETE package; keep Backend beside the wizard. No execution is authorized.';
    Exit;
  end;
  if not FileExists(DevAdapter) then
  begin
    Summary.Text := 'Execution adapter is missing: ' + DevAdapter + '. Restore the complete matching package.';
    Exit;
  end;

  CurrentJob := Lowercase(GetSHA256OfString(GetDateTimeString('yyyymmddhhnnss', #0, #0) + IntToStr(Random(2147483647))));
  JobFolder := DevExchange + CurrentJob + '\';
  StartupErrorFile := ExpandConstant('{tmp}\hf-startup-') + CurrentJob + '.txt';
  Params := BackendPrefix + 'prepare --job ' + CurrentJob +
    ' --mask ' + IntToStr(SelectionMask()) + ' --desktop ' + DesktopSelection() +
#ifdef PRIVATE_GAME
    ' --target "' + DemoLibrary() + '"';
#else
    ' --library ' + DemoLibrary();
#endif
#ifdef PORTABLE_BACKEND
  Params := '--startup-error-file "' + StartupErrorFile + '" ' + Params;
#endif
  IdleTicks := 0;
  Preparing := True;
  TimerID := SetTimer(0, 0, 500, CreateCallback(@PollPreparation));
  if TimerID = 0 then begin PreparationFailed('Could not start preparation monitoring. No backend was launched.'); Exit; end;
  if not Exec(DevPython, Params, '', SW_HIDE, ewNoWait, Code) then
    PreparationFailed('Windows could not launch backend (code ' + IntToStr(Code) + '): ' + DevPython +
      '. Check the resource cache and file access. No execution is authorized.');
end;

procedure RefreshSummary;
begin
  BackendOK := False;
  ValidatedBinding := '';
  WizardForm.NextButton.Enabled := False;
  try
    ValidateSummary;
  except
    BackendOK := False;
    ValidatedBinding := '';
    PreparationFailed('Backend validation could not be completed: ' + GetExceptionMessage + #13#10 +
      'Go Back to review choices. No installation is authorized.');
  end;
  WizardForm.NextButton.Enabled := BackendOK;
  WizardForm.BackButton.Enabled := not Preparing;
  if not Preparing then begin PreparationProgress.Visible := False; TechnicalBody := Summary.Text; SummaryDetailsButton.Enabled := True; end;
end;

procedure ShowOutcome(State, Body: String; Succeeded: Boolean);
begin
  Terminal := True;
  ActiveWorker := False;
  StopPolling;
  Progress.Style := npbstNormal;
  if Succeeded then Progress.Position := 100 else Progress.Position := 0;
  if Succeeded then ProgressText.Caption := 'Installation completed successfully!' else ProgressText.Caption := State;
  TechnicalBody := PlanDetails + #13#10 + #13#10 + Body;
  if Succeeded then CompletionMemo.Text := PrimaryText else CompletionMemo.Text :=
    'Installation was not completed.' + #13#10 + #13#10 + 'No success is claimed. Keep recovery records and open Technical details.' + #13#10 + #13#10 + State;
  ProgressDetails.Text := CompletionMemo.Text;
  WizardForm.NextButton.Enabled := True;
  WizardForm.NextButton.Caption := '&View result';
end;

procedure PollBackend(Arg1: HWND; Arg2: UINT; Arg3: UINT_PTR; Arg4: DWORD);
var State, Body: String;
    IsFinal, Succeeded: Boolean;
begin
  if Polling or not ActiveWorker then Exit;
  Polling := True;
  try
    try
      IdleTicks := IdleTicks + 1;
      Body := ReadStartupFailure();
      if Body <> '' then
      begin
        ShowOutcome('Backend refused - no success claimed', Body, False);
        Exit;
      end;
      if ReadFrame(State, Body, IsFinal, Succeeded) and (State <> 'Prepared') then
      begin
        ProgressText.Caption := DisplayTitle;
        ProgressDetails.Text := PrimaryText;
        TechnicalBody := PlanDetails + #13#10 + #13#10 + Body;
        if IsFinal then
        begin
          WorkerMayRun := False;
          ShowOutcome(State, Body, Succeeded);
        end;
      end;
      if ActiveWorker and (IdleTicks > 120) then
        ShowOutcome('Uncertain - recovery may be required',
          'No verified terminal response. The worker may still be running; it has not been terminated.' + #13#10 +
          'Keep this job ID: ' + CurrentJob + #13#10 + 'After the worker exits, open Technical details for the retained runtime recovery command.', False);
    except
      ShowOutcome('Response error - no success claimed', GetExceptionMessage + #13#10 +
        'Worker may still be running. Keep job: ' + CurrentJob, False);
    end;
  finally
    Polling := False;
  end;
end;

procedure StartWorker;
var Params: String;
    Code: Integer;
begin
  if ExecutionStarted then Exit;
  ExecutionStarted := True;
  WizardForm.BackButton.Enabled := False;
  WizardForm.NextButton.Enabled := False;
  if not FileExists(DevPython) or not FileExists(DevAdapter) then
  begin
    ShowOutcome('Backend unavailable', 'The bundled backend or execution adapter is missing. No worker was launched.', False);
    Exit;
  end;
  ProgressText.Caption := 'Preparing worker';
  Progress.Style := npbstMarquee;
  TimerID := SetTimer(0, 0, 500, CreateCallback(@PollBackend));
  if TimerID = 0 then
  begin
    ShowOutcome('Failed to start status monitoring', 'No worker was launched.', False);
    Exit;
  end;
#ifdef SINGLE_EXE
  try
    VerifyResourceCache(CacheRoot);
  except
    ShowOutcome('Resource integrity failure', GetExceptionMessage, False);
    Exit;
  end;
#endif
  Params := BackendPrefix + 'run --job ' + CurrentJob + ' --approve-plan ' + PlanDigest;
#ifdef PORTABLE_BACKEND
  Params := '--startup-error-file "' + StartupErrorFile + '" ' + Params;
#endif
  ActiveWorker := True;
  WorkerMayRun := True;
  IdleTicks := 0;
  if not Exec(DevPython, Params, '', SW_HIDE, ewNoWait, Code) then
  begin
    WorkerMayRun := False;
    ShowOutcome('Failed to launch backend', 'No transaction success is claimed. Keep job: ' + CurrentJob, False);
  end;
end;

procedure InitializeWizard;
begin
#ifdef PORTABLE_BACKEND
#ifdef SINGLE_EXE
  try
    PrepareEmbeddedBackend;
  except
    ResourceError := GetExceptionMessage;
  end;
  DevPython := CacheRoot + '\Backend\HFBackend.exe';
  DevExchange := PersistentBase + '\state\out\gui-install\';
#else
  DevPython := ExpandConstant('{src}\Backend\HFBackend.exe');
  DevExchange := ExpandConstant('{src}\Backend\state\out\gui-install\');
#endif
  DevAdapter := DevPython;
#ifdef PRIVATE_GAME
  BackendPrefix := 'private-gui ';
#else
#ifdef REAL_COMPONENTS
  BackendPrefix := 'real-gui ';
#else
  BackendPrefix := 'gui ';
#endif
#endif
#else
  DevPython := ExpandConstant('{src}\DevelopmentPythonNotConfigured.exe');
  DevAdapter := ExpandConstant('{src}\tools\gui_install.py');
  DevExchange := ExpandConstant('{src}\out\gui-install\');
  BackendPrefix := '-I -S -B "' + DevAdapter + '" ';
#endif
  WizardForm.Font.Name := 'Segoe UI';
  WizardForm.Font.Size := 10;
  WizardForm.WizardSmallBitmapImage.Visible := False;
  WizardForm.PageNameLabel.Font.Size := 13;
  WizardForm.PageNameLabel.Top := ScaleY(16);
  WizardForm.PageNameLabel.Height := ScaleY(28);
  WizardForm.PageDescriptionLabel.Visible := False;
  WizardForm.BeveledLabel.Caption := '';

  WelcomePage := Chapter(wpWelcome, '01 / 07', 'VR Kanojo Mod Installer.',
    'A considered new interface for the original VR Kanojo (2018).');
  LabelAt(WelcomePage, 148, 30, 13, 'BUILT ON A COMMUNITY LEGACY');
  LabelAt(WelcomePage, 205, 55, 11,
#ifdef REAL_COMPONENTS
#ifdef PRIVATE_GAME
    'Install reviewed framework and plugins into your selected original VR Kanojo game folder. No game repair, models or saves.');
#else
    'Copy verified plugin files into disposable test roots. No game repair, models or saves are included.');
#endif
#else
    'Explore a simpler setup experience: choose a demo library, compare components and review your selections.');
#endif
  LabelAt(WelcomePage, 278, 70, 10,
    'Original HF Patch by ManlyMarco and its contributors.' + #13#10 +
    'Maintained by FeriousX. Independent GPL-3.0 project; not an official release or endorsement.');

#ifdef PRIVATE_GAME
  LocationPage := Chapter(WelcomePage.ID, '02 / 07', 'Select your game folder.',
    'Original VR Kanojo (2018), x64 Unity 5.4.5p1. Technical checks do not certify the game version.');
  LabelAt(LocationPage, 150, 25, 10, 'GAME DIRECTORY');
  GameDirectory := TNewEdit.Create(WizardForm);
  GameDirectory.Parent := LocationPage.Surface;
  GameDirectory.SetBounds(ScaleX(8), ScaleY(188), LocationPage.SurfaceWidth - ScaleX(124), ScaleY(28));
  BrowseGame := TNewButton.Create(WizardForm);
  BrowseGame.Parent := LocationPage.Surface;
  BrowseGame.SetBounds(LocationPage.SurfaceWidth - ScaleX(108), ScaleY(186), ScaleX(100), ScaleY(30));
  BrowseGame.Caption := '&Browse...';
  BrowseGame.OnClick := @BrowseGameClick;
  LabelAt(LocationPage, 304, 70, 10,
    'Directory identity, game structure and hashes are checked by the backend. No installation occurs until separate plan consent.');
#else
  LocationPage := Chapter(WelcomePage.ID, '02 / 07', 'Choose a demo location.',
    'Select an example library to explore the setup flow.');
  LabelAt(LocationPage, 150, 25, 10, 'EXAMPLE GAME LIBRARY');
  Location := TNewComboBox.Create(WizardForm);
  Location.Parent := LocationPage.Surface;
  Location.SetBounds(ScaleX(8), ScaleY(188), LocationPage.SurfaceWidth - ScaleX(16), ScaleY(32));
  Location.Style := csDropDownList;
#ifdef REAL_COMPONENTS
  Location.Items.Add('Disposable test A / backend-owned root');
  Location.Items.Add('Disposable test B / backend-owned root');
#else
  Location.Items.Add('Demo library A / VR Kanojo (2018)');
  Location.Items.Add('Demo library B / VR Kanojo (2018)');
#endif
  Location.ItemIndex := 0;
  LabelAt(LocationPage, 252, 70, 10,
#ifdef REAL_COMPONENTS
    'The backend creates a fresh disposable root. No game browsing, scanning or arbitrary destinations are available.');
#else
    'Example locations only. Folder browsing and game detection are unavailable; no directories are opened or created.');
#endif

#endif

  ComponentsPage := Chapter(LocationPage.ID, '03 / 07', 'Make it your setup.',
#ifdef REAL_COMPONENTS
#ifdef PRIVATE_GAME
    'Choose reviewed plugin components for your selected game.');
#else
    'Select real plugins for a disposable test root; no game files are accessed.');
#endif
#else
    'Choose the component groups to include in your simulated setup.');
#endif
#ifdef REAL_COMPONENTS
  FrameworkChoice := CheckAt(ComponentsPage, 132, 'BepInEx framework (required)',
    'Verified framework and game-specific entry-point settings. Legacy F1 menu is excluded.', True);
  FrameworkChoice.Enabled := False;
  SettingsChoice := CheckAt(ComponentsPage, 200, 'Uncensor Loader + XUnity (optional)',
    'Not included in this initial public profile.', False);
  SettingsChoice.Enabled := False;
  ToolsChoice := CheckAt(ComponentsPage, 268, 'Optional utilities and developer tools',
    'Not included in this initial public profile.', False);
  ToolsChoice.Enabled := False;
#else
  FrameworkChoice := CheckAt(ComponentsPage, 132, 'Core framework',
    'Runtime and compatibility foundation.', True);
  SettingsChoice := CheckAt(ComponentsPage, 200, 'Configuration tools',
    'F1 configuration menu and settings management.', True);
  ToolsChoice := CheckAt(ComponentsPage, 268, 'Optional utilities',
    'Additional convenience tools, optional by default.', False);
#endif

  DesktopPage := Chapter(ComponentsPage.ID, '04 / 07', 'Choose how you play.',
    'Select one desktop-control option, or keep the standard VR experience.');
  DesktopFerious := RadioAt(132, 'VR Kanojo Desktop  /  FeriousX',
    'Modern keyboard and mouse controls.');
  DesktopOriginal := RadioAt(200, 'Original Play Without VR  /  ManlyMarco',
    'Not included in this initial public profile.');
  DesktopOriginal.Enabled := False;
  DesktopNeither := RadioAt(268, 'Neither',
    'Keep the standard VR experience without a desktop plugin.');
  DesktopNeither.Checked := True;

  SummaryPage := Chapter(DesktopPage.ID, '05 / 07', 'Review installation',
#ifdef REAL_COMPONENTS
#ifdef PRIVATE_GAME
    'Review your selections. Installation begins only after your confirmation.');
#else
    'Actual real-file fixture plan. Review all paths and hashes before consent.');
#endif
#else
    'Actual synthetic plan. Start requires separate consent for these exact text-file changes.');
#endif
  Summary := TNewMemo.Create(WizardForm);
  Summary.Parent := SummaryPage.Surface;
  Summary.SetBounds(ScaleX(8), ScaleY(142), SummaryPage.SurfaceWidth - ScaleX(16),
    SummaryPage.SurfaceHeight - ScaleY(214));
  Summary.ReadOnly := True;
  Summary.ScrollBars := ssVertical;
  Summary.WordWrap := True;
  SummaryDetailsButton := DetailsAt(SummaryPage);
  PreparationProgress := TNewProgressBar.Create(WizardForm);
  PreparationProgress.Parent := SummaryPage.Surface;
  PreparationProgress.SetBounds(ScaleX(184), SummaryPage.SurfaceHeight - ScaleY(60), SummaryPage.SurfaceWidth - ScaleX(200), ScaleY(8));
  PreparationProgress.Visible := False;

  SimulationPage := Chapter(SummaryPage.ID, '06 / 07', 'Installation progress.',
#ifdef REAL_COMPONENTS
    'Actual plugin file-copy transaction into the selected directory. No binaries execute.');
#else
    'Actual journaled transaction. No game or plugin installation is supported.');
#endif
  ProgressText := LabelAt(SimulationPage, 140, 42, 15, 'Preparing');
  Progress := TNewProgressBar.Create(WizardForm);
  Progress.Parent := SimulationPage.Surface;
  Progress.SetBounds(ScaleX(8), ScaleY(192), SimulationPage.SurfaceWidth - ScaleX(16), ScaleY(12));
  Progress.Min := 0;
  Progress.Max := 100;
  ProgressDetails := TNewMemo.Create(WizardForm);
  ProgressDetails.Parent := SimulationPage.Surface;
  ProgressDetails.SetBounds(ScaleX(8), ScaleY(222), SimulationPage.SurfaceWidth - ScaleX(16),
    SimulationPage.SurfaceHeight - ScaleY(310));
  ProgressDetails.ReadOnly := True;
  ProgressDetails.ScrollBars := ssVertical;
  ProgressDetails.WordWrap := True;
  ProgressDetailsButton := DetailsAt(SimulationPage);

  CompletePage := Chapter(SimulationPage.ID, '07 / 07', 'Installation result',
    'Review the verified result. Technical details and recovery instructions remain available.');
  CompletionMemo := TNewMemo.Create(WizardForm);
  CompletionMemo.Parent := CompletePage.Surface;
  CompletionMemo.SetBounds(ScaleX(8), ScaleY(142), CompletePage.SurfaceWidth - ScaleX(16),
    CompletePage.SurfaceHeight - ScaleY(230));
  CompletionMemo.ReadOnly := True;
  CompletionMemo.ScrollBars := ssVertical;
  CompletionMemo.WordWrap := True;
  CompletionDetailsButton := DetailsAt(CompletePage);
end;

type
  TLicenseWorkArea = record
    Left, Top, Right, Bottom: Integer;
  end;

function LicenseSystemParametersInfo(Action, Param: UINT; var Area: TLicenseWorkArea; Flags: UINT): Boolean;
  external 'SystemParametersInfoW@user32.dll stdcall';

function AcceptRuntimeConditions(): Boolean;
var
  Form: TSetupForm;
  Intro: TNewStaticText;
  TermsMemo: TNewMemo;
  AcceptButton, DeclineButton: TNewButton;
  Area: TLicenseWorkArea;
  MarginX, MarginY, ButtonWidth, ButtonHeight, ButtonTop: Integer;
begin
  Result := False;
  { SPI_GETWORKAREA uses the same DPI coordinate space as this Setup process. }
  if not LicenseSystemParametersInfo(48, 0, Area, 0) then
  begin
    MsgBox('Cannot determine the available screen area. Setup cannot continue.', mbError, MB_OK);
    Exit;
  end;
  { CreateCustomForm scales these dimensions itself. Never pre-scale them. }
  Form := CreateCustomForm(640, 480, True, True);
  try
    Form.Caption := 'Runtime redistribution conditions';
    Form.BorderStyle := bsDialog;
    Form.Position := poDesigned;
    MarginX := ScaleX(16);
    MarginY := ScaleY(16);
    if Form.Width > Area.Right - Area.Left - 2 * MarginX then
      Form.Width := Area.Right - Area.Left - 2 * MarginX;
    if Form.Height > Area.Bottom - Area.Top - 2 * MarginY then
      Form.Height := Area.Bottom - Area.Top - 2 * MarginY;
    Form.Left := Area.Left + (Area.Right - Area.Left - Form.Width) div 2;
    Form.Top := Area.Top + (Area.Bottom - Area.Top - Form.Height) div 2;
    ButtonWidth := ScaleX(120);
    ButtonHeight := ScaleY(30);
    ButtonTop := Form.ClientHeight - MarginY - ButtonHeight;
    if (Form.ClientWidth < 2 * ButtonWidth + 3 * MarginX) or
       (ButtonTop < ScaleY(160)) then Exit;
    Intro := TNewStaticText.Create(Form);
    Intro.Parent := Form;
    Intro.SetBounds(MarginX, MarginY, Form.ClientWidth - 2 * MarginX, ScaleY(58));
    Intro.AutoSize := False;
    Intro.WordWrap := True;
    Intro.Caption := 'Please review the complete conditions below. They apply only to Microsoft Distributable Code in the Windows Python runtime, not to this GPL application. Accept to continue, or Decline to exit.';
    TermsMemo := TNewMemo.Create(Form);
    TermsMemo.Parent := Form;
    TermsMemo.SetBounds(MarginX, MarginY + ScaleY(66), Form.ClientWidth - 2 * MarginX,
      ButtonTop - MarginY - (MarginY + ScaleY(66)));
    TermsMemo.ReadOnly := True;
    TermsMemo.ScrollBars := ssVertical;
    TermsMemo.WordWrap := True;
    TermsMemo.TabOrder := 0;
    TermsMemo.Text := 'Additional Conditions for this Windows binary build' + #13#10 +
      '---------------------------------------------------' + #13#10 +
      '' + #13#10 +
      'This program is linked with and uses Microsoft Distributable Code,' + #13#10 +
      'copyrighted by Microsoft Corporation. The Microsoft Distributable Code' + #13#10 +
      'is embedded in each .exe, .dll and .pyd file as a result of running' + #13#10 +
      'the code through a linker.' + #13#10 +
      '' + #13#10 +
      'If you further distribute programs that include the Microsoft' + #13#10 +
      'Distributable Code, you must comply with the restrictions on' + #13#10 +
      'distribution specified by Microsoft. In particular, you must require' + #13#10 +
      'distributors and external end users to agree to terms that protect the' + #13#10 +
      'Microsoft Distributable Code at least as much as Microsoft''s own' + #13#10 +
      'requirements for the Distributable Code. See Microsoft''s documentation' + #13#10 +
      '(included in its developer tools and on its website at microsoft.com)' + #13#10 +
      'for specific details.' + #13#10 +
      '' + #13#10 +
      'Redistribution of the Windows binary build of the Python interpreter' + #13#10 +
      'complies with this agreement, provided that you do not:' + #13#10 +
      '' + #13#10 +
      '- alter any copyright, trademark or patent notice in Microsoft''s' + #13#10 +
      'Distributable Code;' + #13#10 +
      '' + #13#10 +
      '- use Microsoft''s trademarks in your programs'' names or in a way that' + #13#10 +
      'suggests your programs come from or are endorsed by Microsoft;' + #13#10 +
      '' + #13#10 +
      '- distribute Microsoft''s Distributable Code to run on a platform other' + #13#10 +
      'than Microsoft operating systems, run-time technologies or application' + #13#10 +
      'platforms; or' + #13#10 +
      '' + #13#10 +
      '- include Microsoft Distributable Code in malicious, deceptive or' + #13#10 +
      'unlawful programs.' + #13#10 +
      '' + #13#10 +
      'These restrictions apply only to the Microsoft Distributable Code as' + #13#10 +
      'defined above, not to Python itself or any programs running on the' + #13#10 +
      'Python interpreter. The redistribution of the Python interpreter and' + #13#10 +
      'libraries is governed by the Python Software License included with this' + #13#10 +
      'file, or by other licenses as marked.';
    AcceptButton := TNewButton.Create(Form);
    AcceptButton.Parent := Form;
    AcceptButton.SetBounds(Form.ClientWidth - MarginX * 2 - ButtonWidth * 2,
      ButtonTop, ButtonWidth, ButtonHeight);
    AcceptButton.Caption := '&Accept';
    AcceptButton.TabOrder := 1;
    AcceptButton.ModalResult := mrOk;
    DeclineButton := TNewButton.Create(Form);
    DeclineButton.Parent := Form;
    DeclineButton.SetBounds(Form.ClientWidth - MarginX - ButtonWidth,
      ButtonTop, ButtonWidth, ButtonHeight);
    DeclineButton.Caption := '&Decline';
    DeclineButton.TabOrder := 2;
    DeclineButton.ModalResult := mrCancel;
    DeclineButton.Default := True;
    DeclineButton.Cancel := True;
    Form.ActiveControl := DeclineButton;
    Result := Form.ShowModal = mrOk;
  finally
    Form.Free;
  end;
end;

function InitializeSetup(): Boolean;
begin
  Result := False;
  if not WizardSilent then
    Result := AcceptRuntimeConditions();
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  WizardForm.NextButton.Caption := '&Continue';
  WizardForm.NextButton.Enabled := True;
  WizardForm.CancelButton.Caption := '&Close';
  if CurPageID = WelcomePage.ID then WizardForm.NextButton.Caption := '&Continue';
  if CurPageID = SummaryPage.ID then
  begin
    RefreshSummary;
    WizardForm.NextButton.Caption := '&Install';
    WizardForm.NextButton.Enabled := BackendOK;
  end;
  if CurPageID = SimulationPage.ID then
  begin
    WizardForm.NextButton.Enabled := Terminal;
    WizardForm.BackButton.Enabled := False;
    StartWorker;
  end;
  if CurPageID = CompletePage.ID then
  begin
    WizardForm.NextButton.Visible := False;
    WizardForm.BackButton.Visible := False;
  end;
  if CurPageID = wpReady then
    WizardForm.NextButton.Enabled := False;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := (PageID = wpWelcome) or (PageID = wpReady) or (PageID = wpFinished);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := CurPageID <> wpReady;
#ifdef PRIVATE_GAME
  if CurPageID = LocationPage.ID then
  begin
    Result := (DemoLibrary() <> '') and (Pos('"', DemoLibrary()) = 0) and
      (Pos(#13, DemoLibrary()) = 0) and (Pos(#10, DemoLibrary()) = 0);
    if not Result then MsgBox('Select the folder containing the game executable and matching Data folder.', mbError, MB_OK);
  end;
#endif
  if CurPageID = SummaryPage.ID then
  begin
    Result := BackendOK and (ValidatedBinding = SelectionBinding()) and (not ExecutionStarted);
    if Result then
      Result := ConfirmInstallation();
    Result := Result and BackendOK and (ValidatedBinding = SelectionBinding()) and IsHex64(PlanDigest);
  end;
  if CurPageID = CompletePage.ID then Result := False;
  if CurPageID = SimulationPage.ID then Result := Terminal;
end;

function BackButtonClick(CurPageID: Integer): Boolean;
begin
  Result := (not ExecutionStarted) and (not Preparing);
end;

procedure CancelButtonClick(CurPageID: Integer; var Cancel, Confirm: Boolean);
begin
  Cancel := True;
  Confirm := False;
  if WorkerMayRun then
    Cancel := MsgBox('The backend may still be running. Close only this window and let the journaled transaction continue?' + #13#10 +
      'It will not be terminated. Keep job ID: ' + CurrentJob, mbConfirmation, MB_YESNO) = IDYES;
  if Cancel then StopPolling;
end;

procedure DeinitializeSetup;
begin
  StopPolling;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  NeedsRestart := False;
  Result := 'NONFUNCTIONAL PROTOTYPE: installation is disabled.';
end;
