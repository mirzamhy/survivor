# Rig, Control Rig & Hand Mechanics Design Specification

Arsitektur rig produksi Low-Poly Zombie Apocalypse (`c:/Mirza Personal/lowpoly-survivor`) kini lengkap dengan **5 jari individual (55 Mixamo + 2 ForeArmTwist = 57 deform bones)**, **Interactive Blender Control Rig**, **9 preset genggaman mikro**, dan **14 Blender Actions** siap game.

## 1. Struktur Tulang (`Deform` vs `Controls` Bone Collections)

### A. 57 Deform Bones (`use_deform = True` → Diekspor ke `.glb`)
- **Spine & Head (7)**: `Hips -> Spine -> Spine1 -> Spine2 -> Neck -> Head -> HeadTop_End`
- **Clavicle & Arm (5 per sisi)**: `Shoulder -> Arm -> ForeArm -> ForeArmTwist (leaf) -> Hand`
- **5 Individual Fingers (15 per sisi)**: `Thumb1..3`, `Index1..3`, `Middle1..3`, `Ring1..3`, `Pinky1..3`
- **Leg & Foot (4 per sisi)**: `UpLeg -> Leg -> Foot -> ToeBase`
- **`ForeArmTwist`**: Membagi **55%** rotasi longitudinal sumbu `+Y` agar telapak tangan kiri bisa bersupinasi penuh menopang bagian bawah *handguard* tanpa pergelangan terpelintir.

### B. Interactive Control Rig (`Controls` Collection, `use_deform = False` → Otomatis terstrip saat ekspor `.glb`)
Diaktifkan/nonaktifkan secara instan lewat custom property **`arm_obj["use_live_ik"]`** (`0.0` = mainkan Action / ekspor glTF bersih; `1.0` = rig IK interaktif penuh di Blender):
- **`CTRL_Root`**, **`CTRL_Weapon`** (weapon master socket), **`CTRL_LookAt`** (*Damped Track*: `14% Spine2` → `38% Neck` → `62% Head` dengan *Limit Rotation*).
- **`CTRL_Hand_IK_L/R`** + **`CTRL_Pole_Elbow_L/R`** (2-bone IK + *Copy Rotation* + *Clavicle Follow* `20%`).
- **Reverse-Foot Roll Hierarchy (L/R)**:
  `CTRL_Foot_IK -> CTRL_Heel_Roll -> CTRL_Toe_Roll -> CTRL_Ball_Pivot -> CTRL_Ankle_Target` + **`CTRL_Pole_Knee_L/R`** + *Limit Rotation* lutut `[-135°, 0°]`.

## 2. Anatomi Tangan 5 Jari & 9 Preset Mikro (`pose_hand_grip`)

Setiap tangan memodelkan **5 jari terpisah** via `ring_perp()` dan bantalan *thenar eminence*:
1. `trigger_on` — Jari telunjuk melingkari pelatuk; 3 jari bawah mengunci grip.
2. `trigger_off` — Disiplin taktis: telunjuk lurus di *receiver* atas pelindung pelatuk (*Idle*, *Reload*, *Walk/Run*).
3. `support_under` — Supinasi telapak menghadap ke atas menopang bawah *handguard*.
4. `support_c_clamp` — Genggaman C-clamp dengan ibu jari di rel atas.
5. `mag_pinch` — Ibu jari + telunjuk + tengah menjepit sisi magasin saat *reload*.
6. `pistol_support` — *Thumbs-forward* dua tangan membungkus grip pistol.
7. `fist` — Kepalan penuh untuk kunci pipa dan busur.
8. `relaxed` — Rileks bertingkat alami (*cascade* telunjuk `-14°` hingga kelingking `-36°`).
9. `claw` — Cakar tegang terbuka melebar untuk serangan zombie.

## 3. Daftar 14 Production Blender Actions (`.blend`)

Setiap karakter `.blend` di `output/survivors/` menyertakan **14 Action** permanen (`use_fake_user = True`, keyframe hanya pada bone deform):
1. `Idle_Ready` — Bernapas + disiplin pelatuk + lirikan ringan.
2. `Aim_ADS` — Senapan masuk kantong bahu kanan, *clavicle auto-follow*, *cheek-weld*.
3. `Shoot_Recoil` — Sentakan bahu `+3.8 cm`, hentakan laras `+9.5°`, *counter-dip* pemulihan.
4. `Reload_Tactical` — 5 tahap: memiringkan senjata (`cant`) → melepas magasin (`mag_pinch`) → meraih *pouch* → memasang magasin → menampar *bolt catch*.
5. `Crouch_Aim` — Berlutut rendah taktis dengan bahu tetap membidik.
6. `Walk_Cycle` — Siklus penuh dengan *Foot-Roll IK*, *pelvis bob*, dan *counter-rotation*.
7. `Run_Cycle` — Condong depan, angkat lutut tinggi, dan fase melayang.
8. `Strafe_Right` — **Upper/Lower body split**: kaki melangkah ke samping saat dada & senapan tetap mengunci target `-Y`.
9. `Melee_Swing` — Ayunan penuh pinggul-ke-bahu (*windup* → *impact* → *follow* → *recover*).
10. `Hit_React` — Sentakan mundur terkena serangan.
11. `Head_LookAt` — Sapuan tolehan kepala anatomis kiri/kanan/atas/bawah.
12. `Zombie_Walk_Shamble` — Jalan pincang asimetris membungkuk + cakar menjulur.
13. `Zombie_Lunge` — Terkaman 4 tahap (*windup* → *launch* → *lunge* → *recover*).
14. `Zombie_Bite_Grab` — Cengkeraman bahu dua tangan + gigitan leher ke depan.
