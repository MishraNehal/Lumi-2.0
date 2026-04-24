Set-Location "D:\Projects\LUMI 2.0\lumi-v2-backend"

$listeners = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($listeners) {
  foreach ($procId in $listeners) {
    try { Stop-Process -Id $procId -Force -ErrorAction Stop } catch {}
  }
}

$pyCmd = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } elseif (Test-Path "C:/Python312/python.exe") { "C:/Python312/python.exe" } else { $null }
if (-not $pyCmd) {
  Write-Output "STEP1_SERVER=FAIL reason=no_python"
  exit 0
}

$uvicornLog = "uvicorn_verify.log"
if (Test-Path $uvicornLog) { Remove-Item $uvicornLog -Force }
$proc = Start-Process -FilePath $pyCmd -ArgumentList "-m uvicorn app.main:app --host 0.0.0.0 --port 8000" -WorkingDirectory (Get-Location).Path -RedirectStandardOutput $uvicornLog -RedirectStandardError $uvicornLog -PassThru

$openapiReady = $false
for ($i = 0; $i -lt 60; $i++) {
  try {
    $null = Invoke-RestMethod -Uri "http://127.0.0.1:8000/openapi.json" -Method GET -TimeoutSec 2
    $openapiReady = $true
    break
  } catch {}
}
if (-not $openapiReady) {
  $tail = if (Test-Path $uvicornLog) { (Get-Content $uvicornLog -Tail 20 -ErrorAction SilentlyContinue) -join " | " } else { "no_log" }
  Write-Output "STEP1_SERVER=FAIL reason=openapi_unreachable log=$tail"
  exit 0
}
Write-Output "STEP1_SERVER=PASS"

$openapi = Invoke-RestMethod -Uri "http://127.0.0.1:8000/openapi.json" -Method GET -TimeoutSec 10
$paths = $openapi.paths.PSObject.Properties.Name
$loginPath = $paths | Where-Object { $_ -match "login" -and $openapi.paths.$_.post } | Select-Object -First 1
if (-not $loginPath) { $loginPath = "/api/v1/auth/login" }

$loginUrl = "http://127.0.0.1:8000$loginPath"
$token = $null
try {
  $loginBodyJson = @{ email = "nehalmishra2005@gmai.com"; password = "LumiTest@12345" } | ConvertTo-Json
  $loginResp = Invoke-RestMethod -Uri $loginUrl -Method POST -Body $loginBodyJson -ContentType "application/json" -TimeoutSec 20
  $token = $loginResp.access_token
} catch {
  try {
    $form = "username=nehalmishra2005%40gmai.com&password=LumiTest%4012345"
    $loginResp = Invoke-RestMethod -Uri $loginUrl -Method POST -Body $form -ContentType "application/x-www-form-urlencoded" -TimeoutSec 20
    $token = $loginResp.access_token
  } catch {}
}
if (-not $token) {
  Write-Output "STEP2_LOGIN=FAIL path=$loginPath"
  exit 0
}
Write-Output "STEP2_LOGIN=PASS token_prefix=$($token.Substring(0,[Math]::Min(12,$token.Length)))"

$headers = @{ Authorization = "Bearer $token" }
$listUrl = "http://127.0.0.1:8000/api/v1/documents/?page=1&page_size=1"
try {
  $docResp = Invoke-RestMethod -Uri $listUrl -Method GET -Headers $headers -TimeoutSec 30
} catch {
  Write-Output "STEP3_LIST=FAIL reason=request_error"
  exit 0
}

$total = if ($null -ne $docResp.total) { $docResp.total } else { $null }
$page = if ($null -ne $docResp.page) { $docResp.page } else { $null }
$pageSize = if ($null -ne $docResp.page_size) { $docResp.page_size } elseif ($null -ne $docResp.pageSize) { $docResp.pageSize } else { $null }
$hasNext = if ($null -ne $docResp.has_next) { $docResp.has_next } elseif ($null -ne $docResp.hasNext) { $docResp.hasNext } else { $null }
Write-Output "STEP3_LIST=PASS total=$total page=$page page_size=$pageSize has_next=$hasNext"

$items = @()
if ($docResp.items) { $items = @($docResp.items) }
elseif ($docResp.documents) { $items = @($docResp.documents) }
elseif ($docResp.data) { $items = @($docResp.data) }

if ($items.Count -lt 1) {
  Write-Output "STEP4_DELETE=SKIP reason=no_documents"
  Write-Output "STEP5_REPROCESS=SKIP reason=no_documents"
  exit 0
}

$firstDoc = $items[0]
$docId = $null
foreach ($k in @("document_id","id","uuid","_id")) {
  if ($firstDoc.PSObject.Properties.Name -contains $k -and $firstDoc.$k) { $docId = [string]$firstDoc.$k; break }
}
if (-not $docId) {
  Write-Output "STEP4_DELETE=FAIL reason=no_document_id"
  Write-Output "STEP5_REPROCESS=FAIL reason=no_document_id"
  exit 0
}

$deleteUrl = "http://127.0.0.1:8000/api/v1/documents/$docId"
$deleteOk = $true
try {
  $null = Invoke-RestMethod -Uri $deleteUrl -Method DELETE -Headers $headers -TimeoutSec 30
} catch {
  $deleteOk = $false
}
if (-not $deleteOk) {
  Write-Output "STEP4_DELETE=FAIL document_id=$docId"
} else {
  $confirmUrl = "http://127.0.0.1:8000/api/v1/documents/?include_deleted=true&page=1&page_size=5"
  $confirm = Invoke-RestMethod -Uri $confirmUrl -Method GET -Headers $headers -TimeoutSec 30
  $cItems = @()
  if ($confirm.items) { $cItems = @($confirm.items) }
  elseif ($confirm.documents) { $cItems = @($confirm.documents) }
  elseif ($confirm.data) { $cItems = @($confirm.data) }

  $foundDeleted = $false
  foreach ($d in $cItems) {
    $cid = $null
    foreach ($k in @("document_id","id","uuid","_id")) { if ($d.PSObject.Properties.Name -contains $k -and $d.$k) { $cid = [string]$d.$k; break } }
    $isDel = $false
    if ($d.PSObject.Properties.Name -contains "is_deleted") { $isDel = [bool]$d.is_deleted }
    elseif ($d.PSObject.Properties.Name -contains "isDeleted") { $isDel = [bool]$d.isDeleted }
    if ($cid -eq $docId -and $isDel) { $foundDeleted = $true; break }
  }
  if ($foundDeleted) { Write-Output "STEP4_DELETE=PASS document_id=$docId is_deleted=true" }
  else { Write-Output "STEP4_DELETE=FAIL document_id=$docId is_deleted_not_confirmed" }
}

$reprocessUrl = "http://127.0.0.1:8000/api/v1/documents/$docId/reprocess"
try {
  $reprocessResp = Invoke-RestMethod -Uri $reprocessUrl -Method POST -Headers $headers -TimeoutSec 30
  $jobId = $reprocessResp.job_id
  $status = $reprocessResp.status
  $requestedAt = $reprocessResp.requested_at
  if ($jobId -and $status -and $requestedAt) {
    Write-Output "STEP5_REPROCESS=PASS document_id=$docId job_id=$jobId status=$status requested_at=$requestedAt"
  } else {
    Write-Output "STEP5_REPROCESS=FAIL document_id=$docId missing_fields job_id=$jobId status=$status requested_at=$requestedAt"
  }
} catch {
  Write-Output "STEP5_REPROCESS=FAIL document_id=$docId reason=request_error"
}
