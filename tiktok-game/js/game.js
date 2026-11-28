// Core Fortress Defense Game Loop, AI Tension Director, Dual Evolution (Lv.1-8), Infection & HUD Controller

import {
  SURVIVORS,
  MUTANT_BOSSES,
  GIFT_CATALOG,
  GIFT_LIST,
  getZombieTierMeta,
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

const $ = (id) => document.getElementById(id);
const stageWrap = $('stage-wrap');
const labelsLayer = $('labels-layer');
const vignetteCrisis = $('vignette-crisis');

const hudPhasePill = $('hud-phase-pill');
const hudTimer = $('hud-timer');
const hudRoundBadge = $('hud-round-badge');
const hudHumanFill = $('hud-human-fill');
const hudHumanText = $('hud-human-text');
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
const btnQuickManusia = $('btn-quick-manusia');
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
const sliderZoom = $('slider-zoom');
const zoomVal = $('zoom-val');
const chkCompactHud = $('chk-compact-hud');
const chkMiniLabels = $('chk-mini-labels');
const btnPause = $('btn-pause');
const btnNextRound = $('btn-next-round');
const btnObsMode = $('btn-obs-mode');
const btnExitObs = $('btn-exit-obs');

const connBadge = $('conn-badge');
const inpWsUrl = $('inp-ws-url');
const btnConnectWs = $('btn-connect-ws');

const audio = createAudioEngine();
if (startMute) {
  audio.setEnabled(false);
  if (chkSfx) chkSfx.checked = false;
}

const bus = new LiveEventBus();

// Fortress Defense Economy & Round Constants
const MAX_SURVIVORS = 8;
const MAX_ENEMIES = 12;
const ROUND_COMBAT_SEC = 180;
const PREP_SEC = 5.0;
const RECAP_SEC = 10.0;
const GOAL_TARGET = 100;
const BASE_MAX_HP = 3000;

const state = {
  roundNumber: 1,
  phase: 'PREP', // 'PREP' | 'COMBAT' | 'FINAL_WAVE' | 'ENDED'
  phaseTimer: PREP_SEC,
  combatTimeLeft: ROUND_COMBAT_SEC,
  wave: 1,
  humanBaseMaxHp: BASE_MAX_HP,
  humanBaseHp: BASE_MAX_HP,
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
  crisisAlertTimer: 0,
  directorTimer: 1.5,
  spawningLock: false,
  bannerTimer: 0,
  variantSeq: 0,
  defendLeaderboard: new Map(),
  sabotageLeaderboard: new Map(),
  survivorProfiles: new Map(), // userLower -> { ownerName, specId, level }
  zombieProfiles: new Map(),   // userLower -> { ownerName, level, variantIdx }
  respawnQueue: [],            // [{ faction, user, delay, pos }]
  fallenHeroes: [],
  joinQueue: [],
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

function showGiftBanner({ emoji, title, sub, combo = '', faction = 'defend', duration = 2.5 }) {
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

function getEnemyByOwner(user) {
  const lower = user.toLowerCase();
  return engine.getUnits().find((u) => u.team === 'enemy' && !u.dead && u.ownerName && u.ownerName.toLowerCase() === lower);
}

function countLiving(team) {
  return engine.getUnits().filter((u) => u.team === team && !u.dead).length;
}

function getActiveBosses() {
  return engine.getUnits().filter((u) => u.team === 'enemy' && !u.dead && u.isBoss);
}

const engine = createArenaEngine(stageWrap, labelsLayer, audio, {
  onHumanBaseDamage(dmg) {
    if (state.phase === 'ENDED') return;
    state.humanBaseHp = Math.max(0, state.humanBaseHp - dmg);
    engine.setHumanBaseVisual(state.humanBaseHp / state.humanBaseMaxHp);
    if (state.humanBaseHp <= 0) {
      finishRound(false, 'Gerbang Benteng Jebol oleh Serbuan Zombie!');
    }
  },
  onUnitDied(unit) {
    if (unit.team === 'survivor' && !unit.isBot) {
      state.fallenHeroes.push({ ownerName: unit.ownerName, specId: unit.specId, level: unit.level });
      // Schedule Turned-Zombie Infection + Hero Respawn
      state.respawnQueue.push({
        kind: 'infect',
        user: unit.ownerName,
        delay: 2.6,
        pos: unit.group.position.clone(),
      });
      state.respawnQueue.push({
        kind: 'human_respawn',
        user: unit.ownerName,
        delay: 6.2,
      });
    } else if (unit.team === 'enemy' && unit.ownerName && !unit.isInfected) {
      state.respawnQueue.push({
        kind: 'zombie_respawn',
        user: unit.ownerName,
        delay: 5.2,
      });
    }
  },
});

const mockStream = new MockTikTokStream(
  bus,
  () => ({
    humanBaseRatio: state.humanBaseHp / state.humanBaseMaxHp,
    bossAlive: getActiveBosses().length > 0,
    finalWave: state.phase === 'FINAL_WAVE',
    phase: state.phase,
  }),
  (action) => {
    if (action === 'drop_barricade_critical' && state.phase !== 'ENDED') {
      state.humanBaseHp = Math.min(state.humanBaseHp, Math.round(state.humanBaseMaxHp * 0.22));
      engine.setHumanBaseVisual(state.humanBaseHp / state.humanBaseMaxHp);
      addChatLine('⚠️ ALERT', 'Gerbang Benteng Manusia kritis tersisa 22%!!', 'alert-sab');
    }
  }
);

function cureInfectedCopy(user) {
  const lower = user.toLowerCase();
  const inf = engine.getUnits().find((u) => u.team === 'enemy' && !u.dead && u.isInfected && u.ownerName?.toLowerCase() === lower);
  if (inf) {
    inf.hp = 0;
    inf.dead = true;
    inf.deadTimer = 4.6;
    if (inf.hudEl) inf.hudEl.style.display = 'none';
    addChatLine('💊 DISEMBUHKAN', `@${user} pulih dari infeksi zombie!`, 'gift-def');
  }
}

async function spawnOrPromoteHero({ user, minLevel = 1, upgradeBy = 1, isVip = true, isSultan = false }) {
  const lower = user.toLowerCase();
  cureInfectedCopy(user);

  const prof = state.survivorProfiles.get(lower) || {
    ownerName: user,
    specId: SURVIVORS[Math.floor(Math.random() * SURVIVORS.length)].id,
    level: 1,
  };
  prof.level = Math.min(8, Math.max(prof.level, minLevel));
  state.survivorProfiles.set(lower, prof);

  const existing = getHeroByOwner(user);
  if (existing) {
    await engine.upgradeSurvivor(existing, upgradeBy, minLevel > existing.level ? minLevel : null);
    prof.level = existing.level;
    return existing;
  }

  const livingSurvs = engine.getUnits().filter((u) => u.team === 'survivor' && !u.dead);
  if (livingSurvs.length >= MAX_SURVIVORS) {
    const sacrificial = livingSurvs.find((u) => u.isBot)
      || livingSurvs.filter((u) => !u.isSultan).sort((a, b) => a.level - b.level)[0];
    if (sacrificial) {
      sacrificial.dead = true;
      sacrificial.deadTimer = 4.5;
      if (sacrificial.hudEl) sacrificial.hudEl.style.display = 'none';
    }
  }

  return engine.spawnSurvivor({
    specId: prof.specId,
    ownerName: user,
    level: prof.level,
    isVip,
    isSultan: isSultan || prof.level >= 8,
  });
}

async function spawnOrEvolveZombie({ user, minLevel = 1, upgradeBy = 0 }) {
  const lower = user.toLowerCase();
  const prof = state.zombieProfiles.get(lower) || {
    ownerName: user,
    level: 1,
    variantIdx: state.variantSeq++,
  };
  const nextLv = Math.min(8, Math.max(prof.level + upgradeBy, minLevel));
  prof.level = nextLv;
  state.zombieProfiles.set(lower, prof);

  const waveMult = 1 + (state.wave - 1) * 0.14;
  const existing = getEnemyByOwner(user);
  if (existing && !existing.isInfected) {
    if (nextLv > existing.level) {
      return engine.evolveEnemy(existing, nextLv, waveMult);
    }
    existing.hp = existing.maxHp;
    return existing;
  }

  const livingEnm = engine.getUnits().filter((u) => u.team === 'enemy' && !u.dead);
  if (livingEnm.length >= MAX_ENEMIES) {
    const sacrificial = livingEnm.find((u) => u.isBot && !u.isBoss)
      || livingEnm.filter((u) => !u.isBoss).sort((a, b) => (a.level || 1) - (b.level || 1))[0];
    if (sacrificial) {
      sacrificial.dead = true;
      sacrificial.deadTimer = 4.5;
      if (sacrificial.hudEl) sacrificial.hudEl.style.display = 'none';
    }
  }

  const meta = getZombieTierMeta(prof.level, prof.variantIdx);
  return engine.spawnEnemy({
    specId: meta.specId,
    ownerName: user,
    level: prof.level,
    variantIdx: prof.variantIdx,
    isBoss: meta.isBoss,
    isElite: prof.level >= 6,
    waveMult,
  });
}

function healBase(amount) {
  if (state.phase === 'ENDED') return;
  state.humanBaseHp = Math.min(state.humanBaseMaxHp, state.humanBaseHp + amount);
  engine.setHumanBaseVisual(state.humanBaseHp / state.humanBaseMaxHp);
}

async function handleGiftEvent(evt) {
  const gMeta = GIFT_CATALOG[evt.giftId];
  if (!gMeta || state.phase === 'ENDED') return;

  const rep = evt.repeatCount || 1;
  const coins = evt.coins || (gMeta.coins * rep);
  state.sessionCoins += coins;
  state.roundCoins += coins;

  // Sultan gifts (500/1K) already unleash their own Airstrike/Boss; process goal modulo synchronously before any await
  const goalDelta = Math.min(GOAL_TARGET - 1, coins);
  let triggeredDefendGoal = false;
  let triggeredSabotageGoal = false;
  if (gMeta.faction === 'defend') {
    state.defendCoins += coins;
    state.goalDefend += goalDelta;
    if (state.goalDefend >= GOAL_TARGET) {
      state.goalDefend = state.goalDefend % GOAL_TARGET;
      triggeredDefendGoal = true;
    }
    state.defendLeaderboard.set(evt.user, (state.defendLeaderboard.get(evt.user) || 0) + coins);
  } else {
    state.sabotageCoins += coins;
    state.goalSabotage += goalDelta;
    if (state.goalSabotage >= GOAL_TARGET) {
      state.goalSabotage = state.goalSabotage % GOAL_TARGET;
      triggeredSabotageGoal = true;
    }
    state.sabotageLeaderboard.set(evt.user, (state.sabotageLeaderboard.get(evt.user) || 0) + coins);
  }

  audio.playCoinChime(evt.comboCount || rep, gMeta.faction);

  const comboTag = evt.comboCount > 1 ? `x${evt.comboCount}` : '';
  addChatLine(`${gMeta.emoji} @${evt.user}`, `kirim ${rep}x ${gMeta.name} (${coins} koin)`, gMeta.faction === 'defend' ? 'gift-def' : 'gift-sab');

  showGiftBanner({
    emoji: gMeta.emoji,
    title: `@${evt.user} • ${gMeta.name}`,
    sub: gMeta.shortDesc,
    combo: comboTag,
    faction: gMeta.faction,
    duration: gMeta.coins >= 99 ? 3.2 : 2.2,
  });

  const waveMult = 1 + (state.wave - 1) * 0.14;
  switch (evt.giftId) {
    case 'rose': {
      engine.triggerHealPulse({ amount: 35 * Math.min(3, rep), shieldSec: 0 });
      healBase(20 * rep);
      cureInfectedCopy(evt.user);
      state.microCounterDefend += rep;
      if (state.microCounterDefend >= 10) {
        state.microCounterDefend %= 10;
        engine.triggerRageAura(7.5);
        addChatLine('🔥 COMBO x10!', 'FRENZY FIRE RATE 2x BENTENG AKTIF!', 'gift-def');
      }
      break;
    }

    case 'ice_cream': {
      await spawnOrEvolveZombie({ user: evt.user, minLevel: 2, upgradeBy: rep >= 5 ? 1 : 0 });
      state.microCounterSabotage += rep;
      if (state.microCounterSabotage >= 10) {
        state.microCounterSabotage %= 10;
        for (let i = 0; i < 3; i++) {
          if (countLiving('enemy') < MAX_ENEMIES + 2) {
            engine.spawnEnemy({ specId: 'zombie_crawler_stalker', waveMult });
          }
        }
        addChatLine('☠️ SWARM x10!', '+3 Feral Crawler menyerbu Gerbang Benteng!', 'gift-sab');
      }
      break;
    }

    case 'finger_heart': {
      healBase(Math.round(state.humanBaseMaxHp * 0.08 * Math.min(3, rep)));
      engine.triggerHealPulse({ amount: 60, shieldSec: 5.0 * Math.min(2, rep), repairFlash: true });
      break;
    }

    case 'gg_troll': {
      engine.triggerHordeFrenzy(6.0);
      await spawnOrEvolveZombie({ user: evt.user, minLevel: 3, upgradeBy: 1 });
      break;
    }

    case 'doughnut': {
      await spawnOrPromoteHero({ user: evt.user, minLevel: 3, upgradeBy: 1, isVip: true });
      break;
    }

    case 'cap_horde': {
      await spawnOrEvolveZombie({ user: evt.user, minLevel: 4, upgradeBy: 1 });
      for (const specId of ['zombie_crawler_stalker', 'zombie_bloater_boomer']) {
        if (countLiving('enemy') < MAX_ENEMIES + 1) {
          engine.spawnEnemy({ specId, isElite: true, waveMult });
        }
      }
      break;
    }

    case 'corgi_supply': {
      engine.triggerSupplyDrop(evt.user, async () => {
        const alive = engine.getUnits().filter((u) => u.team === 'survivor' && !u.dead);
        for (const u of alive) {
          await engine.upgradeSurvivor(u, 1);
          const prof = state.survivorProfiles.get(u.ownerName.toLowerCase());
          if (prof) prof.level = u.level;
        }
        healBase(Math.round(state.humanBaseMaxHp * 0.14));
        if (state.fallenHeroes.length > 0 && countLiving('survivor') < MAX_SURVIVORS) {
          const revived = state.fallenHeroes.shift();
          await spawnOrPromoteHero({ user: revived.ownerName, minLevel: Math.max(2, revived.level), upgradeBy: 0, isVip: true });
          addChatLine('🐶 REVIVE', `@${revived.ownerName} bangkit di Gerbang Benteng!`, 'gift-def');
        }
      });
      break;
    }

    case 'storm_curse': {
      engine.triggerStormCurse(16.0);
      await spawnOrEvolveZombie({ user: evt.user, minLevel: 6, upgradeBy: 1 });
      break;
    }

    case 'money_gun': {
      await spawnOrPromoteHero({ user: evt.user, minLevel: 8, upgradeBy: 8, isVip: true, isSultan: true });
      engine.triggerAirstrike(evt.user);
      healBase(Math.round(state.humanBaseMaxHp * 0.20));
      break;
    }

    case 'galaxy_boss': {
      const bosses = getActiveBosses();
      const existingOwner = getEnemyByOwner(evt.user);
      if (bosses.length >= 2 && (!existingOwner || !existingOwner.isBoss)) {
        for (const b of bosses) {
          b.maxHp += 380;
          b.hp += 380;
        }
        audio.playBossHorn();
        addChatLine('🌌 ENRAGE TITAN', `@${evt.user} memacu semua Boss Titan (+380 HP)!`, 'gift-sab');
      } else {
        await spawnOrEvolveZombie({ user: evt.user, minLevel: 8, upgradeBy: 8 });
      }
      break;
    }
  }

  // Collective Dual Goal Milestones (triggered via pre-clamped flags so HUD never shows >=100)
  if (triggeredDefendGoal) {
    addChatLine('✈️ GOAL BENTENG', `100 Koin oleh @${evt.user}! COMMUNITY AIRSTRIKE!`, 'gift-def');
    showGiftBanner({
      emoji: '✈️',
      title: `PENENTU: @${evt.user}!`,
      sub: 'Goal 100 Koin → AIRSTRIKE ke Gerombolan Zombie!',
      combo: 'GOAL 100%',
      faction: 'defend',
      duration: 3.4,
    });
    engine.triggerAirstrike(evt.user);
    healBase(Math.round(state.humanBaseMaxHp * 0.10));
  }

  if (triggeredSabotageGoal) {
    addChatLine('👾 GOAL HORDE', `100 Koin oleh @${evt.user}! GIANT MUTANT BOSS!`, 'gift-sab');
    showGiftBanner({
      emoji: '👾',
      title: `INVASI BOSS: @${evt.user}!`,
      sub: 'Goal 100 Koin → GIANT MUTANT BOSS TURUN!',
      combo: 'GOAL 100%',
      faction: 'sabotage',
      duration: 3.4,
    });
    const bossSpec = MUTANT_BOSSES[Math.floor(Math.random() * MUTANT_BOSSES.length)];
    engine.spawnEnemy({ specId: bossSpec.id, ownerName: evt.user, level: 8, isBoss: true, waveMult });
  }
}

async function handleChatEvent(evt) {
  const msgLower = evt.message.toLowerCase();
  if (msgLower.startsWith('!manusia') || msgLower.startsWith('!join') || msgLower === '1') {
    const existing = getHeroByOwner(evt.user);
    if (existing) {
      addChatLine(`@${evt.user}`, 'Hero kamu sudah berjuang di medan perang!', 'talk');
      return;
    }
    if (countLiving('survivor') < MAX_SURVIVORS) {
      await spawnOrPromoteHero({ user: evt.user, minLevel: 1, upgradeBy: 0, isVip: false });
      addChatLine(`🏰 @${evt.user}`, `bergabung membela Benteng (Lv.1 Pistol)!`, 'gift-def');
    } else {
      if (!state.joinQueue.includes(evt.user)) state.joinQueue.push(evt.user);
      addChatLine(`⏳ @${evt.user}`, `antrean penuh (${state.joinQueue.length}). Kirim 🍩 Donat potong antrean!`, 'talk');
    }
    return;
  }

  if (msgLower.startsWith('!zombie') || msgLower === '2') {
    const existing = getEnemyByOwner(evt.user);
    if (existing) {
      addChatLine(`@${evt.user}`, `Zombie Lv.${existing.level || 1} kamu sedang menyerbu Benteng!`, 'talk');
      return;
    }
    await spawnOrEvolveZombie({ user: evt.user, minLevel: 1, upgradeBy: 0 });
    addChatLine(`☠️ @${evt.user}`, `datang dari kabut timur sebagai Walker Lv.1!`, 'gift-sab');
    return;
  }

  addChatLine(`@${evt.user}`, evt.message, 'talk');
}

function handleLikeEvent(evt) {
  state.likesCount += evt.count;
  const bucket = Math.floor(state.likesCount / 100);
  if (bucket > state.likesMilestoneMod) {
    state.likesMilestoneMod = bucket;
    healBase(Math.round(state.humanBaseMaxHp * 0.03));
    engine.triggerHealPulse({ amount: 22, shieldSec: 0 });
    addChatLine('❤️ 100 TAP LIKES', 'Bantuan Amunisi & +3% Repair Benteng!', 'gift-def');
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
    state.humanBaseHp = state.humanBaseMaxHp;
    state.roundCoins = 0;
    state.directorTimer = 1.4;
    state.fallenHeroes = [];
    state.joinQueue = [];
    state.respawnQueue = [];
    state.survivorProfiles.clear();
    state.zombieProfiles.clear();
    engine.setHumanBaseVisual(1.0);
    engine.setFinalWave(false);
    recapOverlay.classList.remove('show');
    vignetteCrisis.classList.remove('active');
    crisisBanner.classList.remove('show');

    // Starter Fortress Defenders vs Incoming Zombie Wave
    await engine.spawnSurvivor({ specId: 'jake_male',   ownerName: 'Unit-Alpha', level: 2, isVip: false });
    await engine.spawnSurvivor({ specId: 'lena_female', ownerName: 'Unit-Bravo', level: 2, isVip: false });
    await engine.spawnSurvivor({ specId: 'rico_male',   ownerName: 'Unit-Delta', level: 2, isVip: false });

    await engine.spawnEnemy({ specId: 'zombie_walker_shambler', level: 1, waveMult: 1.0 });
    await engine.spawnEnemy({ specId: 'zombie_walker_shambler', level: 1, waveMult: 1.0 });
    await engine.spawnEnemy({ specId: 'zombie_crawler_stalker', level: 2, waveMult: 1.0 });

    addChatLine('🛡️ PERTAHANAN BENTENG', `Ronde #${state.roundNumber}! Ketik !manusia (1) atau !zombie (2)!`, 'gift-def');
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

function finishRound(humanWon, reasonText) {
  if (state.phase === 'ENDED') return;
  state.phase = 'ENDED';
  state.phaseTimer = RECAP_SEC;
  engine.setFinalWave(false);
  audio.playRoundEnd(humanWon);

  recapTitle.textContent = humanWon ? '🏆 BENTENG BERTAHAN!' : '☠️ BENTENG JEBOL!';
  recapTitle.style.color = humanWon ? '#4ade80' : '#f87171';
  recapSub.textContent = `${reasonText} • Total ${state.roundCoins} Koin Ronde Ini`;

  let killLeader = '-';
  let maxKills = 0;
  for (const u of engine.getUnits()) {
    if ((u.kills || 0) > maxKills) {
      maxKills = u.kills;
      killLeader = `@${u.ownerName || u.shortName} (${maxKills} Kill)`;
    }
  }

  recapMvpList.innerHTML = `
    <div class="recap-row"><span>🛡️ Top Penyelamat</span><strong>${topEntry(state.defendLeaderboard)}</strong></div>
    <div class="recap-row"><span>☠️ Top Penghancur</span><strong>${topEntry(state.sabotageLeaderboard)}</strong></div>
    <div class="recap-row"><span>🎯 Kill Terbanyak</span><strong>${killLeader}</strong></div>
  `;
  recapOverlay.classList.add('show');
}

// AI Tension Director, Respawn & Infection Tick
engine.onTick((simDt, rawDt) => {
  bus.pump(2);

  if (state.bannerTimer > 0) {
    state.bannerTimer -= rawDt;
    if (state.bannerTimer <= 0) giftBanner.classList.remove('show');
  }

  // Process respawns & Turned-Zombie Infection timers
  if (state.phase !== 'ENDED' && simDt > 0) {
    for (let i = state.respawnQueue.length - 1; i >= 0; i--) {
      const rq = state.respawnQueue[i];
      rq.delay -= simDt;
      if (rq.delay <= 0) {
        state.respawnQueue.splice(i, 1);
        if (rq.kind === 'infect') {
          // Turn fallen survivor into infected zombie if not already alive on human side
          if (!getHeroByOwner(rq.user) && countLiving('enemy') < MAX_ENEMIES + 2) {
            engine.spawnEnemy({
              specId: 'zombie_crawler_stalker',
              ownerName: rq.user,
              level: 2,
              isInfected: true,
              waveMult: 1 + (state.wave - 1) * 0.14,
              posOverride: rq.pos,
            });
            addChatLine('☣️ TERINFEKSI!', `@${rq.user} bangkit jadi ZOMBIE menyerang Benteng!`, 'alert-sab');
          }
        } else if (rq.kind === 'human_respawn') {
          const prof = state.survivorProfiles.get(rq.user.toLowerCase());
          if (prof && !getHeroByOwner(rq.user) && countLiving('survivor') < MAX_SURVIVORS) {
            spawnOrPromoteHero({ user: prof.ownerName, minLevel: prof.level, upgradeBy: 0, isVip: prof.level >= 3 });
          }
        } else if (rq.kind === 'zombie_respawn') {
          const zprof = state.zombieProfiles.get(rq.user.toLowerCase());
          if (zprof && !getEnemyByOwner(rq.user) && countLiving('enemy') < MAX_ENEMIES) {
            spawnOrEvolveZombie({ user: zprof.ownerName, minLevel: zprof.level, upgradeBy: 0 });
          }
        }
      }
    }
  }

  // Promote free !manusia queue
  if (state.phase !== 'ENDED' && state.joinQueue.length > 0 && countLiving('survivor') < MAX_SURVIVORS) {
    const nextUser = state.joinQueue.shift();
    if (!getHeroByOwner(nextUser)) {
      spawnOrPromoteHero({ user: nextUser, minLevel: 1, upgradeBy: 0, isVip: false });
    }
  }

  if (state.phase === 'PREP') {
    state.phaseTimer -= simDt;
    if (state.phaseTimer <= 0) state.phase = 'COMBAT';
  } else if (state.phase === 'COMBAT' || state.phase === 'FINAL_WAVE') {
    state.combatTimeLeft -= simDt;
    const elapsed = ROUND_COMBAT_SEC - state.combatTimeLeft;
    state.wave = Math.min(5, 1 + Math.floor(elapsed / 32));
    if (state.phase === 'COMBAT' && state.combatTimeLeft <= 30) {
      state.phase = 'FINAL_WAVE';
      engine.setFinalWave(true);
      audio.playBossHorn();
      addChatLine('🔥 FINAL WAVE!', '30 DETIK TERAKHIR! ZOMBIE MENGGILA!', 'alert-sab');
    }
    if (state.combatTimeLeft <= 0) {
      state.combatTimeLeft = 0;
      finishRound(true, 'Benteng Manusia Berhasil Bertahan Hingga Evakuasi!');
      return;
    }

    // Fortress Critical Health Check
    const hRatio = state.humanBaseHp / state.humanBaseMaxHp;
    const isHumanCrit = hRatio < 0.30;

    vignetteCrisis.classList.toggle('active', isHumanCrit || state.phase === 'FINAL_WAVE');
    if (isHumanCrit) {
      crisisBanner.textContent = '⚠️ BENTENG MANUSIA KRITIS! KIRIM 🌹 ROSE / 🫶 HEART!';
      crisisBanner.classList.add('show');
    } else {
      crisisBanner.classList.remove('show');
    }

    if (isHumanCrit) {
      state.crisisAlertTimer -= rawDt;
      if (state.crisisAlertTimer <= 0) {
        state.crisisAlertTimer = 3.2;
        audio.playEmergencyBeep();
      }
    }

    // Ambient Wave Spawner Director from East fog road
    state.directorTimer -= simDt;
    if (state.directorTimer <= 0) {
      const waveMult = 1 + (state.wave - 1) * 0.12;
      if (countLiving('survivor') < 3) {
        const pick = SURVIVORS[Math.floor(Math.random() * SURVIVORS.length)];
        engine.spawnSurvivor({ specId: pick.id, ownerName: `Unit-${1 + Math.floor(Math.random() * 9)}`, level: Math.min(3, state.wave), isVip: false });
      }
      const targetPop = state.phase === 'FINAL_WAVE' ? 7 : Math.min(5, 2 + state.wave);
      if (countLiving('enemy') < targetPop) {
        const pool = state.wave <= 2
          ? ['zombie_walker_shambler', 'zombie_crawler_stalker', 'zombie_spitter_hazmat']
          : ['zombie_crawler_stalker', 'zombie_banshee_screamer', 'zombie_spitter_hazmat', 'zombie_bloater_boomer', 'zombie_juggernaut_brute'];
        const pick = pool[Math.floor(Math.random() * pool.length)];
        engine.spawnEnemy({ specId: pick, level: state.wave, waveMult });
      }
      state.directorTimer = state.phase === 'FINAL_WAVE' ? 1.8 : Math.max(2.1, 3.8 - state.wave * 0.32);
    }
  } else if (state.phase === 'ENDED') {
    state.phaseTimer -= rawDt;
    if (recapCountdown) recapCountdown.textContent = `Ronde berikutnya dalam ${Math.max(1, Math.ceil(state.phaseTimer))}s...`;
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
  const hPct = Math.max(0, Math.round((state.humanBaseHp / state.humanBaseMaxHp) * 100));

  hudRoundBadge.textContent = `Ronde #${state.roundNumber}`;
  if (state.phase === 'PREP') hudTimer.textContent = `00:0${Math.ceil(state.phaseTimer)}`;
  else hudTimer.textContent = fmtTime(state.combatTimeLeft);

  if (state.phase === 'PREP') {
    hudPhasePill.textContent = 'PERSIAPAN';
    hudPhasePill.className = 'phase-pill prep';
  } else if (state.phase === 'FINAL_WAVE') {
    hudPhasePill.textContent = 'FINAL WAVE';
    hudPhasePill.className = 'phase-pill crisis';
  } else if (state.phase === 'ENDED') {
    hudPhasePill.textContent = 'RECAP MVP';
    hudPhasePill.className = 'phase-pill';
  } else {
    hudPhasePill.textContent = `WAVE ${state.wave}/5`;
    hudPhasePill.className = 'phase-pill combat';
  }

  hudHumanFill.style.width = `${hPct}%`;
  hudHumanFill.style.background = hPct > 55 ? '#22c55e' : (hPct > 28 ? '#f59e0b' : '#ef4444');
  hudHumanText.textContent = `🏰 HP Benteng Manusia ${hPct}%`;

  const defPct = Math.min(100, Math.round((state.goalDefend / GOAL_TARGET) * 100));
  const sabPct = Math.min(100, Math.round((state.goalSabotage / GOAL_TARGET) * 100));
  goalDefendFill.style.width = `${defPct}%`;
  goalDefendText.textContent = `✈️ Airstrike ${Math.round(state.goalDefend)}/${GOAL_TARGET}`;
  goalSabotageFill.style.width = `${sabPct}%`;
  goalSabotageText.textContent = `👾 Boss ${Math.round(state.goalSabotage)}/${GOAL_TARGET}`;

  const buffs = [];
  if (stats.rageActive) buffs.push('<span class="buff-pill fire">🔥 FRENZY 2x</span>');
  if (stats.hordeRageActive) buffs.push('<span class="buff-pill storm">☠️ HORDE SPEED</span>');
  if (stats.shieldActive) buffs.push('<span class="buff-pill shield">🛡️ PERISAI</span>');
  if (stats.stormActive) buffs.push('<span class="buff-pill storm">⛈️ BADAI ZOMBIE</span>');
  hudBuffs.innerHTML = buffs.join('');

  if (stats.topBoss) {
    bossHud.classList.add('show');
    const b = stats.topBoss;
    bossHudName.textContent = b.ownerName ? `👑 BOSS: @${b.ownerName} • ${b.shortName}` : `💀 ${b.shortName}`;
    bossHudHpFill.style.width = `${Math.max(0, (b.hp / b.maxHp) * 100)}%`;
    bossHudHpText.textContent = `${Math.round(b.hp)} / ${b.maxHp}`;
  } else {
    bossHud.classList.remove('show');
  }

  renderSultanList(sultanDefendList, state.defendLeaderboard);
  renderSultanList(sultanSabotageList, state.sabotageLeaderboard);

  if (telCoins) telCoins.textContent = `${state.sessionCoins.toLocaleString('id-ID')} Koin`;
  const mins = Math.max(0.2, (Date.now() - state.sessionStartMs) / 60000);
  if (telCpm) telCpm.textContent = `${Math.round(state.sessionCoins / mins)} / mnt`;
  const totalSide = state.defendCoins + state.sabotageCoins;
  const dShare = totalSide > 0 ? Math.round((state.defendCoins / totalSide) * 100) : 50;
  if (telDefPct) telDefPct.textContent = `🛡️ ${dShare}%`;
  if (telSabPct) telSabPct.textContent = `${100 - dShare}% ☠️`;
  if (telTugDefBar) telTugDefBar.style.width = `${dShare}%`;
  if (telUnits) telUnits.textContent = `${stats.survAlive} Surv / ${stats.enmAlive} Zomb`;
  if (telFps) telFps.textContent = `${stats.fps} FPS`;
  if (likeProgressText) likeProgressText.textContent = `Tap Likes: ${state.likesCount} (Bonus tiap 100)`;
}

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

if (btnLike25) btnLike25.addEventListener('click', () => { audio.unlock(); bus.emitLike({ user: inpUsername.value || 'Penonton', count: 25 }); });
if (btnLike100) btnLike100.addEventListener('click', () => { audio.unlock(); bus.emitLike({ user: inpUsername.value || 'Penonton', count: 100 }); });
if (btnSendChat) {
  btnSendChat.addEventListener('click', () => {
    audio.unlock();
    const txt = inpChat.value.trim();
    if (!txt) return;
    bus.emitChat({ user: inpUsername.value || 'Penonton', message: txt });
    inpChat.value = '';
  });
}
if (inpChat) inpChat.addEventListener('keydown', (e) => { if (e.key === 'Enter') btnSendChat.click(); });
if (btnQuickManusia) btnQuickManusia.addEventListener('click', () => { audio.unlock(); bus.emitChat({ user: inpUsername.value || 'Penonton', message: '!manusia' }); });
if (btnQuickZombie) btnQuickZombie.addEventListener('click', () => { audio.unlock(); bus.emitChat({ user: inpUsername.value || 'Penonton', message: '!zombie' }); });

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
if (selAutoIntensity) selAutoIntensity.addEventListener('change', () => mockStream.setIntensity(selAutoIntensity.value));

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
if (chkBloom) {
  chkBloom.checked = false;
  chkBloom.addEventListener('change', () => engine.setBloom(chkBloom.checked));
}
if (chkSfx) chkSfx.addEventListener('change', () => audio.setEnabled(chkSfx.checked));
if (sliderZoom) {
  sliderZoom.addEventListener('input', () => {
    const v = parseFloat(sliderZoom.value) || 1.0;
    engine.setZoomScale(v);
    if (zoomVal) zoomVal.textContent = `${v.toFixed(2)}x`;
  });
}
if (chkCompactHud) chkCompactHud.addEventListener('change', () => document.body.classList.toggle('compact-hud', chkCompactHud.checked));
if (chkMiniLabels) chkMiniLabels.addEventListener('change', () => document.body.classList.toggle('mini-labels', chkMiniLabels.checked));

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
if (btnObsMode) btnObsMode.addEventListener('click', () => document.body.classList.add('obs-mode'));
if (btnExitObs) btnExitObs.addEventListener('click', () => document.body.classList.remove('obs-mode'));

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

window.__GAME_DEBUG__ = {
  getDiagnostics: () => engine.getDiagnostics(),
  getState: () => ({
    roundNumber: state.roundNumber,
    phase: state.phase,
    wave: state.wave,
    humanBaseHp: state.humanBaseHp,
    goalDefend: state.goalDefend,
    goalSabotage: state.goalSabotage,
    sessionCoins: state.sessionCoins,
  }),
};

(async () => {
  try {
    await engine.initEnvironment();
    await startNewRound();
    if (startAuto && btnAutoLive) {
      mockStream.start(selAutoIntensity ? selAutoIntensity.value : 'medium');
      btnAutoLive.textContent = '🤖 Auto-Live Ramai: ON';
      btnAutoLive.classList.add('active-auto');
    }
    if (wsParam) bus.connectWebSocket(wsParam);
  } catch (err) {
    console.error('Boot error:', err);
    addChatLine('❌ ERROR', 'Gagal memuat aset 3D. Pastikan dijalankan via HTTP server!', 'alert-sab');
  }
})();
