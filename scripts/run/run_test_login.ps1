# HB_SCRIPT_KIND=RUNNER
# HB_SCRIPT_SCOPE=infra
# HB_SCRIPT_SIDE_EFFECTS=NET
# HB_SCRIPT_IDEMPOTENT=YES
# HB_SCRIPT_ENTRYPOINT=powershell -File scripts/run/run_test_login.ps1
# HB_SCRIPT_OUTPUTS=stdout
# Teste final de login
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "TESTE FINAL DE LOGIN - SUPER ADMIN" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$email = "adm@handballtrack.app"
$senha = "Admin@123!"

Write-Host "Credenciais:" -ForegroundColor Yellow
Write-Host "   Email: $email" -ForegroundColor White
Write-Host "   Senha: $senha" -ForegroundColor White

Write-Host "`nTestando login via API..." -ForegroundColor Yellow

try {
    $response = Invoke-WebRequest `
        -Uri "http://localhost:8000/api/v1/auth/login" `
        -Method POST `
        -Headers @{"Content-Type"="application/x-www-form-urlencoded"} `
        -Body "username=$email&password=$senha" `
        -UseBasicParsing `
        -ErrorAction Stop
    
    if ($response.StatusCode -eq 200) {
        $data = $response.Content | ConvertFrom-Json
        $token = $data.access_token.Substring(0, 50)
        
        Write-Host "`n✅ LOGIN BEM-SUCEDIDO!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "Status: $($response.StatusCode)" -ForegroundColor Green
        Write-Host "Token: $token..." -ForegroundColor White
        Write-Host "========================================`n" -ForegroundColor Cyan
        
        Write-Host "🎉 PODE FAZER LOGIN NO FRONTEND!" -ForegroundColor Green
        Write-Host "   URL: http://localhost:3000" -ForegroundColor Yellow
        Write-Host "   Email: $email" -ForegroundColor White
        Write-Host "   Senha: $senha" -ForegroundColor White
        Write-Host "`n========================================`n" -ForegroundColor Cyan
    }
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    Write-Host "`n❌ LOGIN FALHOU!" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "Status: $statusCode" -ForegroundColor Red
    Write-Host "Erro: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "========================================`n" -ForegroundColor Red
    
    if ($statusCode -eq 401) {
        Write-Host "⚠️  AÇÃO NECESSÁRIA:" -ForegroundColor Yellow
        Write-Host "   O hash da senha ainda está incorreto." -ForegroundColor White
        Write-Host "   Execute: python validate_and_fix_hash.py" -ForegroundColor White
        Write-Host "   Depois: Reinicie o backend`n" -ForegroundColor White
    }
}
