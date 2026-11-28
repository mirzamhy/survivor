// Standardized LiveEventBus (Mock + WebSocket Bridge ready) & Reactive MockTikTokStream

import { GIFT_CATALOG, MOCK_USERS, MOCK_CHAT_POOL } from './catalog.js';

export class LiveEventBus {
  constructor() {
    this.handlers = {
      gift: [],
      chat: [],
      like: [],
      follow: [],
      status: [],
    };
    this.queue = [];
    this.comboWindowMs = 3500;
    this.comboState = new Map(); // key: `${user}::${giftId}` -> { count, lastTs }
    this.ws = null;
    this.status = 'SIMULASI';
    this.dispatchCooldownMs = 70;
    this.lastDispatchTs = 0;
  }

  on(eventType, fn) {
    if (this.handlers[eventType]) {
      this.handlers[eventType].push(fn);
    }
    return () => {
      if (this.handlers[eventType]) {
        this.handlers[eventType] = this.handlers[eventType].filter((h) => h !== fn);
      }
    };
  }

  _emit(eventType, payload) {
    const list = this.handlers[eventType] || [];
    for (const fn of list) {
      try {
        fn(payload);
      } catch (err) {
        console.error(`[LiveEventBus] handler error for ${eventType}:`, err);
      }
    }
  }

  setStatus(newStatus) {
    this.status = newStatus;
    this._emit('status', { status: newStatus });
  }

  cleanUsername(raw) {
    const clean = String(raw || 'Penonton').trim().replace(/^@+/, '').slice(0, 20);
    return clean || 'Penonton';
  }

  emitGift({ user, giftId, repeatCount = 1, source = 'mock' }) {
    const gMeta = GIFT_CATALOG[giftId];
    if (!gMeta) return null;

    const cleanUser = this.cleanUsername(user);
    const rep = Math.max(1, Math.min(99, Math.floor(Number(repeatCount) || 1)));
    const now = Date.now();

    // Update 3.5s combo aggregator
    const comboKey = `${cleanUser}::${giftId}`;
    const prev = this.comboState.get(comboKey);
    let comboCount = rep;
    if (prev && now - prev.lastTs <= this.comboWindowMs) {
      comboCount = prev.count + rep;
    }
    this.comboState.set(comboKey, { count: comboCount, lastTs: now });

    // Prune stale combos occasionally
    if (this.comboState.size > 120) {
      for (const [k, v] of this.comboState.entries()) {
        if (now - v.lastTs > this.comboWindowMs * 2) this.comboState.delete(k);
      }
    }

    const evt = {
      type: 'gift',
      user: cleanUser,
      giftId,
      repeatCount: rep,
      coins: gMeta.coins * rep,
      comboCount,
      source,
      timestamp: now,
      priority: gMeta.coins >= 500 ? 3 : (gMeta.coins >= 30 ? 2 : 1),
    };

    // High-tier gifts jump to the front ahead of micro-gift backlog
    if (this.queue.length > 60 && evt.priority === 1) {
      // Collapse with last micro-gift of same id/user so no coin credit is ever dropped
      const existing = this.queue.find((q) => q.giftId === evt.giftId && q.user === evt.user);
      if (existing) {
        existing.repeatCount += evt.repeatCount;
        existing.coins += evt.coins;
        existing.comboCount = evt.comboCount;
        return evt;
      }
    }

    this.queue.push(evt);
    this.queue.sort((a, b) => b.priority - a.priority || a.timestamp - b.timestamp);
    return evt;
  }

  emitChat({ user, message, source = 'mock' }) {
    const cleanUser = this.cleanUsername(user);
    const msg = String(message || '').trim().slice(0, 140);
    if (!msg) return null;
    const evt = {
      type: 'chat',
      user: cleanUser,
      message: msg,
      source,
      timestamp: Date.now(),
    };
    this._emit('chat', evt);
    return evt;
  }

  emitLike({ user, count = 15, source = 'mock' }) {
    const evt = {
      type: 'like',
      user: this.cleanUsername(user),
      count: Math.max(1, Math.floor(Number(count) || 1)),
      source,
      timestamp: Date.now(),
    };
    this._emit('like', evt);
    return evt;
  }

  emitFollow({ user, source = 'mock' }) {
    const evt = {
      type: 'follow',
      user: this.cleanUsername(user),
      source,
      timestamp: Date.now(),
    };
    this._emit('follow', evt);
    return evt;
  }

  // Pump priority-queued gift events without stalling main loop
  pump(maxPerTick = 2) {
    const now = Date.now();
    if (this.queue.length === 0) return;
    if (now - this.lastDispatchTs < this.dispatchCooldownMs && this.queue[0].priority < 3) {
      return;
    }
    let processed = 0;
    while (this.queue.length > 0 && processed < maxPerTick) {
      const next = this.queue.shift();
      this._emit('gift', next);
      processed++;
      this.lastDispatchTs = now;
    }
  }

