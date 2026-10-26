param([Parameter(Mandatory=$true)][string]$Destination)
$ErrorActionPreference='Stop'
$app=Join-Path $env:APPDATA 'io.github.clash-verge-rev.clash-verge-rev'
if(Test-Path -LiteralPath $Destination){throw 'Use a new private backup directory'}
New-Item -ItemType Directory -Path $Destination | Out-Null
$files=@('verge.yaml','profiles.yaml','config.yaml','clash-verge.yaml','dns_config.yaml')
$manifest=@()
foreach($file in $files){
    $source=Join-Path $app $file
    if(Test-Path -LiteralPath $source){
        Copy-Item -LiteralPath $source -Destination (Join-Path $Destination $file)
        $manifest+=@{name=$file;sha256=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash}
    }
}
$manifest | ConvertTo-Json -AsArray | Set-Content -LiteralPath (Join-Path $Destination 'manifest.json') -Encoding utf8
'PRIVATE_BACKUP_CREATED; contains local settings, never upload it.'
