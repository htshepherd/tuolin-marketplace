param(
    [string]$FfmpegPath,
    [string]$MineruCommand,
    [string]$ProjectDir = ".",
    [string]$ConfigPath
)

$ErrorActionPreference = "Continue"

$selectedConfigPath = $null
if ($PSBoundParameters.ContainsKey("ConfigPath")) {
    $selectedConfigPath = $ConfigPath
    if (-not (Test-Path -LiteralPath $selectedConfigPath -PathType Leaf)) {
        Write-Error "Configured project file does not exist: $selectedConfigPath"
        exit 1
    }
}
else {
    $candidateConfigPath = Join-Path $ProjectDir "config\tuolin-kb.config.json"
    if (Test-Path -LiteralPath $candidateConfigPath -PathType Leaf) {
        $selectedConfigPath = $candidateConfigPath
    }
}

$projectConfig = $null
if ($null -ne $selectedConfigPath) {
    try {
        $projectConfig = Get-Content -LiteralPath $selectedConfigPath -Raw | ConvertFrom-Json
    }
    catch {
        Write-Error "Invalid project config '$selectedConfigPath': $($_.Exception.Message)"
        exit 1
    }
}

if (-not $PSBoundParameters.ContainsKey("MineruCommand")) {
    $MineruCommand = if ($null -ne $projectConfig.mineru_command) {
        [string]$projectConfig.mineru_command
    }
    else {
        "mineru"
    }
}

if (-not $PSBoundParameters.ContainsKey("FfmpegPath")) {
    $FfmpegPath = if ($null -ne $projectConfig.ffmpeg_path) {
        [string]$projectConfig.ffmpeg_path
    }
    else {
        "ffmpeg"
    }
}

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
