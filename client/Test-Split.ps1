param([int]$Port=7897, [switch]$WithUdp)
$ErrorActionPreference='Stop'
if($Port -lt 1 -or $Port -gt 65535){throw 'Invalid proxy port'}
$proxy="http://127.0.0.1:$Port"
$failed=$false
foreach($url in @('https://www.google.com','https://github.com','https://www.baidu.com')){
    $output=& curl.exe -4 --proxy $proxy --silent --show-error --connect-timeout 10 --max-time 35 --head $url --output NUL --write-out '%{http_code}'
    $code=$LASTEXITCODE
    $http=([string]$output).Trim()
    Write-Output "$url HTTP=$http curl_exit=$code"
    if($code -ne 0 -or $http -ne '200'){$failed=$true}
}
if($WithUdp){
    & python (Join-Path $PSScriptRoot 'probe_socks_udp.py') --port $Port
    if($LASTEXITCODE -ne 0){$failed=$true}
}
if($failed){exit 1}
'PROXY_TESTS_PASSED; confirm DIRECT/SERVER routing in Clash Connections separately.'
