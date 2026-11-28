// Core Game Loop, AI Tension Director, Gift Executor, and HUD/Simulator Controller

import {
  SURVIVORS,
  ZOMBIES,
  MUTANT_BOSSES,
  GIFT_CATALOG,
  GIFT_LIST,
} from './catalog.js';
import { createAudioEngine } from './audio.js';
import { LiveEventBus, MockTikTokStream } from './eventBus.js';
import { createArenaEngine } from './engine3d.js';

const params = new URLSearchParams(window.location.search);
const isObsLocked = params.get('obs') === '1';
const startAuto = params.get('auto') === '1';
const startMute = params.get('mute') === '1';
const wsParam = params.get('ws') || '';

if (isObsLocked) {
  document.body.classList.add('obs-mode', 'obs-locked');
}

// DOM References
const $ = (id) => document.getElementById(id);
const stageWrap = $('stage-wrap');
const labelsLayer = $('labels-layer');
const vignetteCrisis = $('vignette-crisis');

const hudPhasePill = $('hud-phase-pill');
const hudTimer = $('hud-timer');
const hudRoundBadge = $('hud-round-badge');
const hudBarricadeFill = $('hud-barricade-fill');
const hudBarricadeText = $('hud-barricade-text');
const goalDefendFill = $('goal-defend-fill');
const goalDefendText = $('goal-defend-text');
const goalSabotageFill = $('goal-sabotage-fill');
const goalSabotageText = $('goal-sabotage-text');
const hudBuffs = $('hud-buffs');

const sultanDefendList = $('sultan-defend-list');
const sultanSabotageList = $('sultan-sabotage-list');

const bossHud = $('boss-hud');
const bossHudName = $('boss-hud-name');
const bossHudHpFill = $('boss-hud-hp-fill');
const bossHudHpText = $('boss-hud-hp-text');

const giftBanner = $('gift-banner');
const giftBannerEmoji = $('gift-banner-emoji');
const giftBannerTitle = $('gift-banner-title');
const giftBannerSub = $('gift-banner-sub');
const giftBannerCombo = $('gift-banner-combo');

const crisisBanner = $('crisis-banner');
const chatFeed = $('chat-feed');

const recapOverlay = $('recap-overlay');
const recapTitle = $('recap-title');
const recapSub = $('recap-sub');
const recapMvpList = $('recap-mvp-list');
const recapCountdown = $('recap-countdown');

// Simulator / Studio DOM
const inpUsername = $('inp-username');
const btnRandomUser = $('btn-random-user');
const defendGiftGrid = $('defend-gift-grid');
const sabotageGiftGrid = $('sabotage-gift-grid');
const btnLike25 = $('btn-like-25');
const btnLike100 = $('btn-like-100');
const likeProgressText = $('like-progress-text');
const inpChat = $('inp-chat');
const btnSendChat = $('btn-send-chat');
const btnQuickJoin = $('btn-quick-join');
const btnQuickZombie = $('btn-quick-zombie');

const btnAutoLive = $('btn-auto-live');
const selAutoIntensity = $('sel-auto-intensity');
const telCoins = $('tel-coins');
const telCpm = $('tel-cpm');
const telDefPct = $('tel-def-pct');
const telSabPct = $('tel-sab-pct');
const telTugDefBar = $('tel-tug-def-bar');
const telUnits = $('tel-units');
const telFps = $('tel-fps');

const selWeather = $('sel-weather');
const chkBloom = $('chk-bloom');
const chkSfx = $('chk-sfx');
const btnPause = $('btn-pause');
const btnNextRound = $('btn-next-round');
const btnObsMode = $('btn-obs-mode');
const btnExitObs = $('btn-exit-obs');

const connBadge = $('conn-badge');
const inpWsUrl = $('inp-ws-url');
const btnConnectWs = $('btn-connect-ws');

// Modules
const audio = createAudioEngine();
if (startMute) {
  audio.setEnabled(false);
  if (chkSfx) chkSfx.checked = false;
}

const bus = new LiveEventBus();

// Round & Economy State
const MAX_SURVIVORS = 8;
const MAX_ENEMIES = 14;
const ROUND_COMBAT_SEC = 180;
const PREP_SEC = 5.0;
const RECAP_SEC = 10.0;
const GOAL_TARGET = 100;

const state = {
  roundNumber: 1,
  phase: 'PREP', // 'PREP' | 'COMBAT' | 'FINAL_STAND' | 'ENDED'
  phaseTimer: PREP_SEC,
  combatTimeLeft: ROUND_COMBAT_SEC,
  wave: 1,
  barricadeMaxHp: 1200,
  barricadeHp: 1200,
  sessionStartMs: Date.now(),
  sessionCoins: 0,
  roundCoins: 0,
  defendCoins: 0,
  sabotageCoins: 0,
  goalDefend: 0,
  goalSabotage: 0,
  likesCount: 0,
  likesMilestoneMod: 0,
  selectedCombo: 1,
  microCounterDefend: 0,
  microCounterSabotage: 0,
  finalBossSpawned: false,
  crisisAlertTimer: 0,
  directorTimer: 1.5,
  spawningLock: false,
  bannerTimer: 0,
  defendLeaderboard: new Map(),   // user -> coins
  sabotageLeaderboard: new Map(), // user -> coins
  heroRosterMeta: new Map(),      // userLower -> { ownerName, specId, track, level }
  fallenHeroes: [],               // [{ ownerName, specId, level }]
  joinQueue: [],                  // [user]
  botIndex: 1,
};

