# PRD — DEADLINE: LAST STAND (Save vs Sabotage)
**3D TikTok LIVE Interactive Survival Tug-of-War Game**

- **Lokasi Proyek**: `lowpoly-survivor/tiktok-game/`
- **Format Tayang**: Vertikal **9:16** (`1080×1920`) untuk OBS Browser Source / TikTok LIVE Studio + **Control Deck Simulator** terintegrasi di desktop
- **Engine & Aset**: Three.js (`r170`) + Web Audio API procedural SFX + paket aset 3D PBR `../output/...` (`?v=12`: 10 Survivor, 22 Senjata, 6 Zombie, 5 Mutant Boss, 19 Environment Prop)
- **Status Koneksi**: Fase 1 berjalan 100% di **Simulasi Lokal (MockTikTokStream + Gift Deck)** melalui kontrak `LiveEventBus` standar, sehingga siap disambungkan ke `tiktok-live-connector` (`ws://localhost:8787`) di Fase 2 tanpa mengubah engine 3D maupun logic gameplay.

---

## 1. Visi & Positioning Produk

**DEADLINE: LAST STAND** adalah game survival 3D *Asymmetric Tug-of-War* yang dirancang khusus untuk **mengonversi penonton pasif menjadi pemberi gift aktif** di TikTok LIVE.

Penonton tidak sekadar menonton bot bermain, melainkan terbelah secara real-time menjadi dua kubu yang saling beradu pengaruh di arena jalanan apokalips 3D:
1. **🛡️ Kubu Penyelamat (Defend)**: Menjaga **Barikade & Menara Radio Evakuasi** agar bertahan sampai timer evakuasi `180 detik` habis, menyelamatkan/meng-upgrade hero bernama `@Username`, hingga memanggil **Airstrike Barage**.
2. **☠️ Kubu Penghancur (Sabotage)**: Menekan pertahanan dengan mengirim Zombie, memanggil **Badai Petir Blackout**, hingga menurunkan **Giant Mutant Boss** bernama `@Username` untuk menjebol barikade sebelum evakuasi tiba.

> Prinsip utama: Game tetap seru dan terus bergerak **walaupun belum ada gift** (AI Tension Director menjaga tempo wave), namun **setiap gift langsung mengubah drama visual di layar dalam `< 0.2 detik`**.

---

## 2. 7 Metode & Psikologi Tinggi Gift (*High-Gift Conversion Framework*)

Game ini menggabungkan tujuh pemicu psikologis yang terbukti paling efektif menghasilkan retensi tinggi sekaligus lonjakan koin di game interaktif TikTok LIVE:

### Metode 1 — Save vs Sabotage Rivalry (Konflik Dua Kubu)
Manusia jauh lebih terdorong mengeluarkan gift saat **membela tim atau membalas "troll" dari kubu lawan** daripada bermain pasif sendirian. Saat penonton A mengirim Boss untuk menghancurkan markas, penonton B terdorong mengirim Doughnut / Money Gun untuk membalas.

### Metode 2 — Micro-Gift Spam & Combo Escalation (`1–5 Koin`)
Gift murah (`🌹 Rose`, `🍦 Ice Cream`) didesain memberi kepuasan instan:
- Respons `< 200 ms`: bunyi **coin chime bernada naik** per hitungan combo + teks combo besar.
- **Milestones Streak**: `x10 Rose` memicu **Frenzy Mode** (laju tembak `2x`), sementara `x10 Ice Cream` memicu **Swarm Feral** (+3 Crawler cepat). Penonton koin kecil tetap merasa "berkuasa" menggeser jalannya laga.

### Metode 3 — VIP Sultan Status & Ego Spotlight
Pemberi gift menengah hingga besar (`🍩 Doughnut`, `🐶 Corgi`, `🔫 Money Gun`, `🌌 Galaxy`) mendapatkan pengakuan status sosial yang terlihat jelas oleh seluruh room:
- Karakter survivor atau Mutant Boss 3D menyandang **nama `@Username` dan mahkota/tier badge**.
- **Upgrade Senjata Visual Nyata** langsung di tangan karakter 3D:
  `Lv.1 Pistol → Lv.2 SMG → Lv.3 M4 → Lv.4 AK-47 → Lv.5 SCAR → Lv.6 SPAS-12 → Lv.7 Sniper → Lv.8 LMG Golden Crown`.
