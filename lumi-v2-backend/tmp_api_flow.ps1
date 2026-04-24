function Invoke-Api {
    param(
        [string]$Method,
        [string]$Uri,
        [hashtable]$Headers,
        [object]$Body = $null
    )
    try {
        if ($null -ne $Body) {
            $resp = Invoke-WebRequest -Uri $Uri -Method $Method -Headers $Headers -ContentType 'application/json' -Body ($Body | ConvertTo-Json -Depth 10) -SkipHttpErrorCheck
        } else {
            $resp = Invoke-WebRequest -Uri $Uri -Method $Method -Headers $Headers -SkipHttpErrorCheck
        }
        [pscustomobject]@{ Status = [int]$resp.StatusCode; Content = [string]$resp.Content }
    } catch {
        [pscustomobject]@{ Status = -1; Content = $_.Exception.Message }
    }
}

$base = 'http://127.0.0.1:8000'
$login = Invoke-Api -Method 'POST' -Uri "$base/api/v1/auth/login" -Headers @{} -Body @{ email = 'nehalmishra2005@gmai.com'; password = 'LumiTest@12345' }
"LOGIN_STATUS=$($login.Status)"
$loginCompact = $login.Content
if ($loginCompact.Length -gt 240) { $loginCompact = $loginCompact.Substring(0,240) + '...' }
"LOGIN_BODY=$loginCompact"

$token = $null
try {
    $lj = $login.Content | ConvertFrom-Json
    foreach ($k in @('access_token','token','jwt','id_token')) {
        if ($lj.PSObject.Properties.Name -contains $k -and $lj.$k) { $token = [string]$lj.$k; break }
    }
    if (-not $token -and ($lj.PSObject.Properties.Name -contains 'tokens')) {
        $t = $lj.tokens
        foreach ($k in @('access_token','token','jwt','id_token')) {
            if ($t.PSObject.Properties.Name -contains $k -and $t.$k) { $token = [string]$t.$k; break }
        }
    }
    if (-not $token -and ($lj.PSObject.Properties.Name -contains 'data')) {
        $d = $lj.data
        foreach ($k in @('access_token','token','jwt','id_token')) {
            if ($d.PSObject.Properties.Name -contains $k -and $d.$k) { $token = [string]$d.$k; break }
        }
    }
} catch {}
"TOKEN_EXTRACTED=$([bool]$token)"
if ($token) { "TOKEN_PREFIX=$($token.Substring(0,[Math]::Min(24,$token.Length)))" }

$headers = if ($token) { @{ Authorization = "Bearer $token" } } else { @{} }
$list1 = Invoke-Api -Method 'GET' -Uri "$base/api/v1/documents/" -Headers $headers
"LIST1_STATUS=$($list1.Status)"
$list1Compact = $list1.Content
if ($list1Compact.Length -gt 320) { $list1Compact = $list1Compact.Substring(0,320) + '...' }
"LIST1_BODY=$list1Compact"

$firstId = $null
$cand = $null
try {
    $obj = $list1.Content | ConvertFrom-Json
    if ($obj -is [System.Array]) {
        if ($obj.Count -gt 0) { $cand = $obj[0] }
    } elseif ($obj.PSObject.Properties.Name -contains 'documents') {
        if ($obj.documents.Count -gt 0) { $cand = $obj.documents[0] }
    } elseif ($obj.PSObject.Properties.Name -contains 'items') {
        if ($obj.items.Count -gt 0) { $cand = $obj.items[0] }
    } elseif ($obj.PSObject.Properties.Name -contains 'data') {
        if ($obj.data -is [System.Array] -and $obj.data.Count -gt 0) { $cand = $obj.data[0] }
        elseif ($obj.data -and $obj.data.PSObject.Properties.Name -contains 'documents' -and $obj.data.documents.Count -gt 0) { $cand = $obj.data.documents[0] }
    }
    if ($cand) {
        foreach ($idKey in @('document_id','id','_id','uuid')) {
            if ($cand.PSObject.Properties.Name -contains $idKey -and $cand.$idKey) { $firstId = [string]$cand.$idKey; break }
        }
    }
} catch {}
"FIRST_DOCUMENT_ID=$firstId"

if ($firstId) {
    $reprocess = Invoke-Api -Method 'POST' -Uri "$base/api/v1/documents/$firstId/reprocess" -Headers $headers
    "REPROCESS_STATUS=$($reprocess.Status)"
    $rCompact = $reprocess.Content
    if ($rCompact.Length -gt 220) { $rCompact = $rCompact.Substring(0,220) + '...' }
    "REPROCESS_BODY=$rCompact"

    $delete = Invoke-Api -Method 'DELETE' -Uri "$base/api/v1/documents/$firstId" -Headers $headers
    "DELETE_STATUS=$($delete.Status)"
    $dCompact = $delete.Content
    if ($dCompact.Length -gt 220) { $dCompact = $dCompact.Substring(0,220) + '...' }
    "DELETE_BODY=$dCompact"

    $list2 = Invoke-Api -Method 'GET' -Uri "$base/api/v1/documents/" -Headers $headers
    "LIST2_STATUS=$($list2.Status)"
    $l2Compact = $list2.Content
    if ($l2Compact.Length -gt 320) { $l2Compact = $l2Compact.Substring(0,320) + '...' }
    "LIST2_BODY=$l2Compact"
}
