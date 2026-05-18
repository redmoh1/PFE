$ErrorActionPreference = 'Stop'
$base = 'http://127.0.0.1:8001'

$admin = Invoke-RestMethod -Method Post -Uri "$base/api/auth/login" -ContentType 'application/json' -Body '{"email":"admin@acme.com","password":"admin123"}'
$adminHeaders = @{ Authorization = "Bearer $($admin.access_token)"; 'X-Company-ID'='Acme Corp' }

$branches = Invoke-RestMethod -Method Get -Uri "$base/api/branches" -Headers $adminHeaders
Write-Output "admin_branch_count=$($branches.Count)"

$tempName = "Smoke Branch $(Get-Date -Format 'HHmmss')"
$created = Invoke-RestMethod -Method Post -Uri "$base/api/branches" -Headers $adminHeaders -ContentType 'application/json' -Body (@{name=$tempName; city='Test City'; manager_id=$null} | ConvertTo-Json)
Write-Output "created_branch_id=$($created.id)"

$updated = Invoke-RestMethod -Method Put -Uri "$base/api/branches/$($created.id)" -Headers $adminHeaders -ContentType 'application/json' -Body (@{city='Updated City'} | ConvertTo-Json)
Write-Output "updated_branch_city=$($updated.city)"

$analyticsCode = 200
try { $null = Invoke-RestMethod -Method Get -Uri "$base/api/branches/1/analytics" -Headers $adminHeaders } catch { $analyticsCode = $_.Exception.Response.StatusCode.value__ }
Write-Output "branch_analytics_status=$analyticsCode"

$null = Invoke-RestMethod -Method Delete -Uri "$base/api/branches/$($created.id)" -Headers $adminHeaders
Write-Output "deleted_branch_id=$($created.id)"

$mgr = Invoke-RestMethod -Method Post -Uri "$base/api/auth/login" -ContentType 'application/json' -Body '{"email":"manager.setif@acme.com","password":"admin123"}'
$mgrHeaders = @{ Authorization = "Bearer $($mgr.access_token)"; 'X-Company-ID'='Acme Corp'; 'X-Branch-ID'='2' }
$crossBranchCode = 200
try { $null = Invoke-RestMethod -Method Get -Uri "$base/api/datasets" -Headers $mgrHeaders } catch { $crossBranchCode = $_.Exception.Response.StatusCode.value__ }
Write-Output "manager_cross_branch_status=$crossBranchCode"