- **Live Sultan Leaderboard**: Top 3 Penyelamat vs Top 3 Penghancur tampil permanen di layar atas.

### Metode 4 — Near-Death Cliffhanger & Loss Aversion
Ketika **HP Barikade < 30%** atau **Survivor tersisa <= 1**, game masuk ke mode krisis:
- Shield barikade berubah merah berkedip + percikan listrik.
- Vignet merah darurat + bunyi alert taktis + banner CTA besar: **`⚠️ MARKAS KRITIS! KIRIM 🌹 ROSE / 🫶 HEART SEKARANG!`**.
- Psikologi *loss aversion* membuat penonton ragu-ragu akhirnya mengirim gift penyelamat agar progres ronde hampir menang tidak hangus di detik terakhir.

### Metode 5 — Dual Collective Goal Bars (*FOMO Last-Hitter*)
Dua progress bar kolektif `0 → 100 Koin` berjalan bersamaan:
- **🛡️ Bar Community Airstrike** (Defend)
- **☠️ Bar Mutant Boss Invasion** (Sabotage)
Begitu salah satu bar menyentuh **>= 80%**, host/banner menyorot peluang menjadi **"Penentu Terakhir"**. Nama pengirim gift ke-100 diumumkan secara heroik bersama eksekusi efek raksasa, sehingga banyak penonton berebut menembus angka 100.

### Metode 6 — Free Engagement Funnel (*Algoritma FYP Booster*)
Penonton gratis tidak dibiarkan menganggur karena interaksi mereka menaikkan skor algoritma TikTok (Like & Comment Rate):
- **Chat `!join` / `1`**: Rekrut survivor gratis Lv.1 Pistol bernama pengirim (maksimal 8 unit; antrean jika penuh).
- **Chat `!zombie` / `2`**: Munculkan 1 Walker Shambler bernama pengirim.
- **Tap-Tap Layar (`+100 Likes`)**: Memicu **Mini Supply** gratis (`+3% HP Barikade` + `5s` bonus attack speed).
Namun, upgrade senjata tingkat tinggi, potong antrean saat penuh, supply drop, airstrike, dan Giant Mutant Boss hanya dapat dipicu lewat **Gift**.

### Metode 7 — 9:16 TikTok UI Safe Zones
Layout vertikal dibagi ketat agar tidak bertabrakan dengan elemen native aplikasi TikTok saat siaran:
- **`0% – 12%` (Atas)**: Zona aman untuk avatar host, jumlah penonton, & badge LIVE TikTok.
- **`12% – 27%`**: HUD taktis padat (Timer Evakuasi, Wave, HP Barikade, Dual Goal Bars, Mini Sultan Leaderboard, Boss HP Bar).
- **`27% – 66%`**: **3D Combat Arena utama** — Barikade di sisi kiri, baku tembak & ledakan di tengah, gerombolan zombie/mutant datang dari kanan.
- **`66% – 72%`**: Strip **Cheat-Sheet Gift** super ringkas (6 ikon & koin paling sering dikirim).
- **`72% – 100%` (Bawah)**: Area bebas HUD penting untuk kolom komentar asli TikTok (di Desktop Studio, area ini menampilkan Live Chat Simulator; di OBS Mode `?obs=1`, chat simulator disembunyikan otomatis).

---

## 3. Tabel Mapping Gift TikTok Lengkap

