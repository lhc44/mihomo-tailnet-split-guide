param([Parameter(Mandatory=$true)][string]$Backup, [switch]$CheckOnly)
$ErrorActionPreference='Stop'
$manifest=Get-Content -LiteralPath (Join-Path $Backup 'manifest.json') -Raw | ConvertFrom-Json
$allowed=@('verge.yaml','profiles.yaml','config.yaml','clash-verge.yaml','dns_config.yaml')
foreach($r in $manifest){
    if($r.name -notin $allowed){throw 'Invalid backup file name'}
    if((Get-FileHash -LiteralPath (Join-Path $Backup $r.name)).Hash -ne $r.sha256){throw 'Backup hash mismatch'}
}
if($CheckOnly){'BACKUP_HASHES_VALID; no files changed'; exit 0}
if(Get-Process -Name 'clash-verge','verge-mihomo','verge-mihomo-alpha' -ErrorAction SilentlyContinue){
    throw 'Turn off system proxy and TUN, then fully exit Clash from the tray before restoring.'
}
$app=Join-Path $env:APPDATA 'io.github.clash-verge-rev.clash-verge-rev'
foreach($r in $manifest){
    Copy-Item -LiteralPath (Join-Path $Backup $r.name) -Destination (Join-Path $app $r.name) -Force
    if((Get-FileHash -LiteralPath (Join-Path $app $r.name)).Hash -ne $r.sha256){throw 'Restore hash mismatch'}
}
'CLASH_SETTINGS_RESTORED; reconnect your original Tailscale fallback manually if needed.'
