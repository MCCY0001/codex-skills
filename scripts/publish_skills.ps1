param(
    [string]$SourceRoot = "C:\Dev\codex-skills\skills",
    [string]$TargetRoot = "C:\Users\mccy0\.codex\skills",
    [string[]]$SkillName
)

$ErrorActionPreference = "Stop"

function Copy-SkillTree {
    param(
        [string]$SourcePath,
        [string]$TargetPath
    )

    Get-ChildItem -LiteralPath $SourcePath -Force | ForEach-Object {
        if ($_.PSIsContainer) {
            if ($_.Name -eq "__pycache__") {
                return
            }

            $childTarget = Join-Path $TargetPath $_.Name
            New-Item -ItemType Directory -Force -Path $childTarget | Out-Null
            Copy-SkillTree -SourcePath $_.FullName -TargetPath $childTarget
            return
        }

        if ($_.Extension -eq ".pyc") {
            return
        }

        Copy-Item -LiteralPath $_.FullName -Destination $TargetPath -Force
    }
}

if (-not (Test-Path -LiteralPath $SourceRoot)) {
    throw "Source root not found: $SourceRoot"
}

if (-not (Test-Path -LiteralPath $TargetRoot)) {
    throw "Target root not found: $TargetRoot"
}

$skills =
if ($SkillName -and $SkillName.Count -gt 0) {
    $SkillName
} else {
    Get-ChildItem -LiteralPath $SourceRoot -Directory | Select-Object -ExpandProperty Name
}

foreach ($name in $skills) {
    $sourcePath = Join-Path $SourceRoot $name
    $targetPath = Join-Path $TargetRoot $name

    if (-not (Test-Path -LiteralPath $sourcePath)) {
        throw "Skill source not found: $sourcePath"
    }

    if (Test-Path -LiteralPath $targetPath) {
        Remove-Item -Recurse -Force -LiteralPath $targetPath
    }

    New-Item -ItemType Directory -Force -Path $targetPath | Out-Null
    Copy-SkillTree -SourcePath $sourcePath -TargetPath $targetPath
    Write-Output "Published $name"
}