| Tier | Gift ID | Nama & Koin | Kubu | Efek Gameplay & 3D | Visual, Audio & Kamera | Batas / Anti-Spam |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Micro | `rose` | 🌹 **Rose** (`1`) | 🛡️ Defend | Heal semua survivor +35 HP & +4% Fury; **Combo x10** → Frenzy `1.75x` Attack Speed (7s) | Cincin hijau heal, bunyi chime naik per combo | Digabung per combo window 3.5s |
| Micro | `ice_cream` | 🍦 **Ice Cream** (`1`) | ☠️ Sabotage | Spawn 1 `Walker Shambler` bernama `@User`; **Combo x10** → Swarm `+3 Crawler Feral` | Pop chime sabotase, nameplate merah `@User` | Batas musuh aktif max 14 (kelebihan jadi buff HP/speed) |
| Small | `finger_heart` | 🫶 **Finger Heart** (`5`) | 🛡️ Defend | Repair Barikade `+8% HP` + Perisai Skuad 5s (kurangi damage masuk) | Shockwave biru-hijau di barikade, chord shimmer | Heal barikade dibatasi max 100% |
| Small | `gg_troll` | 🎮 **GG / Troll** (`5`) | ☠️ Sabotage | Spawn `Spitter Hazmat` (serangan asam jarak jauh) | Asam neon + tag `@User` di unit zombie | Masuk antrean jika arena penuh |
| Mid | `doughnut` | 🍩 **Doughnut** (`30`) | 🛡️ Defend | Jika `@User` belum punya hero: spawn **VIP Hero Lv.3 (M4/Katana)**. Jika sudah ada: **Upgrade Senjata +1 Tier** + Full Heal (potong antrean!) | Sinar upgrade keemasan, swap mesh senjata real-time, fanfare 3 nada | Cap maksimal Lv.8; lewat Lv.8 → Golden Overcharge +150 HP |
| Mid | `cap_horde` | 🧢 **Cap Horde** (`30`) | ☠️ Sabotage | Turunkan skuad **3 Elite Zombie**: `Crawler Stalker` + `Banshee Screamer` + `Bloater Boomer` | Banner ancaman, camera micro-shake | Maks 3 wave burst simultan dalam antrean |
| Big | `corgi_supply` | 🐶 **Corgi Supply** (`99`) | 🛡️ Defend | **3D Supply Crate Drop** (`env_supply_crate_loot.glb`) jatuh dari langit → Upgrade **SEMUA survivor +1 Tier**, Heal +50% HP, Revive 1 Hero | Sorot kamera singkat, sinar emas vertikal, ledakan debu crate mendarat | Prioritas tinggi antrean |
| Big | `storm_curse` | ⛈️ **Badai Blackout** (`99`) | ☠️ Sabotage | Cuaca berubah **Badai Hujan & Petir** selama 16s, Speed Zombie `1.35x`, plus spawn `Juggernaut Brute SWAT` bernama `@User` | Kilat petir 3D, terompet bahaya, pergeseran IBL & atmosfer badai | Durasi badai di-extend maks 24s |
| Sultan | `money_gun` | 🔫 **Money Gun** (`500`) | 🛡️ Defend | **AIRSTRIKE BARRAGE** (6 roket dari langit menghujani area musuh, `320` AoE) + `@User` naik ke **Sultan Lv.8 LMG Golden Crown** + langit cerah | Slow-motion sinematik `0.45s`, 6 laser target ring merah, ledakan bloom, sirene roket | Prioritas instan (bypass antrean micro) |
| Sultan | `galaxy_boss` | 🌌 **Galaxy Titan** (`1000`) | ☠️ Sabotage | Summon **Giant Mutant Boss** acak (`Bile Juggernaut`, `Scythe Stalker`, `Arachnid Maw`, `Rafflesia`, `Thorn Shroud`) berukuran raksasa bernama `@User` | Slow-motion zoom Boss, petir, warhorn bass dalam, Boss HP Bar raksasa di HUD | Maks 2 Giant Boss bersamaan; ekstra Boss memperkuat Boss aktif (`+350 HP`) |

---

## 4. Core Game Loop & AI Tension Director

1. **Fase 1 — `PREP` (`6 detik`)**: 3 Survivor pemula ditempatkan di garis pertahanan (`x = -3.4`), Barikade aktif di `x = -5.6`, UI menampilkan ajakan `!join` dan duel dimulai.
2. **Fase 2 — `COMBAT` (`0:00 – 2:30`, Wave 1–4)**:
   - Setiap `32 detik`, Wave naik tingkat (komposisi bergerak dari `Walker` → `Crawler` & `Spitter` → `Banshee` & `Bloater` → `Juggernaut Brute`).
   - **AI Tension Director** mengevaluasi populasi musuh setiap detik:
     - Bila musuh aktif `< targetWaveCount` (misal `< 4` di Wave 2), sistem menurunkan bala bantuan zombie otomatis agar aksi 3D tidak pernah kosong meski belum ada gift.
     - Bila Barikade kritis (`< 30% HP`), jeda spawn ambient sedikit dilonggarkan sambil memicu alert darurat agar penonton penyelamat punya peluang melakukan *heroic comeback*.