function fmtTime(sec) {
  const s = Math.max(0, Math.ceil(sec));
  const mm = String(Math.floor(s / 60)).padStart(2, '0');
  const ss = String(s % 60).padStart(2, '0');
  return `${mm}:${ss}`;
}

function addChatLine(badge, text, kind = 'talk') {
  if (!chatFeed) return;
  const row = document.createElement('div');
  row.className = `chat-line ${kind}`;
  const bSpan = document.createElement('span');
  bSpan.className = 'chat-badge';
  bSpan.textContent = badge;
  const tSpan = document.createElement('span');
  tSpan.textContent = ` ${text}`;
  row.appendChild(bSpan);
  row.appendChild(tSpan);
  chatFeed.appendChild(row);
  while (chatFeed.children.length > 5) {
    chatFeed.removeChild(chatFeed.firstChild);
  }
}

function showGiftBanner({ emoji, title, sub, combo = '', faction = 'defend', duration = 2.6 }) {
  if (!giftBanner) return;
  giftBannerEmoji.textContent = emoji;
  giftBannerTitle.textContent = title;
  giftBannerSub.textContent = sub;
  giftBannerCombo.textContent = combo;
  giftBannerCombo.style.display = combo ? 'inline-block' : 'none';
  giftBanner.className = `show ${faction}`;
  state.bannerTimer = duration;
}

function getHeroByOwner(user) {
  const lower = user.toLowerCase();
  return engine.getUnits().find((u) => u.team === 'survivor' && !u.dead && u.ownerName.toLowerCase() === lower);
}

function countLiving(team) {
  return engine.getUnits().filter((u) => u.team === team && !u.dead).length;
}

function getActiveBosses() {
  return engine.getUnits().filter((u) => u.team === 'enemy' && !u.dead && u.isBoss);
}

const engine = createArenaEngine(stageWrap, labelsLayer, audio, {
  onBarricadeDamage(dmg) {
    if (state.phase === 'ENDED') return;
    state.barricadeHp = Math.max(0, state.barricadeHp - dmg);
    engine.setBarricadeVisual(state.barricadeHp / state.barricadeMaxHp);
    if (state.barricadeHp <= 0) {
      finishRound(false, 'Barikade Evakuasi Jebol!');
    }
  },
  onUnitDied(unit) {
    if (unit.team === 'survivor' && !unit.isBot) {
      state.fallenHeroes.push({
        ownerName: unit.ownerName,
        specId: unit.specId,
        level: unit.level,
      });
    }
  },
});

const mockStream = new MockTikTokStream(
  bus,
  () => ({
    barricadeRatio: state.barricadeHp / state.barricadeMaxHp,
    bossAlive: getActiveBosses().length > 0,
    aliveSurvivors: countLiving('survivor'),
    phase: state.phase,
  }),
  (action) => {
    if (action === 'drop_barricade_critical' && state.phase !== 'ENDED') {
      state.barricadeHp = Math.min(state.barricadeHp, Math.round(state.barricadeMaxHp * 0.22));
      engine.setBarricadeVisual(state.barricadeHp / state.barricadeMaxHp);
      addChatLine('⚠️ ALERT', 'Barikade kritis tersisa 22%!!', 'alert-sab');
    }
  }
);

async function spawnOrPromoteHero({ user, minLevel = 3, upgradeBy = 1, isVip = true, isSultan = false }) {
  const existing = getHeroByOwner(user);
  if (existing) {
    await engine.upgradeSurvivor(existing, upgradeBy, minLevel > existing.level ? minLevel : null);
    return existing;
  }

  let livingSurvs = engine.getUnits().filter((u) => u.team === 'survivor' && !u.dead);
  if (livingSurvs.length >= MAX_SURVIVORS) {
    // VIP Cut-Line: sacrifice a bot or lowest-level non-Sultan unit so gift sender enters immediately
    const sacrificial = livingSurvs.find((u) => u.isBot)
      || livingSurvs.filter((u) => !u.isSultan).sort((a, b) => a.level - b.level)[0];
    if (sacrificial) {
      sacrificial.dead = true;
      sacrificial.deadTimer = 4.5; // fade out cleanly
      if (sacrificial.hudEl) sacrificial.hudEl.style.display = 'none';
    }
  }

  const pick = SURVIVORS[Math.floor(Math.random() * SURVIVORS.length)];
  const hero = await engine.spawnSurvivor({
    specId: pick.id,
    ownerName: user,
    level: minLevel,
    isVip,
    isSultan,
  });
  return hero;
}

