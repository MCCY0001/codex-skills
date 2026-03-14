[CmdletBinding()]
param(
    [string]$SourceRoot,
    [string]$TargetRoot,
    [string]$BackupDir,
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$SkillName,
    [switch]$List,
    [switch]$WhatIfPreview,
    [switch]$NoClobber,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$cliPath = Join-Path $scriptRoot "skill_repo.py"

function Invoke-PythonCli {
    param(
        [string]$ScriptPath,
        [string[]]$CliArguments
    )

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        try {
            $probeOutput = & $python.Source -c "print('codex-python-ok')" 2>$null
            if ($LASTEXITCODE -eq 0 -and $probeOutput -match "codex-python-ok") {
                & $python.Source $ScriptPath @CliArguments
                return $true
            }
        } catch {
        }
    }

    $uv = Get-Command uv -ErrorAction SilentlyContinue
    if ($uv) {
        try {
            & $uv.Source run python $ScriptPath @CliArguments
            return $true
        } catch {
        }
    }

    return $false
}

function Get-DefaultSourceRoot {
    return [System.IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $scriptRoot) "skills"))
}

function Get-DefaultTargetRoot {
    if ($env:CODEX_HOME) {
        return [System.IO.Path]::GetFullPath((Join-Path $env:CODEX_HOME "skills"))
    }

    return [System.IO.Path]::GetFullPath((Join-Path $HOME ".codex\skills"))
}

function Resolve-RootPath {
    param(
        [string]$PathValue,
        [string]$Fallback
    )

    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        return $Fallback
    }

    return [System.IO.Path]::GetFullPath($PathValue)
}

function Test-SkillDirectory {
    param([string]$PathValue)

    return (Test-Path -LiteralPath $PathValue -PathType Container) -and (Test-Path -LiteralPath (Join-Path $PathValue "SKILL.md") -PathType Leaf)
}

function Get-SkillDirectories {
    param(
        [string]$SourceRootPath,
        [string[]]$Names
    )

    if (-not (Test-Path -LiteralPath $SourceRootPath -PathType Container)) {
        throw "Source root not found: $SourceRootPath"
    }

    if ($Names -and $Names.Count -gt 0) {
        $selected = @()
        foreach ($name in $Names) {
            $skillPath = Join-Path $SourceRootPath $name
            if (-not (Test-SkillDirectory -PathValue $skillPath)) {
                throw "Skill source not found or missing SKILL.md: $skillPath"
            }
            $selected += (Get-Item -LiteralPath $skillPath)
        }
        return $selected
    }

    return Get-ChildItem -LiteralPath $SourceRootPath -Directory |
        Where-Object { -not $_.Name.StartsWith(".") -and (Test-SkillDirectory -PathValue $_.FullName) } |
        Sort-Object Name
}

function Publish-SkillsWithPowerShell {
    param(
        [string]$ResolvedSourceRoot,
        [string]$ResolvedTargetRoot,
        [string]$ResolvedBackupDir,
        [string[]]$RequestedSkillNames,
        [switch]$ListOnly,
        [switch]$PreviewOnly,
        [switch]$PreventOverwrite,
        [switch]$ReplaceWithoutBackup
    )

    $skills = Get-SkillDirectories -SourceRootPath $ResolvedSourceRoot -Names $RequestedSkillNames
    if ($ListOnly) {
        foreach ($skill in $skills) {
            Write-Output $skill.Name
        }
        return
    }

    if ($PreventOverwrite -and $ReplaceWithoutBackup) {
        throw "--no-clobber and --force cannot be used together."
    }

    foreach ($skill in $skills) {
        $targetDir = Join-Path $ResolvedTargetRoot $skill.Name
        if (Test-Path -LiteralPath $targetDir) {
            if ($PreventOverwrite) {
                throw "Destination already exists and --no-clobber is set: $targetDir"
            }

            if ($ReplaceWithoutBackup) {
                if ($PreviewOnly) {
                    Write-Output "Would remove $targetDir"
                } else {
                    Remove-Item -LiteralPath $targetDir -Recurse -Force
                }
            } else {
                $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
                $backupTarget = Join-Path $ResolvedBackupDir "$($skill.Name)-$timestamp"
                if ($PreviewOnly) {
                    Write-Output "Would backup $targetDir -> $backupTarget"
                } else {
                    New-Item -ItemType Directory -Path $ResolvedBackupDir -Force | Out-Null
                    Move-Item -LiteralPath $targetDir -Destination $backupTarget
                    Write-Output "Backed up $($skill.Name) -> $backupTarget"
                }
            }
        }

        if ($PreviewOnly) {
            Write-Output "Would publish $($skill.FullName) -> $targetDir"
            continue
        }

        New-Item -ItemType Directory -Path $ResolvedTargetRoot -Force | Out-Null
        Copy-Item -LiteralPath $skill.FullName -Destination $targetDir -Recurse -Force
        Write-Output "Published $($skill.Name)"
    }
}

$arguments = @()
$usingPythonCli = $false

if ($List) {
    $arguments += @("list", "--catalog", "source", "--format", "names")
} else {
    $arguments += "publish"
    if ($SkillName -and $SkillName.Count -gt 0) {
        $arguments += $SkillName
    }
}

if ($SourceRoot) {
    $arguments += @("--source-root", $SourceRoot)
}

if ($TargetRoot) {
    $arguments += @("--runtime-path", $TargetRoot)
}

if ($BackupDir) {
    $arguments += @("--backup-dir", $BackupDir)
}

if ($WhatIfPreview) {
    $arguments += "--what-if"
}

if ($NoClobber) {
    $arguments += "--no-clobber"
}

if ($Force) {
    $arguments += "--force"
}

$usingPythonCli = Invoke-PythonCli -ScriptPath $cliPath -CliArguments $arguments
if ($usingPythonCli) {
    exit $LASTEXITCODE
}

$resolvedSourceRoot = Resolve-RootPath -PathValue $SourceRoot -Fallback (Get-DefaultSourceRoot)
$resolvedTargetRoot = Resolve-RootPath -PathValue $TargetRoot -Fallback (Get-DefaultTargetRoot)
$resolvedBackupDir = Resolve-RootPath -PathValue $BackupDir -Fallback (Join-Path $resolvedTargetRoot ".backup")

Publish-SkillsWithPowerShell `
    -ResolvedSourceRoot $resolvedSourceRoot `
    -ResolvedTargetRoot $resolvedTargetRoot `
    -ResolvedBackupDir $resolvedBackupDir `
    -RequestedSkillNames $SkillName `
    -ListOnly:$List `
    -PreviewOnly:$WhatIfPreview `
    -PreventOverwrite:$NoClobber `
    -ReplaceWithoutBackup:$Force

exit 0