3. **Fase 3 — `FINAL STAND` (`30 detik terakhir`)**:
   - Timer berubah merah berdenyut, laju serangan meningkat, dan bila belum ada Mutant Boss aktif, **1 Mini-Boss Titan** otomatis turun sebagai ujian akhir evakuasi.
4. **Fase 4 — `VICTORY / DEFEAT` (`10 detik` Auto-Cycle 24/7)**:
   - **Survivor Menang** jika Timer Evakuasi mencapai `00:00` dengan `HP Barikade > 0` dan minimal 1 Survivor masih hidup (atau bertahan di detik akhir).
   - **Sabotage Menang** jika **HP Barikade = 0** atau **seluruh Survivor gugur** tanpa sisa di arena.
   - Layar menampilkan **MVP Recap** (Kubu Pemenang, Total Koin Ronde, Top Penyelamat, Top Penghancur, Kill Terbanyak) dan menghitung mundur `10 detik` untuk langsung memulai ronde berikutnya tanpa intervensi host.

---

## 5. Arsitektur Teknis & Kesiapan Integrasi TikTok (`LiveEventBus`)

Seluruh simulasi berjalan lewat satu kontrak event tunggal di `js/eventBus.js`:

```json
{
  "type": "gift",
  "user": "SultanJakarta",
  "giftId": "money_gun",
  "repeatCount": 1,
  "coins": 500,
  "source": "mock",
  "timestamp": 1795800000000
}
```

Jenis event standar lain yang diterima `LiveEventBus`:
- `{ "type": "chat", "user": "@nama", "message": "!join" }`
- `{ "type": "like", "user": "@nama", "count": 25 }`
- `{ "type": "follow", "user": "@nama" }`

**Alur Penyambungan ke TikTok LIVE Nanti (Fase 2)**:
1. Jalankan bridge Node.js lokal dengan `tiktok-live-connector` (WebSocket server di `ws://localhost:8787`).
2. Mapping `giftName` / `giftId` TikTok asli ke 10 `giftId` internal (`rose`, `doughnut`, `money_gun`, `galaxy_boss`, dll.) dan teruskan JSON ke WebSocket.
3. Di game (`game.js`), aktifkan `?ws=ws://localhost:8787` atau tombol **Hubungkan Bridge**. Mesin 3D, audio, HUD, goal bar, leaderboard, dan combat AI bekerja identik baik menerima event dari simulator maupun langsung dari live chat TikTok.

---

## 6. Panduan Operasional Host LIVE & OBS

1. **Setup OBS Studio**:
   - Base / Output Resolution: **`1080 × 1920`** (portrait 9:16).
   - Tambahkan **Browser Source** → URL: `http://localhost:8080/tiktok-game/index.html?obs=1`
   - Width: `1080`, Height: `1920`, aktifkan *"Control audio via OBS"*.
   - Mode `?obs=1` otomatis menyembunyikan panel simulator kiri/kanan dan kolom chat palsu di bawah sehingga 30% area bawah bersih untuk kolom chat asli TikTok.
2. **Skrip Pancingan MC Saat Live**:
   - **Saat Bar Goal >= 80%**: *"Kurang 15 koin lagi bar Airstrike penuh! Siapa yang mau namanya jadi penentu ledakan?!"*
   - **Saat `!join` penuh**: *"Antrean gratis penuh ya guys, yang mau langsung masuk bawa M4/Katana atau upgrade senjata bisa lempar Donat!"*
   - **Saat Markas Kritis (< 30%)**: *"Aduh barikade tinggal 20%! Tim Penyelamat tolongin kirim Rose atau Heart, jangan kasih menang tim Zombie!"*
3. **Target KPI Uji Coba**:
   - **Watch Time Rata-Rata**: `> 4.5 menit` (penonton menunggu hasil 1 ronde 3 menit + pengumuman MVP).
   - **Micro-Gift Frequency**: Minimal 1 event micro/chat tiap `5–8 detik` agar feed terasa hidup.
   - **Climax Conversion**: Rasio puncak pengiriman gift terjadi saat **Bar Goal >= 80%**, **Boss Summon**, dan **Final Stand 30 detik terakhir**.