async function handleGiftEvent(evt) {
  const gMeta = GIFT_CATALOG[evt.giftId];
  if (!gMeta) return;
  if (state.phase === 'ENDED') return;

  const rep = evt.repeatCount || 1;
  const coins = evt.coins || (gMeta.coins * rep);
  state.sessionCoins += coins;
  state.roundCoins += coins;

  // Sultan gifts (500/1K) already unleash their own Airstrike/Boss; cap their community bar contribution to 99 so they don't loop infinite goal triggers
  const goalDelta = Math.min(GOAL_TARGET - 1, coins);
  if (gMeta.faction === 'defend') {
    state.defendCoins += coins;
    state.goalDefend += goalDelta;
    state.defendLeaderboard.set(evt.user, (state.defendLeaderboard.get(evt.user) || 0) + coins);
  } else {
    state.sabotageCoins += coins;
    state.goalSabotage += goalDelta;
    state.sabotageLeaderboard.set(evt.user, (state.sabotageLeaderboard.get(evt.user) || 0) + coins);
  }

  audio.playCoinChime(evt.comboCount || rep, gMeta.faction);

  const comboTag = evt.comboCount > 1 ? `x${evt.comboCount}` : '';
  addChatLine(
    `${gMeta.emoji} @${evt.user}`,
    `kirim ${rep}x ${gMeta.name} (${coins} koin)`,
    gMeta.faction === 'defend' ? 'gift-def' : 'gift-sab'
  );

  showGiftBanner({
    emoji: gMeta.emoji,
    title: `@${evt.user} • ${gMeta.name}`,
    sub: gMeta.shortDesc,
    combo: comboTag,
    faction: gMeta.faction,
    duration: gMeta.coins >= 99 ? 3.4 : 2.3,
  });

  // Execute gift gameplay mechanics
  const waveMult = 1 + (state.wave - 1) * 0.14;
  switch (evt.giftId) {
    case 'rose': {
      engine.triggerHealPulse({ amount: 35 * Math.min(3, rep), shieldSec: 0, repairFlash: false });
      state.barricadeHp = Math.min(state.barricadeMaxHp, state.barricadeHp + 18 * rep);
      engine.setBarricadeVisual(state.barricadeHp / state.barricadeMaxHp);
      state.microCounterDefend += rep;
      if (state.microCounterDefend >= 10) {
        state.microCounterDefend %= 10;
        engine.triggerRageAura(7.5);
        addChatLine('🔥 COMBO x10!', 'FRENZY FIRE RATE 2x AKTIF (7.5s)!', 'gift-def');
      }
      break;
    }

    case 'ice_cream': {
      const cap = Math.min(4, rep);
      for (let i = 0; i < cap; i++) {
        if (countLiving('enemy') < MAX_ENEMIES) {
          engine.spawnEnemy({
            specId: 'zombie_walker_shambler',
            ownerName: i === 0 ? evt.user : null,
            waveMult,
          });
        }
      }
      state.microCounterSabotage += rep;
      if (state.microCounterSabotage >= 10) {
        state.microCounterSabotage %= 10;
        for (let i = 0; i < 3; i++) {
          if (countLiving('enemy') < MAX_ENEMIES + 2) {
            engine.spawnEnemy({ specId: 'zombie_crawler_stalker', waveMult });
          }
        }
        addChatLine('☠️ SWARM x10!', '+3 Feral Crawler menyerbu barikade!', 'gift-sab');
      }
      break;
    }

    case 'finger_heart': {
      const repair = Math.round(state.barricadeMaxHp * 0.08 * Math.min(3, rep));
      state.barricadeHp = Math.min(state.barricadeMaxHp, state.barricadeHp + repair);
      engine.setBarricadeVisual(state.barricadeHp / state.barricadeMaxHp);
      engine.triggerHealPulse({ amount: 60, shieldSec: 5.0 * Math.min(2, rep), repairFlash: true });
      break;
    }

    case 'gg_troll': {
      const n = Math.min(3, rep);
      for (let i = 0; i < n; i++) {
        if (countLiving('enemy') < MAX_ENEMIES) {
          engine.spawnEnemy({ specId: 'zombie_spitter_hazmat', ownerName: evt.user, waveMult });
        }
      }
      break;
    }

    case 'doughnut': {
      await spawnOrPromoteHero({ user: evt.user, minLevel: 3, upgradeBy: 1, isVip: true });
      break;
    }

    case 'cap_horde': {
      const squad = ['zombie_crawler_stalker', 'zombie_banshee_screamer', 'zombie_bloater_boomer'];
      for (const specId of squad) {
        if (countLiving('enemy') < MAX_ENEMIES + 2) {
          engine.spawnEnemy({ specId, ownerName: evt.user, isElite: true, waveMult });
        }
      }
      break;
    }

    case 'corgi_supply': {
      engine.triggerSupplyDrop(evt.user, async () => {
        const alive = engine.getUnits().filter((u) => u.team === 'survivor' && !u.dead);
        for (const u of alive) {
          await engine.upgradeSurvivor(u, 1);
        }
        state.barricadeHp = Math.min(state.barricadeMaxHp, state.barricadeHp + Math.round(state.barricadeMaxHp * 0.15));
        engine.setBarricadeVisual(state.barricadeHp / state.barricadeMaxHp);

        if (state.fallenHeroes.length > 0 && countLiving('survivor') < MAX_SURVIVORS) {
          const revived = state.fallenHeroes.shift();
          await spawnOrPromoteHero({ user: revived.ownerName, minLevel: Math.max(2, revived.level), upgradeBy: 0, isVip: true });
          addChatLine('🐶 REVIVE', `@${revived.ownerName} bangkit kembali ke arena!`, 'gift-def');
        }
      });
      break;
    }

    case 'storm_curse': {
      engine.triggerStormCurse(16.0);
      engine.spawnEnemy({ specId: 'zombie_juggernaut_brute', ownerName: evt.user, isElite: true, waveMult });
      break;
    }

    case 'money_gun': {
      await spawnOrPromoteHero({ user: evt.user, minLevel: 8, upgradeBy: 8, isVip: true, isSultan: true });
      engine.triggerAirstrike(evt.user);
      state.barricadeHp = Math.min(state.barricadeMaxHp, state.barricadeHp + Math.round(state.barricadeMaxHp * 0.22));
      engine.setBarricadeVisual(state.barricadeHp / state.barricadeMaxHp);
      break;
    }

    case 'galaxy_boss': {
      const bosses = getActiveBosses();
      if (bosses.length >= 2) {
        for (const b of bosses) {
          b.maxHp += 350;
          b.hp += 350;
          b.dmg = Math.round(b.dmg * 1.15);
        }
        audio.playBossHorn();
        addChatLine('🌌 ENRAGE BOSS', `@${evt.user} memperkuat semua Boss (+350 HP)!`, 'gift-sab');
      } else {
        const bossSpec = MUTANT_BOSSES[Math.floor(Math.random() * MUTANT_BOSSES.length)];
        await engine.spawnEnemy({ specId: bossSpec.id, ownerName: evt.user, isBoss: true, waveMult });
      }
      break;
    }
  }

  // Collective Dual Goal Milestones (0 -> 100 coins, bounded modulo)
  if (state.goalDefend >= GOAL_TARGET) {
    state.goalDefend = state.goalDefend % GOAL_TARGET;
    addChatLine('✈️ GOAL PENYELAMAT', `100 Koin tembus oleh @${evt.user}! COMMUNITY AIRSTRIKE!`, 'gift-def');
    showGiftBanner({
      emoji: '✈️',
      title: `PENENTU: @${evt.user}!`,
      sub: 'Community Goal 100 Koin → AIRSTRIKE + REPAIR!',
      combo: 'GOAL 100%',
      faction: 'defend',
      duration: 3.5,
    });
    engine.triggerAirstrike(evt.user);
    state.barricadeHp = Math.min(state.barricadeMaxHp, state.barricadeHp + Math.round(state.barricadeMaxHp * 0.12));
    engine.setBarricadeVisual(state.barricadeHp / state.barricadeMaxHp);
  }

  if (state.goalSabotage >= GOAL_TARGET) {
    state.goalSabotage = state.goalSabotage % GOAL_TARGET;
    addChatLine('👾 GOAL PENGHANCUR', `100 Koin tembus oleh @${evt.user}! MUTANT BOSS INVASION!`, 'gift-sab');
    showGiftBanner({
      emoji: '👾',
      title: `INVASI BOSS: @${evt.user}!`,
      sub: 'Sabotage Goal 100 Koin → GIANT MUTANT TURUN!',
      combo: 'GOAL 100%',
      faction: 'sabotage',
      duration: 3.5,
    });
    const bossSpec = MUTANT_BOSSES[Math.floor(Math.random() * MUTANT_BOSSES.length)];
    engine.spawnEnemy({ specId: bossSpec.id, ownerName: evt.user, isBoss: true, waveMult });
  }
}

