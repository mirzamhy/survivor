param(
    [ValidateSet("pack", "proto", "vfx", "zombies", "mutant")]
    [string]$Target = "pack",
    [string]$Mutant = "rafflesia"
)

$ErrorActionPreference = "Stop"
$Blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

if ($Target -eq "pack") {
    Write-Host "=== [1/2] Building Batch 1 & 2 Pack (Weapons, VFX, Survivors & Zombies) ==="
    & $Blender -b --factory-startup -P "$Root\scripts\build_pack.py"

    Write-Host "=== [2/2] Rendering Weapons, Survivors, VFX & Zombies QA Sheets ==="
    & $Blender -b --factory-startup -P "$Root\scripts\render_pack.py"
} elseif ($Target -eq "vfx") {
    Write-Host "=== [1/2] Building Weapons w/ Muzzle Sockets + 13 Modular Weapon VFX GLBs ==="
    & $Blender -b --factory-startup -P "$Root\scripts\build_pack.py" -- --vfx-only

    Write-Host "=== [2/2] Rendering Weapon VFX Sheet & Live Combat VFX QA ==="
    & $Blender -b --factory-startup -P "$Root\scripts\render_pack.py" -- --vfx-only
} elseif ($Target -eq "zombies") {
    Write-Host "=== [1/2] Building 6 Rigged Low-Poly Zombies ==="
    & $Blender -b --factory-startup -P "$Root\scripts\build_pack.py" -- --zombies-only

    Write-Host "=== [2/2] Rendering Zombie Head Sheet, Lineup & Mechanics QA ==="
    & $Blender -b --factory-startup -P "$Root\scripts\render_pack.py" -- --zombies-only
} elseif ($Target -eq "mutant") {
    Write-Host "=== [1/2] Building Weird Mutant ($Mutant) ==="
    & $Blender -b --factory-startup -P "$Root\scripts\build_pack.py" -- --mutant-only $Mutant

    Write-Host "=== [2/2] Rendering Mutant Showcase Turnaround & Skill QA ($Mutant) ==="
    & $Blender -b --factory-startup -P "$Root\scripts\render_pack.py" -- --mutant-only $Mutant
} else {
    Write-Host "=== [1/2] Building Prototype Survivor .blend and .glb ==="
    & $Blender -b --factory-startup -P "$Root\scripts\build_survivor.py"

    Write-Host "=== [2/2] Rendering Prototype Previews ==="
    & $Blender -b --factory-startup -P "$Root\scripts\render_preview.py"
}

Write-Host "=== DONE ==="
