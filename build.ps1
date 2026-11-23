param(
    [ValidateSet("pack", "proto")]
    [string]$Target = "pack"
)

$ErrorActionPreference = "Stop"
$Blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

if ($Target -eq "pack") {
    Write-Host "=== [1/2] Building Batch 1 Pack (7 Weapons + 5 Rigged Survivors) ==="
    & $Blender -b --factory-startup -P "$Root\scripts\build_pack.py"

    Write-Host "=== [2/2] Rendering Weapons Sheet, 5 Survivor Sheets & Lineup ==="
    & $Blender -b --factory-startup -P "$Root\scripts\render_pack.py"
} else {
    Write-Host "=== [1/2] Building Prototype Survivor .blend and .glb ==="
    & $Blender -b --factory-startup -P "$Root\scripts\build_survivor.py"

    Write-Host "=== [2/2] Rendering Prototype Previews ==="
    & $Blender -b --factory-startup -P "$Root\scripts\render_preview.py"
}

Write-Host "=== DONE ==="
