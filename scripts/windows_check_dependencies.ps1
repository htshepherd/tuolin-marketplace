param(
    [string]$FfmpegPath = "ffmpeg",
    [string]$MineruCommand = "mineru"
)

$ErrorActionPreference = "Continue"

function Test-Command {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Command
    )

    $found = Get-Command $Command -ErrorAction SilentlyContinue
    if ($null -eq $found) {
        [PSCustomObject]@{
            name = $Name
            command = $Command
            available = $false
            path = $null
        }
        return
    }

    [PSCustomObject]@{
        name = $Name
        command = $Command
        available = $true
        path = $found.Source
    }
}

$checks = @(
    Test-Command -Name "Git" -Command "git"
    Test-Command -Name "Python" -Command "python"
    Test-Command -Name "MinerU" -Command $MineruCommand
    Test-Command -Name "ffmpeg" -Command $FfmpegPath
)

$checks | ConvertTo-Json -Depth 3

$missing = $checks | Where-Object { -not $_.available }
if ($missing.Count -gt 0) {
    Write-Host ""
    Write-Host "Missing dependencies:" -ForegroundColor Yellow
    $missing | ForEach-Object { Write-Host ("- " + $_.name + " (" + $_.command + ")") }
    exit 1
}

exit 0

