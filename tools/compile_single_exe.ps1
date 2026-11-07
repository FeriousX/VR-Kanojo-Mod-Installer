param([ValidateSet('Q8','A8','B81','B82','RC83','RC1','FINAL100','FINAL110','FINAL111')][string]$Kind='FINAL111', [string]$CompilerPath)
$ErrorActionPreference='Stop'
$w=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if($Kind -in @('FINAL110','FINAL111') -and -not $CompilerPath){throw ($Kind+' requires explicit qualified -CompilerPath')}
$compiler=if($CompilerPath){(Resolve-Path -LiteralPath $CompilerPath).Path}else{Join-Path $w 'cache\inno-7.1.1-x64\portable\ISCC.exe'}
if((Get-FileHash -LiteralPath $compiler -Algorithm SHA256).Hash -ne 'E0F9F1DC32032650C6629F6DEE41EB6D20BA140E4E3C07C25D8A24F9BA781644'){throw 'Compiler hash mismatch'}
$sig=Get-AuthenticodeSignature -LiteralPath $compiler
if($sig.Status -ne 'Valid' -or $sig.SignerCertificate.Subject -notmatch 'CN=Pyrsys B\.V\.,'){throw 'Compiler signature not qualified'}
if((& $compiler --version | Out-String).Trim() -ne '7.1.1'){throw 'Compiler version mismatch'}
$name=if($Kind -eq 'FINAL111'){'VRK-Mod-Installer-v1.1.1'}elseif($Kind -eq 'FINAL110'){'VRK-Mod-Installer-v1.1.0'}elseif($Kind -eq 'FINAL100'){'VRK-Mod-Installer-v1.0.0'}elseif($Kind -eq 'RC1'){'VRK-Mod-Installer-v1.0.0-rc.1'}elseif($Kind -eq 'RC83'){'VRK-Mod-Installer-v1.0.0-rc.8C3-Private'}elseif($Kind -eq 'B82'){'VRK-Mod-Installer-Phase8B2-Private'}elseif($Kind -eq 'B81'){'VRK-Mod-Installer-Phase8B1-Private'}elseif($Kind -eq 'Q8'){'VRK-Mod-Installer-Phase8A-Fixture'}else{'VRK-Mod-Installer-Phase8A-Private'}
$out=if($Kind -eq 'FINAL111'){Join-Path $w 'out\FinalRelease_v1.1.1'}elseif($Kind -eq 'FINAL110'){Join-Path $w 'out\FinalRelease_v1.1.0'}elseif($Kind -eq 'FINAL100'){Join-Path $w 'out\FinalRelease_v1.0.0'}elseif($Kind -eq 'RC1'){Join-Path $w 'out\PublicReleaseCandidate'}elseif($Kind -eq 'RC83'){Join-Path $w 'out\ReleaseCandidate_8C3'}elseif($Kind -eq 'B82'){Join-Path $w 'out\SingleEXE_Phase8B2'}elseif($Kind -eq 'B81'){Join-Path $w 'out\SingleEXE_Phase8B1'}elseif($Kind -eq 'A8'){Join-Path $w 'out\SingleEXE_Phase8A'}else{Join-Path $w 'out\phase8a'}
if($Kind -eq 'FINAL110'){
 $cfg=Get-Content -LiteralPath (Join-Path $w 'manifests\final-v1.1.0.json') -Raw | ConvertFrom-Json
 if($cfg.version -ne '1.1.0' -or $cfg.exe_name -ne 'VRK-Mod-Installer-v1.1.0.exe'){throw 'Final release configuration mismatch'}
 if(-not (Test-Path -LiteralPath (Join-Path $w 'build\FINAL110\single.iss'))){throw 'Prepare and qualify the FINAL110 resource bundle first'}
}
if($Kind -eq 'FINAL111'){
 $cfg=Get-Content -LiteralPath (Join-Path $w 'manifests\final-v1.1.1.json') -Raw | ConvertFrom-Json
 if($cfg.version -ne '1.1.1' -or $cfg.exe_name -ne 'VRK-Mod-Installer-v1.1.1.exe'){throw 'Final release configuration mismatch'}
 if(-not (Test-Path -LiteralPath (Join-Path $w 'build\FINAL111\single.iss'))){throw 'Prepare and qualify the FINAL111 resource bundle first'}
}
New-Item -ItemType Directory -Path $out -Force | Out-Null
if(Test-Path (Join-Path $out ($name+'.exe'))){throw 'Refusing artifact overwrite'}
$report=if($Kind -eq 'FINAL111'){'final-v1.1.1'}elseif($Kind -eq 'FINAL110'){'final-v1.1.0'}elseif($Kind -eq 'FINAL100'){'final-v1.0.0'}elseif($Kind -eq 'RC1'){'public-rc1'}elseif($Kind -eq 'RC83'){'phase8c3'}elseif($Kind -eq 'B82'){'phase8b2'}else{'phase8b1'}
& $compiler /ni /ns /DDEBUG /DUI_PROTOTYPE /DPORTABLE_BACKEND /DREAL_COMPONENTS /DPRIVATE_GAME "/F$name" "/O$out" "$w\build\$Kind\single.iss" > "$w\out\$report\$Kind-inno-build.log" 2>&1
if($LASTEXITCODE){Get-Content "$w\out\$report\$Kind-inno-build.log" -Tail 20;throw 'Single EXE compilation failed'}
Get-FileHash -LiteralPath (Join-Path $out ($name+'.exe')) -Algorithm SHA256
