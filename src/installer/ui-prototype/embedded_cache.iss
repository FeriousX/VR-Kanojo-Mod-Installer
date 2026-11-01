// Persistent resources only. No game target is handled by these routines.
function GetResourceAttributes(Name: String): LongWord;
  external 'GetFileAttributesW@kernel32.dll stdcall';

procedure RequireSafeDirectory(Name: String);
var Attributes: LongWord; Parent: String;
begin
  Parent := ExtractFileDir(Name);
  if (Parent <> Name) and (Length(Name) > 3) then RequireSafeDirectory(Parent);
  Attributes := GetResourceAttributes(Name);
  if Attributes = $FFFFFFFF then
  begin
    if not CreateDir(Name) then RaiseException('Cannot create per-user resource directory: ' + Name);
    Attributes := GetResourceAttributes(Name);
  end;
  if ((Attributes and $400) <> 0) or ((Attributes and $10) = 0) then
    RaiseException('Unsafe resource directory (link/reparse point or non-directory): ' + Name);
end;

function KnownResource(Name: String; IsDirectory: Boolean): Boolean;
var I: Integer;
begin
  Result := False;
  for I := 0 to ResourceCount - 1 do
  begin
    if IsDirectory then
    begin
      if Pos(Lowercase(Name + '\'), Lowercase(ResourceNames[I])) = 1 then Result := True;
    end
    else if Lowercase(Name) = Lowercase(ResourceNames[I]) then Result := True;
  end;
end;

procedure CheckResourceInventory(Root, Relative: String);
var Rec: TFindRec; Name, Full: String; IsDirectory: Boolean;
begin
  if FindFirst(Root + '\' + Relative + '*', Rec) then
  try
    repeat
      if (Rec.Name <> '.') and (Rec.Name <> '..') then
      begin
        Name := Relative + Rec.Name;
        Full := Root + '\' + Name;
        if (Rec.Attributes and $400) <> 0 then RaiseException('Reparse point in backend cache: ' + Full);
        IsDirectory := (Rec.Attributes and $10) <> 0;
        if not KnownResource(Name, IsDirectory) then RaiseException('Unexpected backend resource: ' + Full);
        if IsDirectory then CheckResourceInventory(Root, Name + '\');
      end;
    until not FindNext(Rec);
  finally
    FindClose(Rec);
  end;
end;

procedure VerifyResourceCache(Root: String);
var I: Integer; Full: String;
begin
  RequireSafeDirectory(Root);
  for I := 0 to ResourceCount - 1 do
  begin
    Full := Root + '\' + ResourceNames[I];
    RequireSafeDirectory(ExtractFileDir(Full));
    if not FileExists(Full) then RaiseException('Missing cached backend resource: ' + Full);
    if (GetResourceAttributes(Full) and $400) <> 0 then RaiseException('Reparse point in backend resource: ' + Full);
    if Lowercase(GetSHA256OfFile(Full)) <> ResourceHashes[I] then
      RaiseException('Backend integrity check failed: ' + Full + '. Preserve state; do not execute or repair active resources.');
  end;
  CheckResourceInventory(Root, '');
end;

procedure PrepareEmbeddedBackend;
var Stage, Full: String; I: Integer;
begin
  InitResourceList;
  PersistentBase := ExpandConstant('{localappdata}\') + PersistentSuffix;
  CacheRoot := PersistentBase + '\packages\' + ResourceBundle;
  RequireSafeDirectory(PersistentBase + '\packages');
  if DirExists(CacheRoot) then
  begin
    VerifyResourceCache(CacheRoot);
    Exit;
  end;
  Stage := PersistentBase + '\packages\stage-' + Copy(GetSHA256OfString(
    GetDateTimeString('yyyymmddhhnnss', #0, #0) + IntToStr(Random(2147483647))), 1, 20);
  RequireSafeDirectory(Stage);
  for I := 0 to ResourceCount - 1 do
  begin
    Full := Stage + '\' + ResourceNames[I];
    if Length(Full) >= 260 then RaiseException('Per-user resource path exceeds supported length. Use a shorter Windows profile path; no installation authorized.');
    ExtractTemporaryFiles('{tmp}\VRKMI8A\' + ResourceNames[I]);
    if Lowercase(GetSHA256OfFile(ExpandConstant('{tmp}\VRKMI8A\') + ResourceNames[I])) <> ResourceHashes[I] then
      RaiseException('Embedded resource integrity failure: ' + ResourceNames[I]);
    RequireSafeDirectory(ExtractFileDir(Full));
    if not CopyFile(ExpandConstant('{tmp}\VRKMI8A\') + ResourceNames[I], Full, True) then
      RaiseException('Cannot stage verified resource: ' + Full);
  end;
  VerifyResourceCache(Stage);
  if not RenameFile(Stage, CacheRoot) then
  begin
    if not DirExists(CacheRoot) then RaiseException('Cannot publish persistent backend cache. Keep state unchanged.');
  end;
  VerifyResourceCache(CacheRoot);
end;
