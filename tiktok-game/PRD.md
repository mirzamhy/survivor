# PRD — DEADLINE: LAST STAND (Fortress Defense vs Zombie Horde)
**3D TikTok LIVE Interactive Siege Game**

- **Lokasi Proyek**: `lowpoly-survivor/tiktok-game/`
- **Format Tayang**: Vertikal **9:16** (`1080×1920`) untuk OBS Browser Source / TikTok LIVE Studio + **Control Deck Simulator** terintegrasi di desktop
- **Engine & Medan Perang 3D**: Three.js (`r170`) + Web Audio API + diorama ringan matte [battlefield_fortress_war.glb](file:///c:/Mirza%20Personal/lowpoly-survivor/output/environment/battlefield_fortress_war.glb) (`?v=14`: **4 mesh gabungan** dengan Baked Raycast Vertex AO `COLOR_0`, tanah coklat matte bebas kilap berlebih, Benteng Pelat Baja + Menara Jaga Searchlight + Kawat Berduri + Reruntuhan Perang tampak kamera; **tanpa Base Zombie**)
- **Status Koneksi**: Fase 1 berjalan penuh di **Simulasi Lokal (MockTikTokStream + Gift Deck)** melalui `LiveEventBus`, siap disambungkan ke `tiktok-live-connector` (`ws://127.0.0.1:8787`) di Fase 2 tanpa mengubah kode engine 3D.

---

## 1. Visi & Mekanik Utama Fortress Defense

Penonton TikTok LIVE menentukan nasib **Benteng Manusia (`HP 3000`)** selama **180 detik** menghadapi gelombang zombie yang muncul dari **kabut jalanan timur**:

1. **🛡️ Kubu Penyelamat — Benteng Manusia (Sisi Kiri, `HP 3000`)**:
   - Terlindung di balik benteng pelat baja bergelombang, karung pasir, kawat berduri, perisai energi gerbang, dan Menara Jaga ber-searchlight.
   - Penonton bergabung lewat chat **`!manusia` / `1`** (atau gift Defend) untuk memperoleh **Hero persisten** yang menahan gerbang dan mencegat zombie hingga lini tengah (`x <= +5.20`).
2. **☠️ Kubu Penghancur — Gelombang Horde & Mutant Boss (Dari Timur)**:
   - Tanpa markas zombie di sisi kanan — gerombolan zombie & Boss Titan muncul dari **area kabut/siluet timur (`x ≈ +6.6..+9.2`)**.
   - Penonton bergabung lewat chat **`!zombie` / `2`** (atau gift Sabotage) untuk mengerahkan **Zombie persisten** yang terus ber-respawn dan berevolusi dari `Walker Lv.1` hingga `👑 Titan Bile Boss Lv.8` guna menjebol Gerbang Benteng.

> Kondisi Menang: **Benteng bertahan `180 detik` dengan `HP > 0` → Manusia Menang**. Jika **HP Benteng jatuh ke `0`** sebelum waktu habis → **Kubu Zombie Menang**! Memasuki **30 detik terakhir**, arena masuk **🔥 FINAL WAVE** (rim light merah, spawn lebih cepat, damage naik `1.25×`).

---

## 2. 7 Metode Psikologi Tinggi Gift

1. **Loss Aversion Gerbang Tunggal**: Saat HP Benteng `< 30%`, alarm darurat + vignette merah berdenyut untuk memicu gift penyelamatan (`🌹 Rose`, `🫶 Finger Heart`, `🐶 Supply`, `🔫 Money Gun`).
2. **Micro-Gift Spam & Combo (`1–5 Koin`)**:
   - `🌹 Rose` (`1`): Heal skuad + repair Benteng + sembuhkan infeksi; **`x10` → Frenzy 2x Fire Rate**.
   - `🍦 Ice Cream` (`1`): Join/Mutasi Zombie serbu Benteng; **`x10` → Swarm +3 Feral Crawler**.
3. **Evolusi Karakter Ganda (`Lv.1 → Lv.8`) + VIP Crown**:
   - **Manusia**: `Pistol → SMG → M4 → AK-47 → SCAR → SPAS-12 → Sniper → 👑 LMG Sultan`.
   - **Zombie**: `Walker → Feral Crawler → Spitter Asam → Banshee Sonic → Bloater Boomer → Brute SWAT → Mutant Elite → 👑 TITAN BILE BOSS`.
4. **Mekanik Infeksi (*Turned Zombie*)**: Jika Hero Survivor milik `@User` gugur di medan perang, ia bangkit dalam `2.6 detik` menjadi **`☣️ @User (Terinfeksi)`** yang berbalik menyerang Benteng sampai disembuhkan oleh `🌹 Rose` / `🍩 Doughnut` atau respawn kembali sebagai Defender!
5. **Dual Collective Goal Bars (`0–99 / 100` FOMO)**: Bar kolektif memicu **Community Airstrike** (Manusia `100`) dan **Giant Mutant Boss** (Horde `100`).
6. **Funnel Gratis Booster FYP**: Chat `!manusia` (`1`), `!zombie` (`2`), dan tiap `+100 Tap Likes` memberi bonus amunisi & `+3%` repair Benteng.
7. **Ringan & Sinematik 9:16**: Direct WebGL rendering (Bloom opsional) dengan 2 dynamic lights + baked Vertex AO agar berjalan mulus mendekati 60 FPS di OBS Studio.

---

## 3. Tabel Mapping Gift

| Tier | Gift ID | Koin | Kubu | Efek Langsung |
| :--- | :--- | :--- | :--- | :--- |
| Micro | `rose` | `1` | 🛡️ Penyelamat | Heal skuad + repair Benteng + sembuhkan infeksi; `x10` = **Frenzy 2x** |
| Micro | `ice_cream` | `1` | ☠️ Penghancur | Join/Spawn Zombie serbu Benteng; `x10` = **Swarm +3 Feral** |
| Small | `finger_heart` | `5` | 🛡️ Penyelamat | Repair **Benteng +8%** + Perisai Skuad 5s |
| Small | `gg_troll` | `5` | ☠️ Penghancur | Mutasi `@User` min **Lv.3 Spitter** + **Horde Frenzy Speed 6s** |
| Mid | `doughnut` | `30` | 🛡️ Penyelamat | Join/Upgrade Hero `@User` **+1 Tier** (min Lv.3 M4/Machete) |
| Mid | `cap_horde` | `30` | ☠️ Penghancur | Mutasi Zombie `@User` **+1 Tier** (min Lv.4) + 2 Elite pengawal |
| Big | `corgi_supply` | `99` | 🛡️ Penyelamat | **Supply Crate 3D jatuh**: semua Hero +1 Tier, heal Benteng, revive Hero gugur |
| Big | `storm_curse` | `99` | ☠️ Penghancur | **Badai Petir 16s** (Zombie 1.35x cepat) + Mutasi `@User` min **Lv.6 Brute SWAT** |
| Sultan | `money_gun` | `500` | 🛡️ Penyelamat | **AIRSTRIKE 6 Roket** + Hero `@User` naik **👑 Lv.8 LMG Sultan** + heal Benteng |
| Sultan | `galaxy_boss` | `1000` | ☠️ Penghancur | Evolusi Zombie `@User` langsung jadi **👑 Lv.8 TITAN BILE BOSS**! |

---

## 4. Loop Ronde & AI Tension Director (`24/7 Auto-Cycle`)

1. **`PREP (5s)`**: 3 Defender Benteng & 3 Zombie awal bersiap; chat mulai merekrut pasukan.
2. **`COMBAT (180s, Wave 1–5)`**: AI Tension Director menjaga ritme gelombang dari kabut timur dan menaikkan intensitas tiap `32 detik`.
3. **`FINAL_WAVE` (30s terakhir)**: Rim light bergeser merah, zombie bergerak `1.15×` lebih cepat dan agresif hingga detik evakuasi `00:00`.
4. **`ENDED (10s Recap)`**: Pengumuman MVP (`Top Penyelamat`, `Top Penghancur`, `Kill Terbanyak`) lalu reset ke ronde baru secara otomatis.

---

## 5. Kontrak Integrasi TikTok (`LiveEventBus`) & OBS Setup

- **URL Studio**: `http://localhost:8080/tiktok-game/index.html`
- **URL OBS (`1080×1920`)**: `http://localhost:8080/tiktok-game/index.html?obs=1`
- **Bridge WebSocket Fase 2**: Aktifkan `ws://127.0.0.1:8787` dengan paket JSON `{ type: "gift" | "chat" | "like", user, giftId?, repeatCount?, message?, count? }` dari `tiktok-live-connector`.