  clearQueue() {
    this.queue.length = 0;
  }

  // Ready for Phase 2 Node.js tiktok-live-connector WebSocket bridge
  connectWebSocket(url = 'ws://127.0.0.1:8787') {
    this.disconnectWebSocket();
    try {
      this.setStatus('MENYAMBUNG...');
      const ws = new WebSocket(url);
      this.ws = ws;
      ws.addEventListener('open', () => {
        if (this.ws === ws) this.setStatus('LIVE TERHUBUNG');
      });
      ws.addEventListener('message', (msgEvt) => {
        try {
          const data = JSON.parse(msgEvt.data);
          if (!data || !data.type) return;
          if (data.type === 'gift') {
            this.emitGift({
              user: data.user,
              giftId: data.giftId,
              repeatCount: data.repeatCount || 1,
              source: 'tiktok',
            });
          } else if (data.type === 'chat') {
            this.emitChat({ user: data.user, message: data.message, source: 'tiktok' });
          } else if (data.type === 'like') {
            this.emitLike({ user: data.user, count: data.count || 10, source: 'tiktok' });
          } else if (data.type === 'follow') {
            this.emitFollow({ user: data.user, source: 'tiktok' });
          }
        } catch {
          // Ignore malformed bridge packet
        }
      });
      ws.addEventListener('close', () => {
        if (this.ws === ws) {
          this.ws = null;
          this.setStatus('SIMULASI');
        }
      });
      ws.addEventListener('error', () => {
        if (this.ws === ws) {
          ws.close();
        }
      });
    } catch {
      this.setStatus('SIMULASI');
    }
  }

  disconnectWebSocket() {
    if (this.ws) {
      try {
        this.ws.close();
      } catch {
        // ignore
      }
      this.ws = null;
    }
    this.setStatus('SIMULASI');
  }
}

export class MockTikTokStream {
  constructor(eventBus, getContextState, onScenarioTrigger = null) {
    this.bus = eventBus;
    this.getContextState = getContextState;
    this.onScenarioTrigger = onScenarioTrigger;
    this.running = false;
    this.intensity = 'medium'; // 'low' | 'medium' | 'viral'
    this.timer = null;
    this.scenarioTimers = [];
  }

  _pickUser() {
    return MOCK_USERS[Math.floor(Math.random() * MOCK_USERS.length)];
  }

  setIntensity(val) {
    if (val === 'low' || val === 'medium' || val === 'viral') {
      this.intensity = val;
    }
  }

  start(intensity = null) {
    if (intensity) this.setIntensity(intensity);
    if (this.running) return;
    this.running = true;
    this._scheduleNext();
  }

  stop() {
    this.running = false;
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    this.clearScenarioTimers();
  }

  clearScenarioTimers() {
    for (const id of this.scenarioTimers) clearTimeout(id);
    this.scenarioTimers.length = 0;
  }

  _scheduleNext() {
    if (!this.running) return;
    const baseMs = this.intensity === 'viral' ? 680 : (this.intensity === 'medium' ? 1450 : 2500);
    const jitter = Math.random() * baseMs * 0.75;
    this.timer = setTimeout(() => {
      if (!this.running) return;
      this._step();
      this._scheduleNext();
    }, baseMs + jitter);
  }

