// Procedural Web Audio SFX + TikTok Live Dopamine Audio Engine (zero external files)

export function createAudioEngine() {
  let ctx = null;
  let masterGain = null;
  let noiseBuf = null;
  let enabled = true;

  function ensure() {
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      ctx = new AC();
      masterGain = ctx.createGain();
      masterGain.gain.value = 0.28;
      masterGain.connect(ctx.destination);

      const len = Math.floor(ctx.sampleRate * 0.45);
      noiseBuf = ctx.createBuffer(1, len, ctx.sampleRate);
      const data = noiseBuf.getChannelData(0);
      for (let i = 0; i < len; i++) {
        data[i] = Math.random() * 2.0 - 1.0;
      }
    }
    return ctx;
  }

  function unlock() {
    try {
      const c = ensure();
      if (c && c.state === 'suspended') {
        c.resume().catch(() => {});
      }
    } catch {
      // Ignore autoplay restriction errors before user gesture
    }
  }

  window.addEventListener('pointerdown', unlock, { passive: true });
  window.addEventListener('keydown', unlock, { passive: true });

  function activeCtx() {
    if (!enabled) return null;
    try {
      const c = ensure();
      if (!c || c.state !== 'running') return null;
      return c;
    } catch {
      return null;
    }
  }

  function playNoise(c, t, dur, filterType, freqStart, freqEnd, q, gainPeak) {
    if (!noiseBuf) return;
    const src = c.createBufferSource();
    src.buffer = noiseBuf;
    const flt = c.createBiquadFilter();
    flt.type = filterType;
    flt.Q.value = q;
    flt.frequency.setValueAtTime(Math.max(40, freqStart), t);
    if (freqEnd !== freqStart) {
      flt.frequency.exponentialRampToValueAtTime(Math.max(30, freqEnd), t + dur);
    }
    const g = c.createGain();
    g.gain.setValueAtTime(Math.max(0.0001, gainPeak), t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    src.connect(flt).connect(g).connect(masterGain);
    src.start(t);
    src.stop(t + dur + 0.02);
  }

  function playTone(c, t, dur, type, freqStart, freqEnd, gainPeak) {
    const osc = c.createOscillator();
    osc.type = type;
    osc.frequency.setValueAtTime(Math.max(24, freqStart), t);
    if (freqEnd !== freqStart) {
      osc.frequency.exponentialRampToValueAtTime(Math.max(24, freqEnd), t + dur);
    }
    const g = c.createGain();
    g.gain.setValueAtTime(Math.max(0.0001, gainPeak), t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    osc.connect(g).connect(masterGain);
    osc.start(t);
    osc.stop(t + dur + 0.02);
  }

  return {
    setEnabled(val) {
      enabled = Boolean(val);
      if (enabled) unlock();
    },
    isEnabled() {
      return enabled;
    },
    isUnlocked() {
      return Boolean(ctx && ctx.state === 'running');
    },
    unlock,

    playGun(cls) {
      const c = activeCtx();
      if (!c) return;
      const t = c.currentTime;
      if (cls === 'bow') {
        playTone(c, t, 0.09, 'triangle', 320, 145, 0.22);
        playNoise(c, t, 0.06, 'highpass', 2400, 1600, 1.0, 0.12);
      } else if (cls === 'shotgun') {
        playNoise(c, t, 0.15, 'bandpass', 960, 310, 0.7, 0.44);
        playTone(c, t, 0.15, 'sine', 135, 36, 0.42);
      } else if (cls === 'pistol') {
        playNoise(c, t, 0.075, 'bandpass', 1550, 620, 0.9, 0.30);
        playTone(c, t, 0.065, 'sine', 180, 58, 0.22);
      } else {
        playNoise(c, t, 0.07, 'bandpass', 1750, 680, 0.85, 0.28);
        playTone(c, t, 0.06, 'sine', 160, 52, 0.20);
      }
    },

    playMelee(heavy) {
      const c = activeCtx();
      if (!c) return;
      const t = c.currentTime;
      playNoise(c, t, heavy ? 0.15 : 0.09, 'bandpass', heavy ? 520 : 880, heavy ? 170 : 300, 1.8, heavy ? 0.30 : 0.20);
    },

    playHit(heavy, isMutant) {
      const c = activeCtx();
      if (!c) return;
      const t = c.currentTime;
      playTone(c, t, heavy ? 0.09 : 0.06, 'triangle', isMutant ? 115 : 155, isMutant ? 42 : 58, heavy ? 0.24 : 0.14);
    },

    playMonsterAttack(isSlam) {
      const c = activeCtx();
      if (!c) return;
      const t = c.currentTime;
      if (isSlam) {
        playTone(c, t, 0.22, 'sine', 108, 32, 0.45);
        playNoise(c, t, 0.18, 'lowpass', 360, 110, 0.9, 0.32);
      } else {
        playNoise(c, t, 0.10, 'bandpass', 620, 220, 1.4, 0.20);
      }
    },

    playDeathThud(shakeStrength) {
      const c = activeCtx();
      if (!c) return;
      const t = c.currentTime;
      const w = Math.min(1.0, Math.max(0.26, (shakeStrength || 0.06) / 0.24));
      playTone(c, t, 0.22, 'sine', 95, 30, 0.42 * w);
      playNoise(c, t, 0.16, 'lowpass', 260, 90, 0.8, 0.26 * w);
    },

    playCoinChime(comboCount = 1, faction = 'defend') {
      const c = activeCtx();
      if (!c) return;
      const t = c.currentTime;
      const step = Math.min(14, Math.max(0, comboCount - 1));
      const baseFreq = faction === 'defend' ? 587.33 : 440.0; // D5 or A4
      const freq = baseFreq * Math.pow(2, step / 12);
      if (faction === 'defend') {
        playTone(c, t, 0.14, 'triangle', freq, freq * 1.02, 0.34);
        playTone(c, t + 0.045, 0.18, 'sine', freq * 1.5, freq * 1.5, 0.22);
      } else {
        playTone(c, t, 0.14, 'sawtooth', freq, freq * 0.84, 0.20);
        playTone(c, t + 0.04, 0.16, 'square', freq * 0.75, freq * 0.65, 0.14);
      }
    },

    playUpgradeFanfare() {
      const c = activeCtx();
      if (!c) return;
      const t = c.currentTime;
      const notes = [523.25, 659.25, 783.99, 1046.5];
      notes.forEach((f, i) => {
        playTone(c, t + i * 0.065, 0.24, 'triangle', f, f * 1.01, 0.28);
      });
    },

    playHealPulse() {
      const c = activeCtx();
      if (!c) return;
      const t = c.currentTime;
      playTone(c, t, 0.32, 'sine', 440, 660, 0.24);
      playTone(c, t + 0.06, 0.36, 'sine', 554.37, 880, 0.22);
    },

    playAirstrike() {
      const c = activeCtx();
      if (!c) return;
      const t = c.currentTime;
      // Incoming whistle
      playTone(c, t, 0.38, 'sine', 1350, 260, 0.26);
      // Staggered explosions
      for (let i = 0; i < 4; i++) {
        const dt = 0.26 + i * 0.16;
        playTone(c, t + dt, 0.35, 'sine', 120, 28, 0.55);
        playNoise(c, t + dt, 0.40, 'lowpass', 720, 120, 0.7, 0.50);
      }
    },

    playBossHorn() {
      const c = activeCtx();
      if (!c) return;
      const t = c.currentTime;
      playTone(c, t, 0.65, 'sawtooth', 82.4, 65.4, 0.34);
      playTone(c, t + 0.04, 0.65, 'triangle', 123.5, 98.0, 0.26);
      playNoise(c, t + 0.10, 0.45, 'lowpass', 420, 140, 0.8, 0.24);
    },

    playEmergencyBeep() {
      const c = activeCtx();
      if (!c) return;
      const t = c.currentTime;
      playTone(c, t, 0.11, 'square', 880, 820, 0.12);
    },

    playRoundEnd(victory) {
      const c = activeCtx();
      if (!c) return;
      const t = c.currentTime;
      const seq = victory
        ? [523.25, 659.25, 783.99, 1046.5]
        : [293.66, 261.63, 220.0, 146.83];
      seq.forEach((f, i) => {
        playTone(c, t + i * 0.12, 0.32, victory ? 'triangle' : 'sawtooth', f, f, 0.28);
      });
    },
  };
}
