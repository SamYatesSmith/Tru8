# Analyze Clerk Keys
$envPath = ".env"

$pubKey = (Select-String -Path $envPath -Pattern 'NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=(.+)').Matches.Groups[1].Value
$secretKey = (Select-String -Path $envPath -Pattern 'CLERK_SECRET_KEY=(.+)' | Select-Object -First 1).Matches.Groups[1].Value

Write-Host "=== CLERK KEY ANALYSIS ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "Publishable Key:" -ForegroundColor Yellow
Write-Host "  Prefix: $($pubKey.Substring(0, 8))"
Write-Host "  Length: $($pubKey.Length) characters"
Write-Host "  Full: $pubKey"
Write-Host ""

Write-Host "Secret Key:" -ForegroundColor Yellow
Write-Host "  Prefix: $($secretKey.Substring(0, 8))"
Write-Host "  Length: $($secretKey.Length) characters"
Write-Host "  Full: $secretKey"
Write-Host ""

# Decode publishable key to get instance domain
try {
    $decoded = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($pubKey.Substring(8)))
    Write-Host "Decoded Publishable Key (Instance):" -ForegroundColor Green
    Write-Host "  $decoded"
} catch {
    Write-Host "Could not decode publishable key (invalid base64)" -ForegroundColor Red
}
Write-Host ""

Write-Host "=== INSTRUCTIONS ===" -ForegroundColor Cyan
Write-Host "1. Both keys should start with 'pk_test_' and 'sk_test_' (test mode)"
Write-Host "2. Keys must be from the SAME Clerk instance"
Write-Host "3. To verify, go to: https://dashboard.clerk.com"
Write-Host "4. Navigate to: Your App -> API Keys"
Write-Host "5. Copy BOTH keys from the same environment"
