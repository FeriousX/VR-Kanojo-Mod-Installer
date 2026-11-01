param([string]$CompilerPath, [string]$ExpectedCompilerSHA256, [switch]$PortableBackend)
$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$out = Join-Path $workspace 'out\Preview'
if ($PortableBackend) { $out = Join-Path $workspace 'out\Portable Preview' }
[void](New-Item -ItemType Directory -Path $out -Force)
$report = [ordered]@{profile='NONFUNCTIONAL_UI_PROTOTYPE';compiler_invoked=$false;installer_run=$false;status='BLOCKED';reason='';compiler=$null}
if (-not $CompilerPath) {
    $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($cmd) { $CompilerPath = $cmd.Source }
}
if (-not $CompilerPath -or -not (Test-Path -LiteralPath $CompilerPath -PathType Leaf)) {
    $report.reason='ISCC.exe unavailable. No compiler downloaded or installed; no EXE produced.'
    $report | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $out 'build-attempt.json')
    Write-Output $report.reason
    exit 2
}
$compiler = Get-Item -LiteralPath $CompilerPath
$hash = (Get-FileHash -LiteralPath $compiler.FullName -Algorithm SHA256).Hash
$signature = Get-AuthenticodeSignature -LiteralPath $compiler.FullName
if (-not $ExpectedCompilerSHA256 -or $hash -ne $ExpectedCompilerSHA256 -or $signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'CN=Pyrsys B\.V\.,') {
    throw 'Compiler must have an independently approved SHA-256 and valid Authenticode signature before execution.'
}
$engineVersion = (& $compiler.FullName --version | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $engineVersion -ne '7.1.1') { throw 'Only qualified Inno Setup engine 7.1.1 is allowed' }
$report.compiler=@{path=$compiler.FullName;version=$engineVersion;file_version=$compiler.VersionInfo.FileVersion;sha256=$hash;signer=$signature.SignerCertificate.Subject}
$report.compiler_invoked=$true
$report.command=@($compiler.FullName,'/ni','/ns','/DDEBUG','/DUI_PROTOTYPE',"/O$out",(Join-Path $PSScriptRoot 'preview.iss'))
if ($PortableBackend) {
    $bundle=Join-Path $workspace 'out\Portable Backend\HFBackend'
    if (-not (Test-Path "$bundle\HFBackend.exe")) {throw 'Qualified portable backend is missing'}
    if (Test-Path (Join-Path $out 'Backend')) {throw 'Refusing to overwrite an existing portable preview/backend state'}
    Copy-Item -LiteralPath $bundle -Destination (Join-Path $out 'Backend') -Recurse
    $report.profile='PORTABLE_SYNTHETIC_PREVIEW'
    $report.command=@($compiler.FullName,'/ni','/ns','/DDEBUG','/DUI_PROTOTYPE','/DPORTABLE_BACKEND','/FHF_UI_PHASE6A_PORTABLE_PREVIEW',"/O$out",(Join-Path $PSScriptRoot 'preview.iss'))
    & $compiler.FullName /ni /ns /DDEBUG /DUI_PROTOTYPE /DPORTABLE_BACKEND /FHF_UI_PHASE6A_PORTABLE_PREVIEW "/O$out" (Join-Path $PSScriptRoot 'preview.iss') > (Join-Path $out 'compiler.log') 2>&1
} else {
    & $compiler.FullName /ni /ns /DDEBUG /DUI_PROTOTYPE "/O$out" (Join-Path $PSScriptRoot 'preview.iss') > (Join-Path $out 'compiler.log') 2>&1
}
$report.compiler_exit_code=$LASTEXITCODE
if ($LASTEXITCODE -eq 0) {
    $artifact=Join-Path $out 'HF_UI_PREVIEW_PHASE5E4_SYNTHETIC.exe'
    if ($PortableBackend) {$artifact=Join-Path $out 'HF_UI_PHASE6A_PORTABLE_PREVIEW.exe'}
    if (-not (Test-Path -LiteralPath $artifact -PathType Leaf)) { throw 'Compiler reported success without expected artifact' }
    $report.status='COMPILED_NOT_RUN'
    $report.artifact=$artifact
    $report.sha256=(Get-FileHash -LiteralPath $artifact -Algorithm SHA256).Hash
} else { $report.reason='Compiler failed; inspect compiler.log' }
$report | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $out 'build-attempt.json')
if ($report.status -ne 'COMPILED_NOT_RUN') { exit 2 }
