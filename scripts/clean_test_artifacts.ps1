$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$projectPrefix = $projectRoot + [IO.Path]::DirectorySeparatorChar

function Remove-VerifiedProjectPath {
    param([Parameter(Mandatory = $true)][string]$LiteralPath)

    $resolved = (Resolve-Path -LiteralPath $LiteralPath).Path
    if (
        $resolved -eq $projectRoot -or
        -not $resolved.StartsWith(
            $projectPrefix,
            [StringComparison]::OrdinalIgnoreCase
        )
    ) {
        throw "Refusing to remove a path outside the verified project: $resolved"
    }
    Write-Host "Removing $resolved"
    try {
        Remove-Item -LiteralPath $resolved -Recurse -Force -ErrorAction Stop
    }
    catch {
        Write-Warning "Could not remove $resolved ($($_.Exception.Message))"
    }
}

$rootCaches = Get-ChildItem -LiteralPath $projectRoot -Force -Directory |
    Where-Object {
        $_.Name -like ".pytest_tmp*" -or
        $_.Name -like ".pytest_cache*"
    }
foreach ($item in $rootCaches) {
    Remove-VerifiedProjectPath -LiteralPath $item.FullName
}

$venvPattern = (Join-Path $projectRoot "venv") + "\*"
$dotVenvPattern = (Join-Path $projectRoot ".venv") + "\*"
$pythonCaches = Get-ChildItem -LiteralPath $projectRoot -Force -Recurse -Directory -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Name -eq "__pycache__" -and
        $_.FullName -notlike $venvPattern -and
        $_.FullName -notlike $dotVenvPattern
    }
foreach ($item in $pythonCaches) {
    if (Test-Path -LiteralPath $item.FullName) {
        Remove-VerifiedProjectPath -LiteralPath $item.FullName
    }
}

$temporaryLogs = Get-ChildItem -LiteralPath $projectRoot -Force -File |
    Where-Object {
        $_.Name -like "streamlit*.log" -or
        $_.Name -like ".streamlit*.log" -or
        $_.Name -like "phase*_streamlit*.log" -or
        $_.Name -eq "pytest_diagnostic.log"
    }
foreach ($item in $temporaryLogs) {
    Remove-VerifiedProjectPath -LiteralPath $item.FullName
}
