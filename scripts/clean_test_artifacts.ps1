$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$artifactNames = @(".pytest_cache", ".pytest_cache_local", ".pytest_tmp")

foreach ($artifactName in $artifactNames) {
    $artifactPath = Join-Path $projectRoot $artifactName
    if (Test-Path -LiteralPath $artifactPath) {
        Write-Host "Removing $artifactPath"
        Remove-Item -LiteralPath $artifactPath -Recurse -Force -ErrorAction SilentlyContinue
    }
}