  _step() {
    const st = (this.getContextState && this.getContextState()) || {};
    if (st.phase === 'ENDED') return;

    const user = this._pickUser();
    const r = Math.random();

    // 45% realistic reactive chat or command
    if (r < 0.44) {
      if (st.humanBaseRatio !== undefined && st.humanBaseRatio < 0.34 && Math.random() < 0.55) {
        const line = MOCK_CHAT_POOL.criticalHuman[Math.floor(Math.random() * MOCK_CHAT_POOL.criticalHuman.length)];
        this.bus.emitChat({ user, message: line });
        return;
      }
      if (st.bossAlive && Math.random() < 0.55) {
        const line = MOCK_CHAT_POOL.boss[Math.floor(Math.random() * MOCK_CHAT_POOL.boss.length)];
        this.bus.emitChat({ user, message: line });
        return;
      }
      if (Math.random() < 0.36) {
        const pool = MOCK_CHAT_POOL.idle;
        const pick = pool[Math.floor(Math.random() * pool.length)];
        this.bus.emitChat({ user, message: pick.msg });
      } else {
        const sidePool = Math.random() < 0.5 ? MOCK_CHAT_POOL.defend : MOCK_CHAT_POOL.sabotage;
        this.bus.emitChat({ user, message: sidePool[Math.floor(Math.random() * sidePool.length)] });
      }
      return;
    }

    // 20% tap-tap likes burst
    if (r < 0.64) {
      this.bus.emitLike({ user, count: 15 + Math.floor(Math.random() * 25) });
      return;
    }

    // 36% weighted Save vs Sabotage gift event (rubber-banded to Fortress Defense drama)
    const humanLow = st.humanBaseRatio !== undefined && st.humanBaseRatio < 0.35;
    let defendBias = st.bossAlive ? 0.58 : (st.finalWave ? 0.54 : 0.48);
    if (humanLow) defendBias = 0.68;
    const isDefend = Math.random() < defendBias;
    const roll = Math.random();

    if (isDefend) {
      if (roll < 0.46) {
        this.bus.emitGift({ user, giftId: 'rose', repeatCount: 1 + (Math.random() < 0.3 ? 2 : 0) });
      } else if (roll < 0.72) {
        this.bus.emitGift({ user, giftId: 'finger_heart', repeatCount: 1 });
      } else if (roll < 0.90) {
        this.bus.emitGift({ user, giftId: 'doughnut', repeatCount: 1 });
      } else if (roll < 0.98) {
        this.bus.emitGift({ user, giftId: 'corgi_supply', repeatCount: 1 });
      } else {
        this.bus.emitGift({ user, giftId: 'money_gun', repeatCount: 1 });
      }
    } else {
      if (roll < 0.46) {
        this.bus.emitGift({ user, giftId: 'ice_cream', repeatCount: 1 + (Math.random() < 0.3 ? 2 : 0) });
      } else if (roll < 0.72) {
        this.bus.emitGift({ user, giftId: 'gg_troll', repeatCount: 1 });
      } else if (roll < 0.90) {
        this.bus.emitGift({ user, giftId: 'cap_horde', repeatCount: 1 });
      } else if (roll < 0.98) {
        this.bus.emitGift({ user, giftId: 'storm_curse', repeatCount: 1 });
      } else {
        this.bus.emitGift({ user, giftId: 'galaxy_boss', repeatCount: 1 });
      }
    }
  }

  runScenario(id) {
    this.clearScenarioTimers();
    const after = (ms, fn) => {
      const t = setTimeout(fn, ms);
      this.scenarioTimers.push(t);
    };

    if (id === 'rose_war') {
      this.bus.emitChat({ user: 'SultanJakarta', message: 'GAS WAR ROSE VS ICE CREAM!!' });
      for (let i = 0; i < 6; i++) {
        after(i * 380, () => {
          this.bus.emitGift({ user: i % 2 === 0 ? 'MbakYanti_Live' : 'NengCici', giftId: 'rose', repeatCount: 2 });
        });
        after(i * 380 + 190, () => {
          this.bus.emitGift({ user: i % 2 === 0 ? 'RajaTroll_ID' : 'BocilGift', giftId: 'ice_cream', repeatCount: 2 });
        });
      }
      after(2600, () => {
        this.bus.emitGift({ user: 'BangJago99', giftId: 'doughnut', repeatCount: 1 });
      });
    } else if (id === 'boss_invasion') {
      this.bus.emitChat({ user: 'RajaTroll_ID', message: 'PANGGIL BADAI + GIANT BOSS SEKARANG!!' });
      this.bus.emitGift({ user: 'RajaTroll_ID', giftId: 'storm_curse', repeatCount: 1 });
      after(900, () => {
        this.bus.emitGift({ user: 'KomandanX', giftId: 'galaxy_boss', repeatCount: 1 });
      });
      after(2000, () => {
        this.bus.emitChat({ user: 'WibuSakti', message: 'GEDE BANGET BOSSNYA TOLONG!!' });
      });
    } else if (id === 'critical_comeback') {
      if (this.onScenarioTrigger) this.onScenarioTrigger('drop_barricade_critical');
      this.bus.emitChat({ user: 'BosMuda_Sby', message: 'MARKAS MERAH!! KIRIM SUPPLY & AIRSTRIKE!' });
      after(800, () => {
        this.bus.emitGift({ user: 'BosMuda_Sby', giftId: 'corgi_supply', repeatCount: 1 });
      });
      after(2300, () => {
        this.bus.emitGift({ user: 'SultanJakarta', giftId: 'money_gun', repeatCount: 1 });
      });
    } else if (id === 'sultan_clash') {
      this.bus.emitChat({ user: 'SultanJakarta', message: 'SULTAN SHOWTIME!' });
      this.bus.emitGift({ user: 'SultanJakarta', giftId: 'doughnut', repeatCount: 1 });
      after(700, () => {
        this.bus.emitGift({ user: 'TuanMuda77', giftId: 'galaxy_boss', repeatCount: 1 });
      });
      after(2200, () => {
        this.bus.emitGift({ user: 'SultanJakarta', giftId: 'money_gun', repeatCount: 1 });
      });
    }
  }
}
