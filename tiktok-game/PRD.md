# PRD — DEADLINE: LAST STAND (2-Base War: Benteng Manusia vs Sarang Zombie)
**3D TikTok LIVE Interactive War Tug-of-War Game**

- **Lokasi Proyek**: `lowpoly-survivor/tiktok-game/`
- **Format Tayang**: Vertikal **9:16** (`1080×1920`) untuk OBS Browser Source / TikTok LIVE Studio + **Control Deck Simulator** terintegrasi di desktop
- **Engine & Medan Perang 3D**: Three.js (`r170`) + Web Audio API + diorama baru [battlefield_fortress_war.glb](file:///c:/Mirza%20Personal/lowpoly-survivor/output/environment/battlefield_fortress_war.glb) (`?v=13`: **Benteng Manusia Pelat Baja + Menara Jaga Searchlight + Kawat Berduri + Czech Hedgehog** vs **Sarang Bio-Hive Zombie**, dikelilingi **puing bangunan bekas perang + besi rebar** di atas **tanah lumpur coklat basah & genangan reflektif**)
- **Status Koneksi**: Fase 1 berjalan penuh di **Simulasi Lokal (MockTikTokStream + Gift Deck)** melalui `LiveEventBus`, siap disambungkan ke `tiktok-live-connector` (`ws://127.0.0.1:8787`) di Fase 2 tanpa mengubah kode engine 3D.

---

## 1. Visi & Mekanik Utama 2-Base War

Penonton TikTok LIVE bertarung dalam perang terbuka **2 Markas Berhadapan (`50:50`)**:

1. **🏰 Kubu Penyelamat — Benteng Manusia (Sisi Kiri, `HP 3000`)**:
   - Terlindung di balik benteng pelat baja bergelombang, karung pasir, kawat berduri, perisai energi gerbang, dan Menara Jaga ber-searchlight yang menyapu medan lumpur.
   - Penonton bergabung lewat chat **`!manusia` / `1`** (atau gift) untuk memperoleh **Hero persisten** yang terus ber-respawn dan mendorong garis depan menuju Sarang Zombie.
2. **🦠 Kubu Penghancur — Sarang Bio-Hive Zombie (Sisi Kanan, `HP 3000`)**:
   - Bunker beton hancur yang ditembus menara daging organik **Bio-Hive Spire** beserta Inti Kelenjar hijau menyala.
   - Penonton bergabung lewat chat **`!zombie` / `2`** (atau gift Sabotage) untuk memperoleh **Zombie persisten** yang juga terus ber-respawn, berevolusi dari `Walker Lv.1` hingga `👑 Titan Bile Boss Lv.8`, dan menyerbu Gerbang Benteng Manusia.

> Kondisi Menang: Tim pertama yang menghancurkan **Base lawan hingga `0 HP`** langsung menang. Jika waktu `180 detik` habis sementara kedua Base masih berdiri, arena masuk **💀 SUDDEN DEATH (`2× Damage`, tanpa heal Base)**!

---

## 2. 7 Metode Psikologi Tinggi Gift (Upgrade 2-Base Symmetry)

1. **Simetri Panik Dua Kubu (*Dual Loss Aversion*)**: Baik kubu Manusia maupun kubu Zombie memiliki Base HP & unit pribadi — saat Base mana pun `< 30%`, alert krisis berbunyi memancing spam gift penyelamatan dari pendukung kubu tersebut.
2. **Micro-Gift Spam & Combo (`1–5 Koin`)**:
   - `🌹 Rose` (`1`): Heal skuad + repair Benteng; **`x10` → Frenzy 2x Fire Rate**.
   - `🍦 Ice Cream` (`1`): Join/Mutasi Zombie + heal Sarang; **`x10` → Swarm +3 Feral Crawler**.
3. **Evolusi Karakter Ganda (`Lv.1 → Lv.8`) + VIP Crown**:
   - **Manusia**: `Pistol → SMG → M4 → AK-47 → SCAR → SPAS-12 → Sniper → 👑 LMG Sultan`.
   - **Zombie**: `Walker → Feral Crawler → Spitter Asam → Banshee Sonic → Bloater Boomer → Brute SWAT → Mutant Elite (Scythe/Arachnid/Rafflesia/Thorn) → 👑 TITAN BILE BOSS`.
4. **Mekanik Infeksi (*Turned Zombie*)**: Jika Hero Survivor milik `@User` gugur di medan lumpur, ia bangkit dalam `2.6 detik` menjadi **`☣️ @User (Terinfeksi)`** yang berbalik menyerang Benteng Manusia sampai disembuhkan oleh `🌹 Rose` / `🍩 Doughnut` atau respawn kembali di Benteng!
5. **Dual Collective Goal Bars (`0–99 / 100` FOMO)**: Bar kolektif kedua kubu memicu **Community Airstrike** (Human `100`) dan **Giant Mutant Boss** (Zombie `100`) untuk penentu terakhir.
6. **Funnel Gratis Booster FYP**: Chat `!manusia` (`1`), `!zombie` (`2`), dan tiap `+100 Tap Likes` memberi bonus minor agar interaksi komentar/like mendorong algoritma TikTok LIVE.
7. **9:16 Safe Zones & Smart Frontline Camera**: Kamera otomatis melacak garis bentrokan terdepan di tanah lumpur antara Benteng dan Sarang, sementara area bawah layar tetap aman di `?obs=1`.

---

## 3. Tabel Mapping Gift 2-Base War

| Tier | Gift ID | Koin | Kubu | Efek Langsung |
| :--- | :--- | :--- | :--- | :--- |
| Micro | `rose` | `1` | 🏰 Manusia | Heal skuad + repair Benteng + sembuhkan infeksi; `x10` = **Frenzy 2x** |
| Micro | `ice_cream` | `1` | 🦠 Zombie | Join/Mutasi Zombie `@User` + heal Sarang; `x10` = **Swarm +3 Feral** |
| Small | `finger_heart` | `5` | 🏰 Manusia | Repair **Benteng +8%** + Perisai Skuad 5s |
| Small | `gg_troll` | `5` | 🦠 Zombie | Heal **Sarang +8%** + Mutasi Zombie `@User` ke min **Lv.3 Spitter** |
| Mid | `doughnut` | `30` | 🏰 Manusia | Join/Upgrade Hero `@User` **+1 Tier** (min Lv.3 M4/Machete) |
| Mid | `cap_horde` | `30` | 🦠 Zombie | Mutasi Zombie `@User` **+1 Tier** (min Lv.4) + 2 Elite pengawal |
| Big | `corgi_supply` | `99` | 🏰 Manusia | **Supply Crate 3D jatuh**: semua Hero +1 Tier, heal Benteng, revive Hero gugur |
| Big | `storm_curse` | `99` | 🦠 Zombie | **Badai Petir 16s** (Zombie 1.35x cepat) + Mutasi `@User` min **Lv.6 Brute SWAT** |
| Sultan | `money_gun` | `500` | 🏰 Manusia | **AIRSTRIKE 6 Roket** + Hero `@User` naik **👑 Lv.8 LMG Sultan** + heal Benteng |
| Sultan | `galaxy_boss` | `1000` | 🦠 Zombie | Evolusi Zombie `@User` langsung jadi **👑 Lv.8 TITAN BILE BOSS**! |

---

## 4. Loop Ronde & AI Tension Director (`24/7 Auto-Cycle`)

1. **`PREP (5s)`**: 3 Defender Benteng & 3 Raider Zombie ditempatkan berhadapan di medan lumpur; chat mulai merekrut pasukan.
2. **`COMBAT (180s, Wave 1–5)`**: AI Tension Director menjaga populasi minimum (`>= 3` per kubu) dan menaikkan tier wave tiap `32 detik`. Penonton yang gugur respawn otomatis dari markas masing-masing sesuai level mutasi/senjata yang sudah dicapai.
3. **`SUDDEN_DEATH` (`00:00` jika 2 Base hidup)**: Semua damage **2× lipat**, heal Base dinonaktifkan, pencahayaan rim bergeser merah hingga salah satu Base hancur.
4. **`ENDED (10s Recap)`**: Pengumuman MVP (`Top Penyelamat`, `Top Penghancur`, `Kill Terbanyak`) lalu lanjut ke ronde baru secara otomatis.

---

## 5. Kontrak Integrasi TikTok (`LiveEventBus`) & OBS Setup

- **URL Studio**: `http://localhost:8080/tiktok-game/index.html`
- **URL OBS (`1080×1920`)**: `http://localhost:8080/tiktok-game/index.html?obs=1`
- **Bridge WebSocket Fase 2**: Aktifkan `ws://127.0.0.1:8787` dengan paket JSON `{ type: "gift" | "chat" | "like", user, giftId?, repeatCount?, message?, count? }` dari `tiktok-live-connector`.