async function handleChatEvent(evt) {
  const msgLower = evt.message.toLowerCase();
  if (msgLower.startsWith('!join') || msgLower === '1') {
    const existing = getHeroByOwner(evt.user);
    if (existing) {
      addChatLine(`@${evt.user}`, 'Hero kamu sudah bertahan di arena!', 'talk');
      return;
    }
    if (countLiving('survivor') < MAX_SURVIVORS) {
      const pick = SURVIVORS[Math.floor(Math.random() * SURVIVORS.length)];
      await engine.spawnSurvivor({ specId: pick.id, ownerName: evt.user, level: 1, isVip: false });
      addChatLine(`🛡️ @${evt.user}`, `bergabung membawa Pistol Lv.1!`, 'gift-def');
    } else {
      if (!state.joinQueue.includes(evt.user)) state.joinQueue.push(evt.user);
      addChatLine(`⏳ @${evt.user}`, `masuk antrean (${state.joinQueue.length}). Kirim 🍩 Donat untuk potong!`, 'talk');
    }
    return;
  }

  if (msgLower.startsWith('!zombie') || msgLower === '2') {
    if (countLiving('enemy') < MAX_ENEMIES) {
      await engine.spawnEnemy({ specId: 'zombie_walker_shambler', ownerName: evt.user, waveMult: 1 + (state.wave - 1) * 0.14 });
      addChatLine(`☠️ @${evt.user}`, `mengirim 1 Walker gratis!`, 'gift-sab');
    }
    return;
  }

  addChatLine(`@${evt.user}`, evt.message, 'talk');
}

