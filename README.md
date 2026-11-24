# Low-Poly Zombie Apocalypse Survivor

Model karakter 3D low-poly **Survivor Pria (Zombie Apocalypse)** yang dibuat secara prosedural menggunakan **Blender 5.2 Python (`bmesh`)** dengan gaya *faceted modern low-poly* (flat-shaded tajam) dan **rig humanoid kompatibel Mixamo**.

## Fitur Utama
- **Gaya Visual**: Pure-triangle *faceted low-poly* (100% segitiga simetris cermin dengan *flat shading* tajam, tanpa tekstur bitmap; semua warna berbasis material PBR `Principled BSDF`).
- **Desain Karakter**:
  - Kepala low-poly pria tanpa mata (*faceless sculpted low-poly*) dengan kontur wajah tegas (tonjolan alis, cekungan rongga mata, tulang pipi, hidung pahat, rahang berjenggot tipis/*stubble*), rambut belakang melengkung rapi, dan beanie rajut lipat warna burgundy.
  - Jaket parka terbuka berkerah tinggi + lapel, kaus henley dengan *dog-tag*, saku dada & saku bawah, perban kain di lengan kiri.
  - Sabuk kulit dengan gesper metal, 2 kantong pinggang, dan 2 saku belakang celana.
  - Celana kargo longgar berlipat halus dengan saku paha kanan-kiri, pelindung lutut (*knee pad*) di lutut kanan, dan lilitan kain di betis kiri.
  - Sepatu boots tempur bersol terpisah (tumit & tapak depan) rata di `Z = 0.00 m` (tinggi total karakter `1.80 m`) lengkap dengan tali pengikat pergelangan.
  - Sarung tangan *fingerless* dengan ibu jari & jari terpisah untuk menggenggam senjata.
- **Perlengkapan & Senjata Terpisah (*Detachable*)**:
  - `Gear_Backpack` (ransel survival + matras gulung + tali bahu) terikat 100% ke tulang `mixamorig:Spine2`.
  - `Weapon_Crowbar` (linggis merah) terpasang di belakang ransel, terikat 100% ke `mixamorig:Spine2`.
  - `Weapon_Bat` (tongkat bisbol berpaku) di tangan kanan, terikat 100% ke `mixamorig:RightHand`.
- **Rigging Mixamo**: Tulang standar `mixamorig:Hips` s/d `HeadTop_End`, bahu/lengan/tangan + jari, dan kaki lengkap dalam **T-pose** standar (`-Y` menghadap depan, `+Z` atas).

## Struktur Folder
```
lowpoly-survivor/
├── build.ps1                    # Script build + render otomatis
├── scripts/
│   ├── palette.py               # Palet warna & material Principled BSDF
│   ├── mesh_utils.py            # Helper BMesh + triangulasi simetris
│   ├── head_sculpt.py           # Pahatan kepala low-poly (Loomis/Asaro) + telinga + beanie
│   ├── body_parts.py            # Geometri tubuh/pakaian + PROPORTIONS bersama
│   ├── gear_parts.py            # Ransel, tongkat berpaku, linggis
│   ├── rig_mixamo.py            # Armature Mixamo & weight painting deterministik
│   ├── build_survivor.py        # Build master, ekspor .blend & .glb + verifikasi
│   └── render_preview.py        # Render 5-view T-pose sheet & pose aksi hero
├── output/
│   ├── survivor_lowpoly.blend         # File sumber Blender lengkap
│   ├── survivor_lowpoly.glb           # Karakter + rig + ransel & senjata
│   └── survivor_character_only.glb    # Karakter + rig tanpa ransel/senjata
└── renders/
    ├── sheet_tpose.png          # Preview 5 sudut (Depan, 3/4, Samping, Belakang, Wajah)
    ├── head_sheet.png           # Turnaround kepala 4 sudut (Depan, 3/4, Samping, Belakang)
    ├── closeup_check.png        # Close-up wajah 3/4 & kepala belakang + ransel/linggis
    └── hero_posed.png           # Preview pose siap bertarung
```

## Batch 1: 10 Paired Survivors (5 Male + 5 Female) + 17 Senjata Universal + Mekanik Rig
Gunakan `.\build.ps1` (default `-Target pack`) untuk membangun **10 model survivor berpasangan Male & Female** (`55 deform bones` Mixamo + `ForeArmTwist`, `19 control bones` via `use_live_ik`, **22 universal Actions** untuk seluruh kelas senjata), `WeaponSocket_R` & `WeaponSocket_L` pada kedua tangan, dan **17 senjata ukuran asli** (pangkal gagang di `(0,0,0)`, moncong ke `+Z`):
- **5 Pasang Survivor (`output/survivors/*_male.*`, `*_female.*`, & `output/survivors/unarmed/*_unarmed.glb`)**:
  - **Jake** (`1.80 m` Male / `1.70 m` Female, default: M4 + Glock 17 holstered)
  - **Maya** (`1.79 m` Male / `1.68 m` Female, default: Glock 17)
  - **Rico** (`1.82 m` Male / `1.70 m` Female, default: Kunci Pipa)
  - **Lena** (`1.80 m` Male / `1.70 m` Female, *uncovered ranger hair + bracer*, default: Busur Compound + Anak Panah + Pisau)
  - **Tom** (`1.81 m` Male / `1.70 m` Female, default: Shotgun Laras Ganda)
- **Semua Karakter Bisa Memakai Semua 17 Senjata**:
  - Di Blender Python, panggil `equip_weapon(arm_obj, weapon_id, materials, idx_map)` dan `apply_survivor_pose(..., style="auto")` untuk memasang senjata apa saja (`m4`, `ak47`, `sniper`, `lmg`, `pistol`, `revolver`, `compound_bow`, `pipe_wrench`, dll.) ke karakter mana saja.
  - Di Game Engine (**Unity / Godot / Three.js**), muat `output/survivors/unarmed/<slug>_unarmed.glb` lalu tempelkan node `weapon_*.glb` langsung ke socket `WeaponSocket_R` (dan `compound_bow` ke `WeaponSocket_L`), kemudian putar salah satu dari **22 Actions universal**:
    - **Rifle / Shotgun / SMG / Sniper / LMG**: `Rifle_Idle_Ready`, `Rifle_Aim_ADS`, `Rifle_Shoot_Recoil`, `Rifle_Reload_Tactical`, `Rifle_Crouch_Aim`, `Rifle_Walk_Cycle`, `Rifle_Run_Cycle`, `Rifle_Strafe_Right`
    - **Pistol / Revolver**: `Pistol_Idle_Ready`, `Pistol_Aim_ADS`, `Pistol_Shoot_Recoil`, `Pistol_Reload_Tactical`
    - **Busur & Panah**: `Bow_Idle_Ready`, `Bow_Aim_Draw`, `Bow_Shoot_Release`
    - **Melee**: `Melee_Idle_Ready`, `Melee_Swing`
    - **Reaksi, Look-At & Zombie**: `Hit_React`, `Head_LookAt`, `Zombie_Walk_Shamble`, `Zombie_Lunge`, `Zombie_Bite_Grab`
- **Render QA & Perbandingan**: [survivors_lineup.png](renders/survivors_lineup.png), [universal_weapons_qa.png](renders/universal_weapons_qa.png), [pair_jake.png](renders/pair_jake.png), [pair_maya.png](renders/pair_maya.png), [pair_rico.png](renders/pair_rico.png), [pair_lena.png](renders/pair_lena.png), [pair_tom.png](renders/pair_tom.png)
- **17 Senjata (`output/weapons/`)**: dilengkapi socket `MuzzleSocket` & `EjectSocket` plus profil `WEAPON_META["vfx_profile"]`:
  - Sidearms: `pistol` (Glock 17, 202mm), `revolver` (S&W 686 4", 243mm)
  - SMG & Rifles: `smg` (MP5A2, 680mm), `m4` (M4A1, 840mm), `ak47` (AKM/AK-47, 880mm), `scar` (FN SCAR-H, 965mm), `aug` (Steyr AUG A3, 790mm), `m14` (M14 Battle Rifle, 1126mm), `sniper` (M24 SWS, 1092mm)
  - Shotguns & LMG: `pump` (Remington 870, 972mm), `double_barrel` (Side-by-Side 26", 1050mm), `spas12` (Franchi SPAS-12, 1041mm), `lmg` (M249 SAW, 1035mm)
  - Non-firearms: `pipe_wrench` (520mm), `compound_bow` (820mm), `arrow` (750mm), `knife` (280mm)
- **13 Efek Senjata Modular (`output/vfx/vfx_*.glb`, `scripts/weapon_vfx.py`)**:
  - *Muzzle Flash Emissive*: `muzzle_pistol`, `muzzle_rifle`, `muzzle_shotgun`, `muzzle_heavy`
  - *Tracer & Selongsong*: `tracer_bullet`, `tracer_pellet`, `shell_rifle`, `shell_shotgun`, `smoke_puff`
  - *Busur, Melee & Impact*: `arrow_trail`, `melee_slash`, `impact_spark`, `impact_blood`
  - Helper `spawn_weapon_vfx()` otomatis menempelkan efek sesuai pose & `MuzzleSocket` / `EjectSocket`; jalankan `.\build.ps1 -Target vfx` untuk build cepat VFX.
  - Render QA VFX: [weapon_vfx_sheet.png](renders/weapon_vfx_sheet.png), [weapon_vfx_action_qa.png](renders/weapon_vfx_action_qa.png)

## Batch 2: 6 Rigged Faceless Horror Zombies (`output/zombies/`)
6 arketipe zombie **faceless** (rongga mata cekung gelap tanpa bola mata agar konsisten dengan gaya pahatan manusia **Loomis/Asaro low-poly**), ukuran bervariasi ekstrem dari kecil hingga bos raksasa (`1.42 m` s/d `2.26 m`), menggunakan rig Mixamo identik (`55 deform` + `19 controls`) + **13 Zombie Actions & Skills**:
- `zombie_crawler_stalker` (`1.42 m`, kecil bungkuk, kain compang-camping, cakar panjang — Skill: `Zombie_Lunge` *Pounce*)
- `zombie_walker_shambler` (`1.78 m`, kemeja & dasi sobek, pipi kanan berlubang — Skill: `Zombie_Bite_Grab`)
- `zombie_banshee_screamer` (`1.66 m`, siluet female kurus dengan rambut acak panjang & rahang ternganga — Skill: `Skill_Sonic_Shriek`)
- `zombie_spitter_hazmat` (`1.76 m`, kantung racun bengkak di leher, setelan hazmat robek & tabung bocor — Skill: `Skill_Acid_Spit`)
- `zombie_bloater_boomer` (`1.88 m`, perut bengkak meletup dipenuhi bisul gas kuning menyala — Skill: `Skill_Volatile_Detonate`)
- `zombie_juggernaut_brute` (`2.26 m`, bos raksasa berzirah SWAT pecah, lengan kanan raksasa berduri tulang + besi beton di punggung — Skill: `Skill_Ground_Slam`)
- Jalankan `.\build.ps1 -Target zombies` untuk build + render QA zombie.
- Render QA Zombie: [zombies_head_sheet.png](renders/zombies_head_sheet.png), [zombies_lineup.png](renders/zombies_lineup.png), [zombie_mechanics_qa.png](renders/zombie_mechanics_qa.png)

## Cara Menjalankan Ulang
```powershell
cd "c:\Mirza Personal\lowpoly-survivor"
.\build.ps1                # Batch 1: 5 Survivor + 7 Senjata + Render Lineup
.\build.ps1 -Target proto  # Prototipe awal survivor tunggal
```

## Cara Lepas/Pasang Gear di Blender atau Game Engine
- Setiap perlengkapan (`Gear_Backpack`, `Weapon_Bat`, `Weapon_Crowbar`) adalah mesh terpisah yang ter-skin 100% ke satu tulang (`mixamorig:Spine2` atau `mixamorig:RightHand`).
- Di **Three.js / Unity / Godot / Blender**, kamu cukup `hide` atau `remove` node mesh `Weapon_Bat` / `Gear_Backpack` / `Weapon_Crowbar` tanpa merusak rig ataupun mesh `Survivor_Body`.
- Untuk animasi cepat, unggah `output/survivor_character_only.glb` atau `output/survivor_lowpoly.glb` ke Mixamo / retargeter animasi humanoid (`mixamorig:*`).
