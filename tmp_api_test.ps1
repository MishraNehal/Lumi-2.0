function Invoke-Api {
    param([string]$Method,[string]$Url,[hashtable]$Headers,$Body)
    try {
        $params=@{Method=$Method;Uri=$Url;ErrorAction='Stop'}
        if($Headers){$params.Headers=$Headers}
        if($null -ne $Body){$params.Body=($Body|ConvertTo-Json -Depth 10);$params.ContentType='application/json'}
        $resp=Invoke-WebRequest @params
        [PSCustomObject]@{status=[int]$resp.StatusCode;body=$resp.Content}
    } catch {
        $status=$null; $content=$_.Exception.Message
        if($_.Exception.Response){
            $status=[int]$_.Exception.Response.StatusCode
            try {
                $reader=New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
                $content=$reader.ReadToEnd(); $reader.Close()
            } catch {}
        }
        [PSCustomObject]@{status=$status;body=$content}
    }
}
$base='http://127.0.0.1:8000'; $results=[ordered]@{}
$s1=Invoke-Api -Method 'POST' -Url "$base/api/v1/auth/login" -Body @{email='nehalmishra2005@gmai.com';password='LumiTest@12345'}
$results.step1=$s1
$token=$null
try { $p=$s1.body|ConvertFrom-Json; if($p.access_token){$token=$p.access_token} elseif($p.tokens.access_token){$token=$p.tokens.access_token} } catch {}
if($token){
    $headers=@{Authorization="Bearer $token"}
    $s2=Invoke-Api -Method 'GET' -Url "$base/api/v1/documents/" -Headers $headers
    $results.step2=$s2
    $docId=$null
    try {
        $parsed=$s2.body|ConvertFrom-Json
        $docObj=$null
        if($parsed -is [System.Array] -and $parsed.Count -gt 0){$docObj=$parsed[0]}
        elseif($parsed.documents -and $parsed.documents.Count -gt 0){$docObj=$parsed.documents[0]}
        elseif($parsed.data -is [System.Array] -and $parsed.data.Count -gt 0){$docObj=$parsed.data[0]}
        elseif($parsed.items -is [System.Array] -and $parsed.items.Count -gt 0){$docObj=$parsed.items[0]}
        if($docObj){ if($docObj.document_id){$docId=$docObj.document_id} elseif($docObj.id){$docId=$docObj.id} }
    } catch {}
    if($docId){
        $results.step3=Invoke-Api -Method 'POST' -Url "$base/api/v1/documents/$docId/reprocess" -Headers $headers
        $results.step4=Invoke-Api -Method 'DELETE' -Url "$base/api/v1/documents/$docId" -Headers $headers
        $results.step5=Invoke-Api -Method 'GET' -Url "$base/api/v1/documents/" -Headers $headers
    } else {
        $results.step3=[PSCustomObject]@{status='SKIPPED';body='No document_id found from list response'}
        $results.step4=[PSCustomObject]@{status='SKIPPED';body='No document_id found from list response'}
        $results.step5=Invoke-Api -Method 'GET' -Url "$base/api/v1/documents/" -Headers $headers
    }
} else {
    $results.step2=[PSCustomObject]@{status='SKIPPED';body='No access token from login response'}
    $results.step3=[PSCustomObject]@{status='SKIPPED';body='No access token from login response'}
    $results.step4=[PSCustomObject]@{status='SKIPPED';body='No access token from login response'}
    $results.step5=[PSCustomObject]@{status='SKIPPED';body='No access token from login response'}
}
$results.GetEnumerator() | ForEach-Object {
    $name=$_.Key; $status=$_.Value.status; $body=[string]$_.Value.body
    if($body.Length -gt 500){$body=$body.Substring(0,500)+'...<truncated>'}
    "${name}_status=$status"
    "${name}_body=$body"
}