function handleLikeEvent(evt) {
  state.likesCount += evt.count;
  const bucket = Math.floor(state.likesCount / 100);
  if (bucket > state.likesMilestoneMod) {
    state.likesMilestoneMod = bucket;
    const repair = Math.round(state.barricadeMaxHp * 0.03);
    state.barricadeHp = Math.min(state.barricadeMaxHp, state.barricadeHp + repair);
    engine.setBarricadeVisual(state.barricadeHp / state.barricadeMaxHp);
    engine.triggerHealPulse({ amount: 22, shieldSec: 0, repairFlash: false });
    addChatLine('❤️ 100 TAP LIKES', 'Mini Supply aktif! Barikade +3% & Heal Skuad!', 'gift-def');
  }
}

bus.on('gift', handleGiftEvent);
bus.on('chat', handleChatEvent);
bus.on('like', handleLikeEvent);
bus.on('status', ({ status }) => {
  if (!connBadge) return;
  connBadge.textContent = status;
  connBadge.className = status === 'LIVE TERHUBUNG' ? 'conn-pill live' : 'conn-pill mock';
});

async function startNewRound() {
  if (state.spawningLock) return;
  state.spawningLock = true;
  try {
    engine.resetUnitsAndFx();
    bus.clearQueue();
    state.phase = 'PREP';
    state.phaseTimer = PREP_SEC;
    state.combatTimeLeft = ROUND_COMBAT_SEC;
    state.wave = 1;
    state.barricadeMaxHp = 1200;
    state.barricadeHp = 1200;
    state.roundCoins = 0;
    state.finalBossSpawned = false;
    state.directorTimer = 1.2;
    state.fallenHeroes = [];
    state.joinQueue = [];
    engine.setBarricadeVisual(1.0);
    recapOverlay.classList.remove('show');
    vignetteCrisis.classList.remove('active');
    crisisBanner.classList.remove('show');

    // Spawn 3 starter defenders right away so arena feels alive immediately
    await engine.spawnSurvivor({ specId: 'jake_male',   ownerName: 'Unit-Alpha', level: 2, isVip: false });
    await engine.spawnSurvivor({ specId: 'lena_female', ownerName: 'Unit-Bravo', level: 2, isVip: false });
    await engine.spawnSurvivor({ specId: 'rico_male',   ownerName: 'Unit-Delta', level: 2, isVip: false });

    // Early wave scouts walking toward barricade
    await engine.spawnEnemy({ specId: 'zombie_walker_shambler', waveMult: 1.0 });
    await engine.spawnEnemy({ specId: 'zombie_walker_shambler', waveMult: 1.0 });
    await engine.spawnEnemy({ specId: 'zombie_crawler_stalker', waveMult: 1.0 });

    addChatLine('📢 RONDE BARU', `Ronde #${state.roundNumber} dimulai! Ketik !join atau kirim gift!`, 'gift-def');
  } finally {
    state.spawningLock = false;
  }
}

function topEntry(map) {
  let bestName = '-';
  let bestVal = 0;
  for (const [k, v] of map.entries()) {
    if (v > bestVal) { bestVal = v; bestName = `@${k} (${v})`; }
  }
  return bestName;
}

function finishRound(survivorsWon, reasonText) {
  if (state.phase === 'ENDED') return;
  state.phase = 'ENDED';
  state.phaseTimer = RECAP_SEC;
  audio.playRoundEnd(survivorsWon);

  recapTitle.textContent = survivorsWon ? '🏆 EVAKUASI BERHASIL!' : '☠️ MARKAS JEBOL!';
  recapTitle.style.color = survivorsWon ? '#4ade80' : '#f87171';
  recapSub.textContent = `${reasonText} • Total ${state.roundCoins} Koin Ronde Ini`;

  let killLeader = '-';
  let maxKills = 0;
  for (const u of engine.getUnits()) {
    if (u.team === 'survivor' && (u.kills || 0) > maxKills) {
      maxKills = u.kills;
      killLeader = `@${u.ownerName} (${maxKills} Kill)`;
    }
  }

  recapMvpList.innerHTML = `
    <div class="recap-row"><span>🛡️ Top Penyelamat</span><strong>${topEntry(state.defendLeaderboard)}</strong></div>
    <div class="recap-row"><span>☠️ Top Penghancur</span><strong>${topEntry(state.sabotageLeaderboard)}</strong></div>
    <div class="recap-row"><span>🎯 Kill Terbanyak</span><strong>${killLeader}</strong></div>
  `;
  recapOverlay.classList.add('show');
}

// AI Tension Director & Simulation Step
engine.onTick((simDt, rawDt) => {
  bus.pump(2);

  if (state.bannerTimer > 0) {
    state.bannerTimer -= rawDt;
    if (state.bannerTimer <= 0) {
      giftBanner.classList.remove('show');
    }
  }

  // Promote free !join queue if slot opened
  if (state.phase !== 'ENDED' && state.joinQueue.length > 0 && countLiving('survivor') < MAX_SURVIVORS) {
    const nextUser = state.joinQueue.shift();
    if (!getHeroByOwner(nextUser)) {
      const pick = SURVIVORS[Math.floor(Math.random() * SURVIVORS.length)];
      engine.spawnSurvivor({ specId: pick.id, ownerName: nextUser, level: 1, isVip: false });
    }
  }

  if (state.phase === 'PREP') {
    state.phaseTimer -= simDt;
    if (state.phaseTimer <= 0) {
      state.phase = 'COMBAT';
    }
  } else if (state.phase === 'COMBAT' || state.phase === 'FINAL_STAND') {
    state.combatTimeLeft -= simDt;
    const elapsed = ROUND_COMBAT_SEC - state.combatTimeLeft;
    state.wave = Math.min(5, 1 + Math.floor(elapsed / 32));

    if (state.combatTimeLeft <= 30 && state.phase !== 'FINAL_STAND') {
      state.phase = 'FINAL_STAND';
      addChatLine('🚨 FINAL STAND', '30 DETIK TERAKHIR! Serbuan puncak dimulai!', 'alert-sab');
      if (!state.finalBossSpawned && getActiveBosses().length === 0) {
        state.finalBossSpawned = true;
        const bossSpec = MUTANT_BOSSES[Math.floor(Math.random() * MUTANT_BOSSES.length)];
        engine.spawnEnemy({ specId: bossSpec.id, ownerName: 'WaveAkhir', isBoss: true, waveMult: 1.25 });
      }
    }

    if (state.combatTimeLeft <= 0) {
      finishRound(true, 'Helikopter Evakuasi Tiba!');
    }

    // Emergency Cliffhanger check
    const hpRatio = state.barricadeHp / state.barricadeMaxHp;
    const survCount = countLiving('survivor');
    const isCritical = hpRatio < 0.30 || survCount <= 1;
    vignetteCrisis.classList.toggle('active', isCritical);
    crisisBanner.classList.toggle('show', isCritical);
    if (isCritical) {
      state.crisisAlertTimer -= rawDt;
      if (state.crisisAlertTimer <= 0) {
        state.crisisAlertTimer = 3.2;
        audio.playEmergencyBeep();
      }
    }

    // Ensure at least 1 NPC bot keeps fighting if all defenders died so barricade battle stays dramatic until barricade breaks or hero arrives
    // Ambient zombie spawner
    state.directorTimer -= simDt;
    if (state.directorTimer <= 0) {
      const enmAlive = countLiving('enemy');
      const targetPop = state.phase === 'FINAL_STAND' ? 7 : Math.min(6, 2 + state.wave);
      if (enmAlive < targetPop) {
        const pool = state.wave === 1
          ? ['zombie_walker_shambler', 'zombie_walker_shambler', 'zombie_crawler_stalker']
          : state.wave === 2
            ? ['zombie_walker_shambler', 'zombie_crawler_stalker', 'zombie_spitter_hazmat']
            : state.wave === 3
              ? ['zombie_crawler_stalker', 'zombie_banshee_screamer', 'zombie_spitter_hazmat', 'zombie_bloater_boomer']
              : ['zombie_crawler_stalker', 'zombie_banshee_screamer', 'zombie_bloater_boomer', 'zombie_juggernaut_brute'];
        const pick = pool[Math.floor(Math.random() * pool.length)];
        engine.spawnEnemy({ specId: pick, waveMult: 1 + (state.wave - 1) * 0.12 });
      }
      state.directorTimer = hpRatio < 0.30 ? 3.8 : Math.max(1.8, 3.6 - state.wave * 0.35);
    }
  } else if (state.phase === 'ENDED') {
    state.phaseTimer -= rawDt;
    if (recapCountdown) {
      recapCountdown.textContent = `Ronde berikutnya dalam ${Math.max(1, Math.ceil(state.phaseTimer))}s...`;
    }
    if (state.phaseTimer <= 0) {
      state.roundNumber++;
      startNewRound();
    }
  }

  refreshHUD();
});

function renderSultanList(el, map) {
  if (!el) return;
  const sorted = [...map.entries()].sort((a, b) => b[1] - a[1]).slice(0, 3);
  if (sorted.length === 0) {
    el.innerHTML = '<div class="sultan-empty">Belum ada gift</div>';
    return;
  }
  el.innerHTML = sorted
    .map(([u, c], idx) => `<div class="sultan-row"><span>${idx === 0 ? '👑' : `#${idx + 1}`} @${u}</span><b>${c}</b></div>`)
    .join('');
}

function refreshHUD() {
  const stats = engine.getStats();
  const hpPct = Math.max(0, Math.round((state.barricadeHp / state.barricadeMaxHp) * 100));

  hudRoundBadge.textContent = `Ronde #${state.roundNumber}`;
  hudTimer.textContent = state.phase === 'PREP' ? `00:0${Math.ceil(state.phaseTimer)}` : fmtTime(state.combatTimeLeft);

  if (state.phase === 'PREP') {
    hudPhasePill.textContent = 'PERSIAPAN';
    hudPhasePill.className = 'phase-pill prep';
  } else if (state.phase === 'FINAL_STAND') {
    hudPhasePill.textContent = 'FINAL STAND!';
    hudPhasePill.className = 'phase-pill crisis';
  } else if (state.phase === 'ENDED') {
    hudPhasePill.textContent = 'RECAP MVP';
    hudPhasePill.className = 'phase-pill';
  } else {
    hudPhasePill.textContent = `WAVE ${state.wave}/5`;
    hudPhasePill.className = 'phase-pill combat';
  }

  hudBarricadeFill.style.width = `${hpPct}%`;
  hudBarricadeFill.style.background = hpPct > 55 ? '#22c55e' : (hpPct > 28 ? '#f59e0b' : '#ef4444');
  hudBarricadeText.textContent = `🛡️ Markas ${hpPct}% (${Math.round(state.barricadeHp)})`;

  const defPct = Math.min(100, Math.round((state.goalDefend / GOAL_TARGET) * 100));
  const sabPct = Math.min(100, Math.round((state.goalSabotage / GOAL_TARGET) * 100));
  goalDefendFill.style.width = `${defPct}%`;
  goalDefendText.textContent = `✈️ Airstrike ${Math.round(state.goalDefend)}/${GOAL_TARGET}`;
  goalSabotageFill.style.width = `${sabPct}%`;
  goalSabotageText.textContent = `👾 Boss ${Math.round(state.goalSabotage)}/${GOAL_TARGET}`;

  // Active status buffs
  const buffs = [];
  if (stats.rageActive) buffs.push('<span class="buff-pill fire">🔥 FRENZY 2x</span>');
  if (stats.shieldActive) buffs.push('<span class="buff-pill shield">🛡️ PERISAI</span>');
  if (stats.stormActive) buffs.push('<span class="buff-pill storm">⛈️ BADAI ZOMBIE</span>');
  hudBuffs.innerHTML = buffs.join('');

  // Boss HP Bar
  if (stats.topBoss) {
    bossHud.classList.add('show');
    const b = stats.topBoss;
    const bPct = Math.max(0, (b.hp / b.maxHp) * 100);
    bossHudName.textContent = b.ownerName ? `💀 BOSS: @${b.ownerName} • ${b.shortName}` : `💀 ${b.shortName}`;
    bossHudHpFill.style.width = `${bPct}%`;
    bossHudHpText.textContent = `${Math.round(b.hp)} / ${b.maxHp}`;
  } else {
    bossHud.classList.remove('show');
  }

  renderSultanList(sultanDefendList, state.defendLeaderboard);
  renderSultanList(sultanSabotageList, state.sabotageLeaderboard);

  // Studio Telemetry
  if (telCoins) telCoins.textContent = `${state.sessionCoins.toLocaleString('id-ID')} Koin`;
  const mins = Math.max(0.2, (Date.now() - state.sessionStartMs) / 60000);
  if (telCpm) telCpm.textContent = `${Math.round(state.sessionCoins / mins)} / mnt`;
  const totalSide = state.defendCoins + state.sabotageCoins;
  const dShare = totalSide > 0 ? Math.round((state.defendCoins / totalSide) * 100) : 50;
  if (telDefPct) telDefPct.textContent = `🛡️ ${dShare}%`;
  if (telSabPct) telSabPct.textContent = `${100 - dShare}% ☠️`;
  if (telTugDefBar) telTugDefBar.style.width = `${dShare}%`;
  if (telUnits) telUnits.textContent = `${stats.survAlive} Surv / ${stats.enmAlive} Musuh`;
  if (telFps) telFps.textContent = `${stats.fps} FPS`;
  if (likeProgressText) likeProgressText.textContent = `Tap Likes: ${state.likesCount} (Bonus tiap 100)`;
}

// Build Gift Buttons in Left Simulator Panel
function renderGiftButtons() {
  const mkBtn = (g) => {
    const btn = document.createElement('button');
    btn.className = `gift-btn ${g.faction} tier-${g.tier}`;
    btn.dataset.giftId = g.id;
    btn.innerHTML = `
      <div class="gb-top">
        <span class="gb-emoji">${g.emoji}</span>
        <span class="gb-name">${g.name}</span>
        <span class="gb-coin">🪙 ${g.coins}</span>
      </div>
      <div class="gb-desc">${g.shortDesc}</div>
    `;
    btn.addEventListener('click', () => {
      audio.unlock();
      bus.emitGift({
        user: inpUsername.value || 'SultanJakarta',
        giftId: g.id,
        repeatCount: state.selectedCombo,
        source: 'mock',
      });
    });
    return btn;
  };

  for (const g of GIFT_LIST) {
    if (g.faction === 'defend' && defendGiftGrid) defendGiftGrid.appendChild(mkBtn(g));
    if (g.faction === 'sabotage' && sabotageGiftGrid) sabotageGiftGrid.appendChild(mkBtn(g));
  }
}

// Wire Simulator Controls
renderGiftButtons();

document.querySelectorAll('[data-combo]').forEach((btn) => {
  btn.addEventListener('click', () => {
    state.selectedCombo = Number(btn.dataset.combo) || 1;
    document.querySelectorAll('[data-combo]').forEach((b) => b.classList.toggle('active', b === btn));
  });
});

if (btnRandomUser) {
  const sampleNames = ['SultanJakarta', 'BangJago99', 'MbakYanti_Live', 'RajaTroll_ID', 'BosMuda_Sby', 'NengCici'];
  btnRandomUser.addEventListener('click', () => {
    inpUsername.value = sampleNames[Math.floor(Math.random() * sampleNames.length)];
  });
}

if (btnLike25) {
  btnLike25.addEventListener('click', () => {
    audio.unlock();
    bus.emitLike({ user: inpUsername.value || 'Penonton', count: 25 });
  });
}
if (btnLike100) {
  btnLike100.addEventListener('click', () => {
    audio.unlock();
    bus.emitLike({ user: inpUsername.value || 'Penonton', count: 100 });
  });
}
if (btnSendChat) {
  btnSendChat.addEventListener('click', () => {
    audio.unlock();
    const txt = inpChat.value.trim();
    if (!txt) return;
    bus.emitChat({ user: inpUsername.value || 'Penonton', message: txt });
    inpChat.value = '';
  });
}
if (inpChat) {
  inpChat.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') btnSendChat.click();
  });
}
if (btnQuickJoin) {
  btnQuickJoin.addEventListener('click', () => {
    audio.unlock();
    bus.emitChat({ user: inpUsername.value || 'Penonton', message: '!join' });
  });
}
if (btnQuickZombie) {
  btnQuickZombie.addEventListener('click', () => {
    audio.unlock();
    bus.emitChat({ user: inpUsername.value || 'Penonton', message: '!zombie' });
  });
}

if (btnAutoLive) {
  btnAutoLive.addEventListener('click', () => {
    audio.unlock();
    if (mockStream.running) {
      mockStream.stop();
      btnAutoLive.textContent = '🤖 Auto-Live Ramai: OFF';
      btnAutoLive.classList.remove('active-auto');
    } else {
      mockStream.start(selAutoIntensity.value);
      btnAutoLive.textContent = '🤖 Auto-Live Ramai: ON';
      btnAutoLive.classList.add('active-auto');
    }
  });
}
if (selAutoIntensity) {
  selAutoIntensity.addEventListener('change', () => mockStream.setIntensity(selAutoIntensity.value));
}

document.querySelectorAll('[data-scenario]').forEach((btn) => {
  btn.addEventListener('click', () => {
    audio.unlock();
    mockStream.runScenario(btn.dataset.scenario);
  });
});

document.querySelectorAll('[data-cam]').forEach((btn) => {
  btn.addEventListener('click', () => {
    engine.setCameraMode(btn.dataset.cam);
    document.querySelectorAll('[data-cam]').forEach((b) => b.classList.toggle('active', b === btn));
  });
});

if (selWeather) selWeather.addEventListener('change', () => engine.setWeather(selWeather.value));
if (chkBloom) chkBloom.addEventListener('change', () => engine.setBloom(chkBloom.checked));
if (chkSfx) chkSfx.addEventListener('change', () => audio.setEnabled(chkSfx.checked));

if (btnPause) {
  btnPause.addEventListener('click', () => {
    const next = !engine.isPaused();
    engine.setPaused(next);
    btnPause.textContent = next ? '▶ Lanjut' : '⏸ Jeda';
  });
}
if (btnNextRound) {
  btnNextRound.addEventListener('click', () => {
    audio.unlock();
    state.roundNumber++;
    startNewRound();
  });
}
if (btnObsMode) {
  btnObsMode.addEventListener('click', () => {
    document.body.classList.add('obs-mode');
  });
}
if (btnExitObs) {
  btnExitObs.addEventListener('click', () => {
    document.body.classList.remove('obs-mode');
  });
}

if (btnConnectWs) {
  btnConnectWs.addEventListener('click', () => {
    if (bus.ws) {
      bus.disconnectWebSocket();
      btnConnectWs.textContent = 'Hubungkan Bridge';
    } else {
      bus.connectWebSocket(inpWsUrl.value.trim() || 'ws://127.0.0.1:8787');
      btnConnectWs.textContent = 'Putuskan Bridge';
    }
  });
}

// Boot Environment & Start Round #1
(async () => {
  try {
    await engine.initEnvironment();
    await startNewRound();
    if (startAuto && btnAutoLive) {
      mockStream.start(selAutoIntensity ? selAutoIntensity.value : 'medium');
      btnAutoLive.textContent = '🤖 Auto-Live Ramai: ON';
      btnAutoLive.classList.add('active-auto');
    }
    if (wsParam) {
      bus.connectWebSocket(wsParam);
    }
  } catch (err) {
    console.error('Boot error:', err);
    addChatLine('❌ ERROR', 'Gagal memuat aset 3D. Pastikan dijalankan via HTTP server!', 'alert-sab');
  }
})();
