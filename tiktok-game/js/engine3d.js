// 9:16 Three.js Combat Arena Engine — PBR Assets, Dynamic Weapon Upgrades, Barricade & Gift VFX

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import * as SkeletonUtils from 'three/addons/utils/SkeletonUtils.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import {
  ASSET_VER,
  ENV_PATHS,
  VFX_PATHS,
  SURVIVORS,
  WEAPONS,
  ZOMBIES,
  MUTANT_BOSSES,
  getTierMeta,
} from './catalog.js';

const WEATHER_PRESETS = {
  apoc_sunset: {
    label: 'Sore Senja Emas',
    topColor: 0x2c4266, midColor: 0x9c5c46, horizonColor: 0xd48e61, groundColor: 0x4f382b,
    sunColor: 0xffc778, sunDir: [-0.66, 0.24, -0.71], sunSize: 0.062,
    cloudColor: 0xc27756, cloudIntensity: 0.48,
    fogColor: 0xd48e61, fogDensity: 0.0110,
    hemiSky: 0xebc3a4, hemiGround: 0x594234, hemiInt: 1.24,
    keyColor: 0xffd2a6, keyPos: [-20, 14, 16], keyInt: 2.65,
    rimColor: 0x99c2ff, rimPos: [16, 13, -12], rimInt: 1.35,
    fireInt: 5.4, fireHaloAlpha: 0.48, lampAlpha: 0.16, coneAlpha: 0.08,
    exposure: 1.12, envInt: 1.00,
    asphaltRough: 0.78, asphaltEnv: 0.60, puddleRough: 0.05, puddleEnv: 2.00,
    rain: false, lightning: false, mistAlpha: 0.56,
    particleMode: 'ash_embers', particleCount: 95, particleColor: 0xffae5c, particleSize: 0.13,
  },
  apoc_morning: {
    label: 'Pagi Berkabut',
    topColor: 0x5d82a8, midColor: 0x9ab4c9, horizonColor: 0xc8c5bc, groundColor: 0x6b6052,
    sunColor: 0xfff3d6, sunDir: [-0.45, 0.44, 0.77], sunSize: 0.045,
    cloudColor: 0xe6eaef, cloudIntensity: 0.42,
    fogColor: 0xc8c5bc, fogDensity: 0.0105,
    hemiSky: 0xeaf2fa, hemiGround: 0x7d6e5d, hemiInt: 1.48,
    keyColor: 0xfff5e4, keyPos: [-14, 22, 16], keyInt: 2.55,
    rimColor: 0xb8d8ff, rimPos: [16, 14, -12], rimInt: 1.25,
    fireInt: 2.6, fireHaloAlpha: 0.28, lampAlpha: 0.0, coneAlpha: 0.0,
    exposure: 1.12, envInt: 1.05,
    asphaltRough: 0.80, asphaltEnv: 0.55, puddleRough: 0.05, puddleEnv: 1.80,
    rain: false, lightning: false, mistAlpha: 0.52,
    particleMode: 'ash_embers', particleCount: 65, particleColor: 0xffe4b8, particleSize: 0.11,
  },
  apoc_noon: {
    label: 'Siang Cerah',
    topColor: 0x3b72b5, midColor: 0x82accf, horizonColor: 0xd2cbbd, groundColor: 0x7a6c5a,
    sunColor: 0xfff8e6, sunDir: [-0.36, 0.62, 0.69], sunSize: 0.042,
    cloudColor: 0xf4f6f8, cloudIntensity: 0.36,
    fogColor: 0xd2cbbd, fogDensity: 0.0085,
    hemiSky: 0xf4f8fc, hemiGround: 0x8a7965, hemiInt: 1.62,
    keyColor: 0xfff8ed, keyPos: [-12, 28, 15], keyInt: 2.90,
    rimColor: 0xd6e8ff, rimPos: [16, 16, -12], rimInt: 1.15,
    fireInt: 2.0, fireHaloAlpha: 0.22, lampAlpha: 0.0, coneAlpha: 0.0,
    exposure: 1.14, envInt: 1.10,
    asphaltRough: 0.84, asphaltEnv: 0.50, puddleRough: 0.05, puddleEnv: 1.75,
    rain: false, lightning: false, mistAlpha: 0.34,
    particleMode: 'ash_embers', particleCount: 50, particleColor: 0xf5ead8, particleSize: 0.10,
  },
  apoc_overcast: {
    label: 'Mendung Berkabut',
    topColor: 0x606e7e, midColor: 0x8a99a8, horizonColor: 0xb2bcc4, groundColor: 0x52575e,
    sunColor: 0xeaf0f5, sunDir: [-0.35, 0.45, 0.82], sunSize: 0.050,
    cloudColor: 0xc2ccd6, cloudIntensity: 0.56,
    fogColor: 0xb2bcc4, fogDensity: 0.0150,
    hemiSky: 0xdde6ee, hemiGround: 0x5c626b, hemiInt: 1.68,
    keyColor: 0xf5f8fb, keyPos: [-11, 24, 15], keyInt: 1.90,
    rimColor: 0xc4e2f8, rimPos: [15, 14, -12], rimInt: 1.15,
    fireInt: 3.6, fireHaloAlpha: 0.36, lampAlpha: 0.0, coneAlpha: 0.0,
    exposure: 1.10, envInt: 1.00,
    asphaltRough: 0.82, asphaltEnv: 0.52, puddleRough: 0.05, puddleEnv: 1.85,
    rain: false, lightning: false, mistAlpha: 0.72,
    particleMode: 'ash_embers', particleCount: 110, particleColor: 0xdbe2ea, particleSize: 0.12,
  },
  storm_rain: {
    label: 'Badai Hujan & Petir',
    topColor: 0x2a3748, midColor: 0x465769, horizonColor: 0x69798b, groundColor: 0x303740,
    sunColor: 0xd6e6ff, sunDir: [-0.42, 0.36, 0.83], sunSize: 0.038,
    cloudColor: 0x6e7e90, cloudIntensity: 0.62,
    fogColor: 0x69798b, fogDensity: 0.0145,
    hemiSky: 0xbad0e6, hemiGround: 0x3b444e, hemiInt: 1.32,
    keyColor: 0xe2ecff, keyPos: [-12, 22, 15], keyInt: 1.85,
    rimColor: 0xa8d4ff, rimPos: [15, 13, -12], rimInt: 1.48,
    fireInt: 6.0, fireHaloAlpha: 0.52, lampAlpha: 0.22, coneAlpha: 0.10,
    exposure: 1.10, envInt: 1.05,
    asphaltRough: 0.45, asphaltEnv: 1.08, puddleRough: 0.04, puddleEnv: 2.20,
    rain: true, lightning: true, mistAlpha: 0.70,
    particleMode: 'embers', particleCount: 65, particleColor: 0xff9a44, particleSize: 0.14,
  },
};

const DEATH_THEMES = {
  mutant_bile_juggernaut: { colors: [0xa3e635, 0x84cc16, 0x65a30d, 0x7f1d1d], poolColor: 0x3f6212, poolRad: 1.80, count: 24, impactDelay: 0.66, shake: 0.22, dustScale: 2.1, dustColor: 0xa3b18a },
  mutant_rafflesia:       { colors: [0xdc2626, 0x991b1b, 0x84cc16, 0x4d7c0f], poolColor: 0x4c0519, poolRad: 1.45, count: 20, impactDelay: 0.58, shake: 0.12, dustScale: 1.5, dustColor: 0xb59e8c },
  mutant_thorn_shroud:    { colors: [0xe2e8f0, 0x93c5fd, 0xcbd5e1, 0x475569], poolColor: 0x1e293b, poolRad: 1.20, count: 20, impactDelay: 0.56, shake: 0.10, dustScale: 1.4, dustColor: 0xcbd5e1 },
  mutant_scythe_stalker:  { colors: [0x991b1b, 0x450a0a, 0xd6d3d1],           poolColor: 0x3b0a0a, poolRad: 1.25, count: 18, impactDelay: 0.54, shake: 0.09, dustScale: 1.4, dustColor: 0xa8a29e },
  mutant_arachnid_maw:    { colors: [0xa6f214, 0x65a30d, 0x1e293b],           poolColor: 0x365314, poolRad: 1.35, count: 20, impactDelay: 0.50, shake: 0.10, dustScale: 1.5, dustColor: 0x9ca3af },
  zombie_bloater_boomer:  { colors: [0xa3e635, 0x84cc16, 0x7f1d1d],           poolColor: 0x3f6212, poolRad: 1.15, count: 20, impactDelay: 0.56, shake: 0.14, dustScale: 1.4, dustColor: 0xa3b18a },
  zombie_spitter_hazmat:  { colors: [0x84cc16, 0x991b1b, 0x4d7c0f],           poolColor: 0x365314, poolRad: 0.95, count: 14, impactDelay: 0.52, shake: 0.05, dustScale: 1.1, dustColor: 0x9ca3af },
  zombie_juggernaut_brute:{ colors: [0xb91c1c, 0x7f1d1d, 0x334155],           poolColor: 0x3b0a0a, poolRad: 1.20, count: 18, impactDelay: 0.60, shake: 0.14, dustScale: 1.4, dustColor: 0x9ca3af },
  _default:               { colors: [0xb91c1c, 0x7f1d1d, 0x450a0a],           poolColor: 0x3b0a0a, poolRad: 0.85, count: 14, impactDelay: 0.52, shake: 0.04, dustScale: 1.0, dustColor: 0x9ca3af },
};

const MAX_DEATH_PUDDLES = 32;
const BARRICADE_X = -5.0;
const ENEMY_STOP_X = -4.25;

export function createArenaEngine(stageWrap, labelsLayer, audio, callbacks = {}) {
  const getStageSize = () => ({
    w: Math.max(240, stageWrap.clientWidth || 405),
    h: Math.max(360, stageWrap.clientHeight || 720),
  });

  const { w: initW, h: initH } = getStageSize();

  const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.45));
  renderer.setSize(initW, initH, false);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.12;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  stageWrap.insertBefore(renderer.domElement, stageWrap.firstChild);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xd48e61);
  scene.fog = new THREE.FogExp2(0xd48e61, 0.0110);

  // Vertical 54deg FOV frames both Barricade (x=-5.0) & Enemy Lane (x=+5.5) cleanly in 9:16
  const camera = new THREE.PerspectiveCamera(54, initW / initH, 0.1, 280);
  camera.position.set(-0.7, 9.0, 21.4);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.target.set(-0.55, 1.05, -0.35);
  controls.maxPolarAngle = Math.PI * 0.485;
  controls.minDistance = 4.0;
  controls.maxDistance = 44.0;

  let manualOrbitPause = 0.0;
  controls.addEventListener('start', () => {
    manualOrbitPause = 4.5;
  });

  // Lighting rig
  const hemi = new THREE.HemisphereLight(0xebc3a4, 0x594234, 1.24);
  scene.add(hemi);

  const keyLight = new THREE.DirectionalLight(0xffd2a6, 2.65);
  keyLight.position.set(-20, 14, 16);
  keyLight.castShadow = true;
  keyLight.shadow.mapSize.set(2048, 2048);
  keyLight.shadow.camera.near = 1;
  keyLight.shadow.camera.far = 58;
  keyLight.shadow.camera.left = -18;
  keyLight.shadow.camera.right = 18;
  keyLight.shadow.camera.top = 14;
  keyLight.shadow.camera.bottom = -14;
  keyLight.shadow.bias = -0.00035;
  keyLight.shadow.normalBias = 0.028;
  scene.add(keyLight);

  const rimLight = new THREE.DirectionalLight(0x99c2ff, 1.35);
  rimLight.position.set(16, 13, -12);
  scene.add(rimLight);

  const combatFlashLight = new THREE.PointLight(0xffcf70, 0, 11.0, 1.6);
  scene.add(combatFlashLight);
  const combatFlash = { timer: 0, dur: 0.08, maxInt: 6.0 };

  function triggerFlashLight(pos, colorHex, intensity = 5.5, duration = 0.075) {
    if (!pos) return;
    combatFlashLight.position.copy(pos);
    combatFlashLight.color.setHex(colorHex);
    combatFlashLight.intensity = intensity;
    combatFlash.maxInt = intensity;
    combatFlash.dur = Math.max(0.03, duration);
    combatFlash.timer = combatFlash.dur;
  }

  const fireLightW = new THREE.PointLight(0xff7722, 5.4, 10.0, 1.6);
  fireLightW.position.set(-4.4, 1.45, -3.65);
  scene.add(fireLightW);

  const fireLightE = new THREE.PointLight(0xff7722, 5.4, 10.0, 1.6);
  fireLightE.position.set(4.6, 1.45, -3.75);
  scene.add(fireLightE);

  // HDR Selective Bloom pipeline
  const composerRT = new THREE.WebGLRenderTarget(initW, initH, {
    type: THREE.HalfFloatType,
    samples: renderer.capabilities.isWebGL2 ? 4 : 0,
  });
  const composer = new EffectComposer(renderer, composerRT);
  composer.setPixelRatio(renderer.getPixelRatio());
  composer.setSize(initW, initH);
  composer.addPass(new RenderPass(scene, camera));
  const bloomPass = new UnrealBloomPass(new THREE.Vector2(initW, initH), 0.24, 0.40, 1.08);
  composer.addPass(bloomPass);
  composer.addPass(new OutputPass());

  let bloomEnabled = true;

  function handleResize() {
    const { w, h } = getStageSize();
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h, false);
    composer.setSize(w, h);
    bloomPass.setSize(w, h);
  }

  const resizeObs = new ResizeObserver(() => handleResize());
  resizeObs.observe(stageWrap);
  window.addEventListener('resize', handleResize);

  // Procedural sky dome + linear PMREM IBL reflections
  const skyUniforms = {
    uTopColor: { value: new THREE.Color(0x2c4266) },
    uMidColor: { value: new THREE.Color(0x9c5c46) },
    uHorizonColor: { value: new THREE.Color(0xd48e61) },
    uGroundColor: { value: new THREE.Color(0x4f382b) },
    uSunColor: { value: new THREE.Color(0xffc778) },
    uSunDir: { value: new THREE.Vector3(-0.66, 0.24, -0.71).normalize() },
    uSunSize: { value: 0.062 },
    uCloudColor: { value: new THREE.Color(0xc27756) },
    uCloudIntensity: { value: 0.48 },
    uTime: { value: 0.0 },
    uFlash: { value: 0.0 },
  };

  const skyVertShader = /* glsl */`
    varying vec3 vWorldDir;
    void main() {
      vWorldDir = position;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `;

  const skyFragBody = /* glsl */`
    uniform vec3 uTopColor;
    uniform vec3 uMidColor;
    uniform vec3 uHorizonColor;
    uniform vec3 uGroundColor;
    uniform vec3 uSunColor;
    uniform vec3 uSunDir;
    uniform float uSunSize;
    uniform vec3 uCloudColor;
    uniform float uCloudIntensity;
    uniform float uTime;
    uniform float uFlash;
    varying vec3 vWorldDir;

    float hash21(vec2 p) {
      p = fract(p * vec2(123.34, 456.21));
      p += dot(p, p + 45.32);
      return fract(p.x * p.y);
    }
    float noise2(vec2 p) {
      vec2 i = floor(p);
      vec2 f = fract(p);
      f = f * f * (3.0 - 2.0 * f);
      float a = hash21(i);
      float b = hash21(i + vec2(1.0, 0.0));
      float c = hash21(i + vec2(0.0, 1.0));
      float d = hash21(i + vec2(1.0, 1.0));
      return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
    }

    void main() {
      vec3 dir = normalize(vWorldDir);
      float h = clamp(dir.y, -1.0, 1.0);
      vec3 col;
      if (h >= 0.0) {
        float tMid = smoothstep(0.0, 0.24, h);
        float tTop = smoothstep(0.18, 0.78, h);
        col = mix(uHorizonColor, uMidColor, tMid);
        col = mix(col, uTopColor, tTop);
      } else {
        col = mix(uHorizonColor, uGroundColor, smoothstep(0.0, -0.25, h));
      }

      float sunDot = max(dot(dir, normalize(uSunDir)), 0.0);
      float halo = pow(sunDot, 10.0) * 0.42 + pow(sunDot, 48.0) * 0.55;
      float disc = smoothstep(cos(uSunSize * 1.45), cos(uSunSize * 0.65), sunDot);
      if (h > -0.04) {
        float vis = smoothstep(-0.04, 0.06, h);
        col += uSunColor * (halo * 0.65 + disc * 1.15) * vis;
      }

      if (dir.y > 0.01 && uCloudIntensity > 0.01) {
        vec2 uv = dir.xz / (dir.y + 0.18);
        vec2 wind = vec2(uTime * 0.014, uTime * 0.005);
        float c1 = noise2(uv * 0.90 + wind);
        float c2 = noise2(uv * 2.10 - wind * 1.4 + vec2(4.2, 1.9));
        float cloudMask = smoothstep(0.46, 0.84, c1 * 0.65 + c2 * 0.35);
        float elevFade = smoothstep(0.01, 0.22, dir.y) * smoothstep(0.96, 0.30, dir.y);
        vec3 cloudCol = mix(uCloudColor, uSunColor * 0.92, pow(sunDot, 6.0) * 0.40);
        cloudCol += vec3(0.55, 0.72, 1.0) * uFlash * (0.45 + 0.55 * c2);
        col = mix(col, cloudCol, cloudMask * elevFade * uCloudIntensity);
      }

      col += vec3(0.28, 0.38, 0.56) * uFlash * smoothstep(-0.05, 0.45, dir.y);
      gl_FragColor = vec4(col, 1.0);
  `;

  const skyMat = new THREE.ShaderMaterial({
    uniforms: skyUniforms,
    side: THREE.BackSide,
    depthWrite: false,
    fog: false,
    vertexShader: skyVertShader,
    fragmentShader: skyFragBody + /* glsl */`
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
    }
    `,
  });

  const skyEnvMat = new THREE.ShaderMaterial({
    uniforms: skyUniforms,
    side: THREE.BackSide,
    depthWrite: false,
    fog: false,
    toneMapped: false,
    vertexShader: skyVertShader,
    fragmentShader: skyFragBody + /* glsl */`
    }
    `,
  });

  const skyDome = new THREE.Mesh(new THREE.SphereGeometry(210, 32, 20), skyEnvMat);
  skyDome.frustumCulled = false;
  scene.add(skyDome);

  function syncBloomSkyMaterial() {
    const targetMat = bloomEnabled ? skyEnvMat : skyMat;
    if (skyDome.material !== targetMat) {
      skyDome.material = targetMat;
    }
  }

  const pmremGen = new THREE.PMREMGenerator(renderer);
  const skyEnvScene = new THREE.Scene();
  skyEnvScene.add(new THREE.Mesh(new THREE.SphereGeometry(20, 24, 14), skyEnvMat));
  let currentEnvRT = null;

  // Shared procedural textures
  function makeRadialTex(innerRgba, midRgba, outerRgba, size = 128) {
    const c = document.createElement('canvas');
    c.width = size; c.height = size;
    const ctx = c.getContext('2d');
    const g = ctx.createRadialGradient(size / 2, size / 2, 1, size / 2, size / 2, size / 2);
    g.addColorStop(0.0, innerRgba);
    g.addColorStop(0.42, midRgba);
    g.addColorStop(1.0, outerRgba);
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, size, size);
    const tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    return tex;
  }

  function makeMistCloudTex(size = 192) {
    const c = document.createElement('canvas');
    c.width = size; c.height = size;
    const ctx = c.getContext('2d');
    const puffs = [
      [0.50, 0.52, 0.44, 0.24], [0.34, 0.48, 0.30, 0.22],
      [0.66, 0.50, 0.30, 0.20], [0.48, 0.38, 0.28, 0.18],
    ];
    for (const [px, py, pr, pa] of puffs) {
      const g = ctx.createRadialGradient(px * size, py * size, 2, px * size, py * size, pr * size);
      g.addColorStop(0.0, `rgba(215, 228, 245, ${pa})`);
      g.addColorStop(0.55, `rgba(185, 204, 224, ${pa * 0.42})`);
      g.addColorStop(1.0, 'rgba(185, 204, 224, 0.0)');
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, size, size);
    }
    const tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    return tex;
  }

  function makeConeGradTex(size = 128) {
    const c = document.createElement('canvas');
    c.width = 16; c.height = size;
    const ctx = c.getContext('2d');
    const g = ctx.createLinearGradient(0, 0, 0, size);
    g.addColorStop(0.0, 'rgba(255, 210, 140, 0.95)');
    g.addColorStop(0.28, 'rgba(255, 196, 120, 0.42)');
    g.addColorStop(1.0, 'rgba(255, 180, 100, 0.0)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, 16, size);
    const tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    return tex;
  }

  const softGlowTex = makeRadialTex('rgba(255,255,255,1)', 'rgba(255,255,255,0.45)', 'rgba(255,255,255,0)', 128);
  const contactShadowTex = makeRadialTex('rgba(6,9,14,0.72)', 'rgba(6,9,14,0.34)', 'rgba(6,9,14,0)', 128);
  const mistCloudTex = makeMistCloudTex(192);
  const coneGradTex = makeConeGradTex(128);

  const splatterTex = (() => {
    const c = document.createElement('canvas');
    c.width = 128; c.height = 128;
    const ctx = c.getContext('2d');
    const blobs = [
      [64, 64, 34], [46, 52, 20], [82, 58, 18], [58, 84, 21],
      [76, 44, 15], [38, 72, 13], [90, 78, 12], [66, 36, 11],
      [26, 54, 7], [98, 50, 6], [42, 98, 7], [88, 96, 6],
    ];
    for (const [bx, by, br] of blobs) {
      const g = ctx.createRadialGradient(bx, by, br * 0.15, bx, by, br);
      g.addColorStop(0, 'rgba(255,255,255,0.96)');
      g.addColorStop(0.68, 'rgba(255,255,255,0.82)');
      g.addColorStop(1, 'rgba(255,255,255,0.0)');
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(bx, by, br, 0, Math.PI * 2);
      ctx.fill();
    }
    const tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    return tex;
  })();

  // Atmosphere FX group
  const atmosphereGroup = new THREE.Group();
  scene.add(atmosphereGroup);

  const lampPoolGeo = new THREE.PlaneGeometry(4.8, 4.8);
  const lampPoolMatW = new THREE.MeshBasicMaterial({
    map: softGlowTex, color: 0xffc168, transparent: true, opacity: 0.16,
    blending: THREE.AdditiveBlending, depthWrite: false, fog: false,
  });
  const lampPoolMatE = lampPoolMatW.clone();
  const lampPoolW = new THREE.Mesh(lampPoolGeo, lampPoolMatW);
  lampPoolW.rotation.x = -Math.PI / 2;
  lampPoolW.position.set(-7.85, 0.011, -2.05);
  scene.add(lampPoolW);

  const lampPoolE = new THREE.Mesh(lampPoolGeo, lampPoolMatE);
  lampPoolE.rotation.x = -Math.PI / 2;
  lampPoolE.position.set(5.45, 0.011, -2.10);
  scene.add(lampPoolE);

  const coneGeo = new THREE.CylinderGeometry(0.14, 2.45, 4.95, 14, 1, true);
  const coneMatW = new THREE.MeshBasicMaterial({
    map: coneGradTex, color: 0xffc670, transparent: true, opacity: 0.08,
    blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide, fog: false,
  });
  const coneMatE = coneMatW.clone();
  const lampConeW = new THREE.Mesh(coneGeo, coneMatW);
  lampConeW.position.set(-7.85, 2.48, -2.55);
  lampConeW.rotation.x = 0.20;
  atmosphereGroup.add(lampConeW);

  const lampConeE = new THREE.Mesh(coneGeo, coneMatE);
  lampConeE.position.set(5.45, 2.48, -2.60);
  lampConeE.rotation.x = 0.20;
  atmosphereGroup.add(lampConeE);

  const fireHaloMatW = new THREE.SpriteMaterial({
    map: softGlowTex, color: 0xff7b1c, transparent: true, opacity: 0.48,
    blending: THREE.AdditiveBlending, depthWrite: false, fog: false,
  });
  const fireHaloMatE = fireHaloMatW.clone();
  const fireHaloW = new THREE.Sprite(fireHaloMatW);
  fireHaloW.position.set(-4.4, 1.18, -3.65);
  fireHaloW.scale.set(2.3, 2.3, 1);
  atmosphereGroup.add(fireHaloW);

  const fireHaloE = new THREE.Sprite(fireHaloMatE);
  fireHaloE.position.set(4.6, 1.18, -3.75);
  fireHaloE.scale.set(2.3, 2.3, 1);
  atmosphereGroup.add(fireHaloE);

  const policeHaloRed = new THREE.Sprite(new THREE.SpriteMaterial({
    map: softGlowTex, color: 0xff2820, transparent: true, opacity: 0.25,
    blending: THREE.AdditiveBlending, depthWrite: false, fog: false,
  }));
  policeHaloRed.position.set(8.72, 1.52, -3.96);
  policeHaloRed.scale.setScalar(1.65);
  atmosphereGroup.add(policeHaloRed);

  const policeHaloBlue = new THREE.Sprite(new THREE.SpriteMaterial({
    map: softGlowTex, color: 0x2688ff, transparent: true, opacity: 0.25,
    blending: THREE.AdditiveBlending, depthWrite: false, fog: false,
  }));
  policeHaloBlue.position.set(8.80, 1.52, -4.54);
  policeHaloBlue.scale.setScalar(1.65);
  atmosphereGroup.add(policeHaloBlue);

  // Smoke plumes
  const smokeEmitters = [
    { x: -4.4, y: 1.25, z: -3.65 },
    { x:  4.6, y: 1.25, z: -3.75 },
    { x: -6.8, y: 0.85, z: -4.20 },
  ];
  const SMOKE_COUNT = 16;
  const smokePos = new Float32Array(SMOKE_COUNT * 3);
  const smokeMeta = [];
  for (let i = 0; i < SMOKE_COUNT; i++) {
    const em = smokeEmitters[i % smokeEmitters.length];
    smokePos[i * 3 + 0] = em.x;
    smokePos[i * 3 + 1] = em.y + (i / SMOKE_COUNT) * 3.2;
    smokePos[i * 3 + 2] = em.z;
    smokeMeta.push({
      emitter: em,
      age: Math.random() * 4.0,
      maxAge: 3.4 + Math.random() * 1.4,
      vx: 0.20 + Math.random() * 0.22,
      vz: (Math.random() - 0.5) * 0.14,
    });
  }
  const smokeGeo = new THREE.BufferGeometry();
  smokeGeo.setAttribute('position', new THREE.BufferAttribute(smokePos, 3));
  const smokePoints = new THREE.Points(smokeGeo, new THREE.PointsMaterial({
    map: mistCloudTex, color: 0x8a929c, size: 1.9, transparent: true, opacity: 0.15,
    depthWrite: false, sizeAttenuation: true, fog: true,
  }));
  smokePoints.frustumCulled = false;
  atmosphereGroup.add(smokePoints);

  // Rain streaks
  const RAIN_COUNT = 380;
  const rainPos = new Float32Array(RAIN_COUNT * 6);
  const rainSeeds = new Float32Array(RAIN_COUNT * 3);
  for (let i = 0; i < RAIN_COUNT; i++) {
    const rx = (Math.random() - 0.5) * 38;
    const ry = Math.random() * 14;
    const rz = (Math.random() - 0.5) * 22;
    rainSeeds[i * 3 + 0] = rx; rainSeeds[i * 3 + 1] = ry; rainSeeds[i * 3 + 2] = rz;
    const i6 = i * 6;
    rainPos[i6 + 0] = rx; rainPos[i6 + 1] = ry; rainPos[i6 + 2] = rz;
    rainPos[i6 + 3] = rx - 0.10; rainPos[i6 + 4] = ry + 0.78; rainPos[i6 + 5] = rz - 0.03;
  }
  const rainGeo = new THREE.BufferGeometry();
  rainGeo.setAttribute('position', new THREE.BufferAttribute(rainPos, 3));
  const rainLines = new THREE.LineSegments(rainGeo, new THREE.LineBasicMaterial({
    color: 0xaec8e8, transparent: true, opacity: 0.36, depthWrite: false, fog: true,
  }));
  rainLines.frustumCulled = false;
  rainLines.visible = false;
  atmosphereGroup.add(rainLines);

  // Embers / Ash
  const PARTICLE_MAX = 140;
  const partPos = new Float32Array(PARTICLE_MAX * 3);
  const partMeta = [];
  for (let i = 0; i < PARTICLE_MAX; i++) {
    partPos[i * 3 + 0] = (Math.random() - 0.5) * 30;
    partPos[i * 3 + 1] = Math.random() * 6.0;
    partPos[i * 3 + 2] = -8 + Math.random() * 14;
    partMeta.push({ phase: Math.random() * 6.28, spdY: 0.35 + Math.random() * 1.0, spdX: 0.25 + Math.random() * 0.45, barrelIdx: i % 2 });
  }
  const partGeo = new THREE.BufferGeometry();
  partGeo.setAttribute('position', new THREE.BufferAttribute(partPos, 3));
  const partMat = new THREE.PointsMaterial({
    map: softGlowTex, color: 0xffae5c, size: 0.13, transparent: true, opacity: 0.84,
    blending: THREE.AdditiveBlending, depthWrite: false, sizeAttenuation: true,
  });
  const floatPoints = new THREE.Points(partGeo, partMat);
  floatPoints.frustumCulled = false;
  atmosphereGroup.add(floatPoints);

  // GLTF asset cache
  const loader = new GLTFLoader();
  const gltfCache = new Map();
  function loadGLB(url) {
    const fullUrl = url + ASSET_VER;
    if (!gltfCache.has(fullUrl)) {
      gltfCache.set(fullUrl, loader.loadAsync(fullUrl));
    }
    return gltfCache.get(fullUrl);
  }

  const unitRimUniforms = {
    uRimColor: { value: new THREE.Color(0x99c2ff) },
    uRimStrength: { value: 0.26 },
  };

  function applyUnitRimShader(mat) {
    if (!mat || !mat.isMeshStandardMaterial || mat.userData._hasRimShader) return;
    mat.userData._hasRimShader = true;
    mat.customProgramCacheKey = () => 'unit_fresnel_rim_v1';
    mat.onBeforeCompile = (shader) => {
      shader.uniforms.uRimColor = unitRimUniforms.uRimColor;
      shader.uniforms.uRimStrength = unitRimUniforms.uRimStrength;
      shader.fragmentShader = shader.fragmentShader
        .replace('#include <common>', '#include <common>\nuniform vec3 uRimColor;\nuniform float uRimStrength;')
        .replace(
          '#include <opaque_fragment>',
          `{
            float _rimNdotV = clamp(dot(normalize(normal), normalize(vViewPosition)), 0.0, 1.0);
            float _rimPow = pow(1.0 - _rimNdotV, 3.2) * uRimStrength;
            outgoingLight += uRimColor * _rimPow * (0.35 + 0.65 * diffuseColor.rgb);
          }
          #include <opaque_fragment>`
        );
    };
    mat.needsUpdate = true;
  }

  function prepShadows(root, envBoost = 1.25, isUnit = false) {
    root.traverse((o) => {
      if (o.isMesh || o.isSkinnedMesh) {
        o.castShadow = true;
        o.receiveShadow = true;
        o.frustumCulled = false;
        const mats = Array.isArray(o.material) ? o.material : [o.material];
        for (const mt of mats) {
          if (!mt) continue;
          if (isUnit) {
            applyUnitRimShader(mt);
            if (!mt.map && mt.isMeshStandardMaterial && !mt.userData._roughCohesed) {
              mt.userData._roughCohesed = true;
              mt.roughness = THREE.MathUtils.clamp(mt.roughness, 0.46, 0.88);
            }
          }
          if ('envMapIntensity' in mt) {
            mt.envMapIntensity = (isUnit && !mt.map) ? Math.min(envBoost, 0.95) : envBoost;
          }
        }
      }
    });
  }

  // Ground fallback while environment GLB loads
  const envGroup = new THREE.Group();
  scene.add(envGroup);

  const envMaterialRefs = {};
  let baseWeatherId = 'apoc_sunset';
  let activeWeatherId = 'apoc_sunset';
  let stormTemporaryTimer = 0.0;
  let lightningState = { timer: 4.5, flash: 0.0 };

  function rebuildEnvReflections(preset) {
    skyUniforms.uTopColor.value.setHex(preset.topColor);
    skyUniforms.uMidColor.value.setHex(preset.midColor);
    skyUniforms.uHorizonColor.value.setHex(preset.horizonColor);
    skyUniforms.uGroundColor.value.setHex(preset.groundColor);
    skyUniforms.uSunColor.value.setHex(preset.sunColor);
    skyUniforms.uSunDir.value.set(...preset.sunDir).normalize();
    skyUniforms.uSunSize.value = preset.sunSize;
    skyUniforms.uCloudColor.value.setHex(preset.cloudColor);
    skyUniforms.uCloudIntensity.value = preset.cloudIntensity;

    const nextRT = pmremGen.fromScene(skyEnvScene, 0.04);
    scene.environment = nextRT.texture;
    scene.environmentIntensity = preset.envInt;
    if (currentEnvRT) currentEnvRT.dispose();
    currentEnvRT = nextRT;
  }

  function applyWeatherPreset(weatherId, isTemporaryStorm = false) {
    activeWeatherId = WEATHER_PRESETS[weatherId] ? weatherId : 'apoc_sunset';
    if (!isTemporaryStorm && activeWeatherId !== 'storm_rain') {
      baseWeatherId = activeWeatherId;
    }
    const p = WEATHER_PRESETS[activeWeatherId];
    syncBloomSkyMaterial();
    rebuildEnvReflections(p);

    scene.background.setHex(p.fogColor);
    scene.fog.color.setHex(p.fogColor);
    scene.fog.density = p.fogDensity;
    renderer.toneMappingExposure = p.exposure;

    hemi.color.setHex(p.hemiSky);
    hemi.groundColor.setHex(p.hemiGround);
    hemi.intensity = p.hemiInt;

    keyLight.color.setHex(p.keyColor);
    keyLight.position.set(...p.keyPos);
    keyLight.intensity = p.keyInt;

    rimLight.color.setHex(p.rimColor);
    rimLight.position.set(...p.rimPos);
    rimLight.intensity = p.rimInt;
    unitRimUniforms.uRimColor.value.setHex(p.rimColor);
    unitRimUniforms.uRimStrength.value = (activeWeatherId === 'apoc_sunset' || activeWeatherId === 'storm_rain') ? 0.30 : 0.24;

    const hasPool = p.lampAlpha > 0.005;
    lampPoolW.visible = hasPool;
    lampPoolE.visible = hasPool;
    lampPoolMatW.opacity = p.lampAlpha;
    lampPoolMatE.opacity = p.lampAlpha;

    if (envMaterialRefs.Mat_Env_AsphaltCracked) {
      envMaterialRefs.Mat_Env_AsphaltCracked.roughness = p.asphaltRough;
      envMaterialRefs.Mat_Env_AsphaltCracked.envMapIntensity = p.asphaltEnv;
    }
    if (envMaterialRefs.Mat_Env_PuddleWet) {
      envMaterialRefs.Mat_Env_PuddleWet.roughness = p.puddleRough;
      envMaterialRefs.Mat_Env_PuddleWet.envMapIntensity = p.puddleEnv;
    }

    rainLines.visible = p.rain;
    const hasCone = p.coneAlpha > 0.005;
    lampConeW.visible = hasCone;
    lampConeE.visible = hasCone;
    coneMatW.opacity = p.coneAlpha;
    coneMatE.opacity = p.coneAlpha;

    partMat.color.setHex(p.particleColor);
    partMat.size = p.particleSize;
    partMat.blending = p.particleMode === 'ash_embers' ? THREE.NormalBlending : THREE.AdditiveBlending;
    partGeo.setDrawRange(0, Math.min(PARTICLE_MAX, p.particleCount));
    lightningState.flash = p.lightning ? 1.0 : 0.0;
    lightningState.timer = 2.4 + Math.random() * 4.5;
    skyUniforms.uFlash.value = lightningState.flash;
  }

  // 3D Defense Barricade & Extraction Radio Beacon at x = -5.0
  const barricadeGroup = new THREE.Group();
  barricadeGroup.position.set(BARRICADE_X, 0, 0);
  scene.add(barricadeGroup);

  const shieldMat = new THREE.MeshStandardMaterial({
    color: 0x22c55e,
    emissive: 0x22c55e,
    emissiveIntensity: 0.75,
    transparent: true,
    opacity: 0.26,
    roughness: 0.2,
    metalness: 0.1,
    side: THREE.DoubleSide,
    depthWrite: false,
  });
  const shieldMesh = new THREE.Mesh(new THREE.PlaneGeometry(5.8, 1.38), shieldMat);
  shieldMesh.rotation.y = Math.PI / 2;
  shieldMesh.position.set(0.28, 0.72, 0);
  barricadeGroup.add(shieldMesh);

  // Extraction Radio Mast behind barricade corner
  const mastGroup = new THREE.Group();
  mastGroup.position.set(-0.85, 0, -2.55);
  barricadeGroup.add(mastGroup);

  const mastBase = new THREE.Mesh(
    new THREE.CylinderGeometry(0.18, 0.26, 0.45, 8),
    new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.7, metalness: 0.5 })
  );
  mastBase.position.y = 0.22;
  mastBase.castShadow = true;
  mastGroup.add(mastBase);

  const mastPole = new THREE.Mesh(
    new THREE.CylinderGeometry(0.055, 0.08, 2.9, 8),
    new THREE.MeshStandardMaterial({ color: 0x475569, roughness: 0.5, metalness: 0.7 })
  );
  mastPole.position.y = 1.65;
  mastPole.castShadow = true;
  mastGroup.add(mastPole);

  const beaconOrbMat = new THREE.MeshStandardMaterial({
    color: 0x22c55e,
    emissive: 0x22c55e,
    emissiveIntensity: 2.2,
    roughness: 0.15,
  });
  const beaconOrb = new THREE.Mesh(new THREE.OctahedronGeometry(0.22, 1), beaconOrbMat);
  beaconOrb.position.y = 3.22;
  mastGroup.add(beaconOrb);

  let barricadeHpRatio = 1.0;
  let barricadeSparkCooldown = 0.0;

  function setBarricadeVisual(ratio) {
    barricadeHpRatio = Math.max(0, Math.min(1, ratio));
    const col = barricadeHpRatio > 0.55
      ? 0x22c55e
      : (barricadeHpRatio > 0.28 ? 0xf59e0b : 0xef4444);
    shieldMat.color.setHex(col);
    shieldMat.emissive.setHex(col);
    beaconOrbMat.color.setHex(col);
    beaconOrbMat.emissive.setHex(col);
    shieldMesh.visible = barricadeHpRatio > 0.001;
  }

  // State arrays & simulation pools
  const units = [];
  const activeVfx = [];
  const activeProjectiles = [];
  const floatLabels = [];
  const deathParticles = [];
  const deathDecals = [];
  const pendingDeathImpacts = [];
  const transientProps = []; // crates, missiles, ground beams

  let nextUid = 1;
  let paused = false;
  let camMode = 'auto';
  let rageTimer = 0.0;
  let squadShieldTimer = 0.0;
  let cameraShake = 0.0;
  let hitStopTimer = 0.0;
  let slowMoScale = 1.0;
  let slowMoTimer = 0.0;
  let dramaticFocus = null; // { targetPos: Vector3, timer, maxTimer }

  const _shakeVec = new THREE.Vector3();
  const _hitFlashColEnemy = new THREE.Color(0xffe6d0);
  const _hitFlashColSurv = new THREE.Color(0xff4040);
  const _tmpVec = new THREE.Vector3();
  const _turnDummy = new THREE.Object3D();

  const contactShadowGeo = new THREE.PlaneGeometry(1, 1);
  const contactShadowMat = new THREE.MeshBasicMaterial({
    map: contactShadowTex, transparent: true, opacity: 0.58, depthWrite: false,
    polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -1,
  });

  function addContactShadow(group, radius = 0.80) {
    const mat = contactShadowMat.clone();
    const decal = new THREE.Mesh(contactShadowGeo, mat);
    decal.rotation.x = -Math.PI / 2;
    decal.position.y = 0.012;
    decal.scale.set(radius * 2.0, radius * 2.0, 1);
    group.add(decal);
    return { mesh: decal, mat, baseRad: radius, baseOpacity: mat.opacity };
  }

  const tierRingGeo = new THREE.RingGeometry(0.42, 0.56, 24);
  const chunkGeo = new THREE.IcosahedronGeometry(0.065, 0);
  const dustRingGeo = new THREE.RingGeometry(0.30, 0.52, 24);

  function pickSurvivorClips(weaponId, availableClips) {
    const w = WEAPONS[weaponId] || WEAPONS.m4;
    const has = (name) => Boolean(availableClips[name]);
    const rWalk = has('Rifle_Walk_Cycle') ? 'Rifle_Walk_Cycle' : 'Rifle_Idle_Ready';
    const rRun = has('Rifle_Run_Cycle') ? 'Rifle_Run_Cycle' : rWalk;
    if (w.cls === 'pistol') {
      return {
        idle: has('Pistol_Idle_Ready') ? 'Pistol_Idle_Ready' : 'Rifle_Idle_Ready',
        aim: has('Pistol_Aim_ADS') ? 'Pistol_Aim_ADS' : 'Pistol_Idle_Ready',
        walk: rWalk, run: rRun,
        attack: has('Pistol_Shoot_Recoil') ? 'Pistol_Shoot_Recoil' : 'Rifle_Shoot_Recoil',
        skill: 'Pistol_Reload_Tactical',
        hit: 'Hit_React',
        death: 'Zombie_Death_Fall',
      };
    }
    if (w.cls === 'bow') {
      return {
        idle: has('Bow_Idle_Ready') ? 'Bow_Idle_Ready' : 'Rifle_Idle_Ready',
        aim: has('Bow_Aim_Draw') ? 'Bow_Aim_Draw' : 'Bow_Idle_Ready',
        walk: rWalk, run: rRun,
        attack: has('Bow_Shoot_Release') ? 'Bow_Shoot_Release' : 'Bow_Aim_Draw',
        skill: 'Bow_Aim_Draw',
        hit: 'Hit_React',
        death: 'Zombie_Death_Fall',
      };
    }
    if (w.cls === 'melee') {
      const mIdle = has('Melee_Idle_Ready') ? 'Melee_Idle_Ready' : 'Rifle_Idle_Ready';
      const mWalk = has('Melee_Walk_Cycle') ? 'Melee_Walk_Cycle' : rWalk;
      const mRun  = has('Melee_Run_Cycle') ? 'Melee_Run_Cycle' : rRun;
      return {
        idle: mIdle, aim: mIdle, walk: mWalk, run: mRun,
        attack: has('Melee_Swing') ? 'Melee_Swing' : 'Rifle_Shoot_Recoil',
        skill: has('Melee_Heavy_Slash') ? 'Melee_Heavy_Slash' : 'Melee_Swing',
        hit: 'Hit_React',
        death: 'Zombie_Death_Fall',
      };
    }
    return {
      idle: 'Rifle_Idle_Ready',
      aim: 'Rifle_Aim_ADS',
      walk: rWalk, run: rRun,
      attack: 'Rifle_Shoot_Recoil',
      skill: 'Rifle_Reload_Tactical',
      hit: 'Hit_React',
      death: 'Zombie_Death_Fall',
    };
  }

  function playClip(unit, clipName, loopOnce = false, fade = 0.14, clipSpeed = 1.0, exclusive = false) {
    if (!clipName) return null;
    const clip = unit.clipsByName[clipName];
    if (!clip) return null;
    if (unit.currentClip === clipName && !loopOnce) {
      if (unit.currentAction) {
        unit.currentAction.enabled = true;
        unit.currentAction.setEffectiveWeight(1.0);
        unit.currentAction.timeScale = clipSpeed;
      }
      return unit.currentAction;
    }

    const nextAct = unit.mixer.clipAction(clip);
    if (exclusive) {
      for (const c of Object.values(unit.clipsByName)) {
        const existing = unit.mixer.existingAction(c);
        if (existing && existing !== nextAct && existing.isRunning()) {
          existing.fadeOut(fade);
        }
      }
    }
    nextAct.reset();
    nextAct.enabled = true;
    nextAct.setEffectiveWeight(1.0);
    nextAct.timeScale = clipSpeed;
    if (loopOnce) {
      nextAct.setLoop(THREE.LoopOnce, 1);
      nextAct.clampWhenFinished = true;
    } else {
      nextAct.setLoop(THREE.LoopRepeat, Infinity);
      nextAct.clampWhenFinished = false;
    }
    nextAct.play();
    if (!exclusive && unit.currentAction && unit.currentAction !== nextAct) {
      unit.currentAction.crossFadeTo(nextAct, fade, false);
    }
    unit.currentAction = nextAct;
    unit.currentClip = clipName;
    return nextAct;
  }

  function createUnitHUD(unit) {
    const el = document.createElement('div');
    el.className = `unit-hud ${unit.kind}${unit.isBoss ? ' boss-unit' : ''}${unit.isSultan ? ' sultan' : ''}`;
    el.innerHTML = `
      <div class="unit-name"></div>
      <div class="hp-track"><div class="hp-fill ${unit.kind}"></div></div>
    `;
    unit.nameEl = el.querySelector('.unit-name');
    unit.hpFillEl = el.querySelector('.hp-fill');
    labelsLayer.appendChild(el);
    unit.hudEl = el;
    syncUnitHUDText(unit);
  }

  function syncUnitHUDText(unit) {
    if (!unit.nameEl) return;
    if (unit.team === 'survivor') {
      const crown = unit.level >= 8 || unit.isSultan ? '👑 ' : (unit.isVip ? '⭐ ' : '');
      const wShort = WEAPONS[unit.weaponId]?.id?.toUpperCase() || 'GUN';
      unit.nameEl.textContent = `${crown}${unit.ownerName} • L${unit.level} ${wShort}`;
    } else if (unit.isBoss) {
      unit.nameEl.textContent = unit.ownerName ? `💀 @${unit.ownerName} [${unit.shortName}]` : `💀 ${unit.shortName}`;
    } else if (unit.ownerName) {
      unit.nameEl.textContent = `☠️ @${unit.ownerName}`;
    } else {
      unit.nameEl.textContent = unit.shortName;
    }
  }

  function spawnFloatingText(worldPos, text, color = '#fbbf24', sizePx = 13) {
    const el = document.createElement('div');
    el.className = 'float-dmg';
    el.style.color = color;
    el.style.fontSize = `${sizePx}px`;
    el.textContent = text;
    labelsLayer.appendChild(el);
    floatLabels.push({ el, pos: worldPos.clone(), life: 0.80, maxLife: 0.80 });
  }

  function prepareCorpseMaterials(unit) {
    if (unit.corpseMats) return;
    const list = [];
    unit.model.traverse((o) => {
      if (!(o.isMesh || o.isSkinnedMesh) || !o.material) return;
      const wasArr = Array.isArray(o.material);
      const srcArr = wasArr ? o.material : [o.material];
      const clonedArr = srcArr.map((mt) => {
        if (!mt) return mt;
        const c = mt.clone();
        if (c.userData && !c.userData._hasRimShader) applyUnitRimShader(c);
        list.push({
          mat: c,
          origColor: c.color ? c.color.clone() : null,
          origEmissive: c.emissive ? c.emissive.clone() : null,
          origEmissiveInt: ('emissiveIntensity' in c) ? c.emissiveIntensity : null,
          origRough: ('roughness' in c) ? c.roughness : null,
        });
        return c;
      });
      o.material = wasArr ? clonedArr : clonedArr[0];
    });
    unit.corpseMats = list;
  }

  function disposeUnit(unit) {
    if (unit.corpseMats) {
      for (const entry of unit.corpseMats) entry.mat.dispose();
      unit.corpseMats = null;
    }
    if (unit.shadow) unit.shadow.mat.dispose();
    if (unit.tierRingMat) unit.tierRingMat.dispose();
    if (unit.hudEl) unit.hudEl.remove();
    scene.remove(unit.group);
  }

  function clearDeathFx() {
    for (const p of deathParticles) {
      scene.remove(p.mesh);
      p.mesh.material.dispose();
    }
    deathParticles.length = 0;
    for (const d of deathDecals) {
      scene.remove(d.mesh);
      d.mesh.material.dispose();
    }
    deathDecals.length = 0;
    pendingDeathImpacts.length = 0;
  }

  function spawnBurstParticles(pos, dirBias, colors, count, speedScale = 1.0, lowDust = false) {
    for (let i = 0; i < count; i++) {
      const col = colors[i % colors.length];
      const mat = new THREE.MeshStandardMaterial({
        color: col, roughness: lowDust ? 0.92 : 0.40, metalness: 0.05,
        transparent: lowDust, opacity: lowDust ? 0.72 : 1.0,
      });
      const m = new THREE.Mesh(chunkGeo, mat);
      const sc = (lowDust ? 1.15 : 0.65) + Math.random() * 1.10;
      m.position.copy(pos);
      m.scale.setScalar(sc);
      m.rotation.set(Math.random() * 6.28, Math.random() * 6.28, Math.random() * 6.28);
      scene.add(m);

      const ang = Math.random() * Math.PI * 2;
      const hSpd = (lowDust ? 1.8 : 1.2) + Math.random() * (lowDust ? 2.4 : 3.0) * speedScale;
      const vx = Math.cos(ang) * hSpd + (dirBias ? dirBias.x * (1.2 + Math.random() * 1.4) : 0);
      const vz = Math.sin(ang) * hSpd + (dirBias ? dirBias.z * (1.2 + Math.random() * 1.4) : 0);
      const vy = lowDust ? (0.4 + Math.random() * 1.0) : (2.2 + Math.random() * 3.2 * speedScale);
      const maxLife = lowDust ? (0.42 + Math.random() * 0.24) : (0.85 + Math.random() * 0.55);
      deathParticles.push({
        mesh: m, vx, vy, vz,
        rx: (Math.random() - 0.5) * 14, ry: (Math.random() - 0.5) * 14,
        life: maxLife, maxLife, baseScale: sc, lowDust,
      });
    }
  }

  function spawnExpandingRing(pos, colorHex, startScale, endScale, duration = 0.55, baseOpacity = 0.72) {
    const mat = new THREE.MeshBasicMaterial({
      color: colorHex, side: THREE.DoubleSide, transparent: true, opacity: baseOpacity, depthWrite: false,
    });
    const ring = new THREE.Mesh(dustRingGeo, mat);
    ring.rotation.x = -Math.PI / 2;
    ring.position.set(pos.x, 0.025, pos.z);
    ring.scale.setScalar(startScale);
    scene.add(ring);
    deathDecals.push({
      kind: 'ring', mesh: ring, age: 0, maxLife: duration, startScale, endScale, baseOpacity,
    });
  }

  async function spawnTimedVfx(glbUrl, worldPos, dirVec, { groundFlat = false, scale = 1.0, life = 0.36 } = {}) {
    if (!glbUrl) return;
    try {
      const gltf = await loadGLB(glbUrl);
      const mesh = gltf.scene.clone(true);
      mesh.position.copy(worldPos);
      mesh.scale.setScalar(scale);
      if (!groundFlat && dirVec && dirVec.lengthSq() > 1e-5) {
        mesh.lookAt(worldPos.clone().add(dirVec));
        mesh.rotateX(Math.PI * 0.5);
      }
      scene.add(mesh);
      activeVfx.push({ mesh, life, maxLife: life, startScale: scale });
    } catch (err) {
      console.warn('VFX load warning:', glbUrl, err);
    }
  }

  function spawnProjectile(fromPos, toPos, colorHex, speed = 24.0, onImpact = null) {
    const dir = new THREE.Vector3().subVectors(toPos, fromPos);
    const dist = dir.length();
    if (dist < 0.05) {
      if (onImpact) onImpact();
      return;
    }
    dir.normalize();
    const mesh = new THREE.Mesh(
      new THREE.CylinderGeometry(0.032, 0.020, 0.48, 6),
      new THREE.MeshBasicMaterial({ color: colorHex })
    );
    mesh.position.copy(fromPos);
    mesh.lookAt(toPos);
    mesh.rotateX(Math.PI * 0.5);
    scene.add(mesh);
    activeProjectiles.push({ mesh, dir, speed, distLeft: dist, onImpact });
  }

  function spawnDeathEffect(target, attacker) {
    prepareCorpseMaterials(target);
    const theme = DEATH_THEMES[target.specId] || DEATH_THEMES._default;
    const away = attacker
      ? new THREE.Vector3().subVectors(target.group.position, attacker.group.position).setY(0)
      : new THREE.Vector3(1, 0, 0);
    if (away.lengthSq() > 1e-5) away.normalize();

    const origin = target.group.position.clone().add(new THREE.Vector3(0, target.height * 0.44, 0));
    spawnBurstParticles(origin, away, theme.colors, theme.count, Math.min(1.3, 0.85 + target.height * 0.14), false);

    let puddleCount = 0;
    for (const d of deathDecals) {
      if (d.kind === 'puddle') puddleCount++;
    }
    if (puddleCount >= MAX_DEATH_PUDDLES) {
      const idx = deathDecals.findIndex((d) => d.kind === 'puddle');
      if (idx !== -1) {
        scene.remove(deathDecals[idx].mesh);
        deathDecals[idx].mesh.material.dispose();
        deathDecals.splice(idx, 1);
      }
    }

    const fwd = new THREE.Vector3(0, 0, 1).applyQuaternion(target.group.quaternion);
    const poolShift = target.specId === 'mutant_arachnid_maw' ? 0.0 : 0.34 * (target.ringScale || 1.0);
    const poolMat = new THREE.MeshStandardMaterial({
      map: splatterTex, color: theme.poolColor, transparent: true, opacity: 0.88,
      roughness: 0.24, metalness: 0.06, depthWrite: false,
      polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2,
    });
    const pool = new THREE.Mesh(contactShadowGeo, poolMat);
    pool.rotation.set(-Math.PI / 2, Math.random() * Math.PI * 2, 0);
    pool.position.set(target.group.position.x + fwd.x * poolShift, 0.008, target.group.position.z + fwd.z * poolShift);
    pool.scale.setScalar(0.22);
    pool.receiveShadow = true;
    scene.add(pool);
    deathDecals.push({ kind: 'puddle', mesh: pool, targetScale: theme.poolRad * 2.0, age: 0, growDur: 1.25 });

    pendingDeathImpacts.push({
      timer: theme.impactDelay,
      unit: target,
      shift: poolShift,
      fwd: fwd.clone(),
      theme,
    });
  }

  async function equipSurvivorWeapon(unit, weaponId) {
    const wMeta = WEAPONS[weaponId] || WEAPONS.m4;
    if (unit.weaponNode && unit.weaponNode.parent) {
      unit.weaponNode.parent.remove(unit.weaponNode);
      unit.weaponNode = null;
      unit.muzzleNode = null;
    }

    const wGltf = await loadGLB(wMeta.glb);
    const wClone = SkeletonUtils.clone(wGltf.scene);
    prepShadows(wClone, 1.25, true);

    const sockName = wMeta.hand === 'L' ? 'WeaponSocket_L' : 'WeaponSocket_R';
    const sock = unit.model.getObjectByName(sockName);
    if (sock) sock.add(wClone);
    else unit.model.add(wClone);

    unit.weaponNode = wClone;
    unit.muzzleNode = wClone.getObjectByName('MuzzleSocket') || null;
    unit.weaponId = wMeta.id;
    unit.weaponClass = wMeta.cls;
    unit.range = wMeta.range;
    unit.cd = wMeta.cd;
    unit.dmg = wMeta.dmg * (1 + (unit.level - 1) * 0.08);
    unit.muzzleZ = wMeta.muzzleZ || 0.45;
    unit.vfxId = wMeta.vfx;
    unit.projId = wMeta.proj;
    unit.slashScale = wMeta.slashScale || 1.0;
    unit.anims = pickSurvivorClips(wMeta.id, unit.clipsByName);
    unit.currentClip = null;
    playClip(unit, unit.anims.aim || unit.anims.idle, false, 0.08, 1.0, true);
  }

  function findSurvivorSlotPos() {
    const active = units.filter((u) => u.team === 'survivor' && !u.dead);
    const slots = [
      [-3.1, 0.0],
      [-3.4, -1.6],
      [-3.4,  1.6],
      [-2.3, -0.9],
      [-2.3,  0.9],
      [-3.9, -2.5],
      [-3.9,  2.5],
      [-2.1, -2.2],
    ];
    let best = slots[active.length % slots.length];
    let bestMinDist = -1;
    for (const [sx, sz] of slots) {
      let minD = 999;
      for (const a of active) {
        const d = Math.hypot(a.group.position.x - sx, a.group.position.z - sz);
        if (d < minD) minD = d;
      }
      if (minD > bestMinDist) {
        bestMinDist = minD;
        best = [sx, sz];
      }
    }
    return best;
  }

  async function spawnSurvivor({ specId = null, ownerName = 'Bot', level = 1, isVip = false, isSultan = false } = {}) {
    const meta = (specId && SURVIVORS.find((s) => s.id === specId))
      || SURVIVORS[Math.floor(Math.random() * SURVIVORS.length)];
    const gltf = await loadGLB(meta.unarmedGlb);
    const clone = SkeletonUtils.clone(gltf.scene);
    prepShadows(clone, 1.25, true);

    const mixer = new THREE.AnimationMixer(clone);
    const clipsByName = {};
    for (const c of gltf.animations) clipsByName[c.name] = c;

    const group = new THREE.Group();
    group.add(clone);
    const shadow = addContactShadow(group, 0.70);

    const clampedLv = Math.min(8, Math.max(1, level));
    const tierMeta = getTierMeta(clampedLv, meta.track);
    const tierRingMat = new THREE.MeshBasicMaterial({
      color: tierMeta.ringColor, side: THREE.DoubleSide, transparent: true, opacity: clampedLv >= 7 ? 0.90 : 0.65,
    });
    const tierRing = new THREE.Mesh(tierRingGeo, tierRingMat);
    tierRing.rotation.x = -Math.PI / 2;
    tierRing.position.y = 0.018;
    group.add(tierRing);

    const [sx, sz] = findSurvivorSlotPos();
    group.position.set(sx, 0, sz);
    group.rotation.set(0, Math.PI * 0.5, 0);
    scene.add(group);

    const maxHp = Math.round(meta.baseHp * (1 + (clampedLv - 1) * 0.14));
    const unit = {
      uid: nextUid++,
      team: 'survivor',
      kind: 'survivor',
      specId: meta.id,
      track: meta.track,
      ownerName: ownerName || meta.name,
      shortName: meta.name,
      isBot: !isVip && ownerName.startsWith('Unit-'),
      isVip,
      isSultan: isSultan || clampedLv >= 8,
      level: clampedLv,
      kills: 0,
      group, model: clone, mixer, clipsByName,
      anims: {},
      shadow, tierRing, tierRingMat,
      bodyRadius: 0.34,
      corpseMats: null,
      hp: maxHp, maxHp,
      speed: 2.35,
      range: 10, skillRange: 10, cd: 0.5, dmg: 20,
      weaponId: tierMeta.weaponId,
      weaponClass: tierMeta.weapon.cls,
      weaponNode: null, muzzleNode: null, muzzleZ: 0.45,
      vfxId: tierMeta.weapon.vfx, projId: tierMeta.weapon.proj, slashScale: 1.0,
      cooldown: Math.random() * 0.25,
      attackCount: 0,
      vel: new THREE.Vector3(),
      pendingHit: null,
      dead: false, deadTimer: 0,
      hitFlash: 0,
      animJitter: 0.94 + Math.random() * 0.12,
      lockTimer: 0,
      height: 1.80,
    };

    units.push(unit);
    await equipSurvivorWeapon(unit, tierMeta.weaponId);
    createUnitHUD(unit);

    spawnExpandingRing(group.position, tierMeta.ringColor, 0.3, 1.4, 0.45, 0.78);
    spawnFloatingText(group.position.clone().add(new THREE.Vector3(0, 2.2, 0)), `+@${unit.ownerName}`, tierMeta.badgeColor, 12);
    return unit;
  }

  async function upgradeSurvivor(unit, levels = 1, forceLevel = null) {
    if (!unit || unit.dead) return false;
    const prevLv = unit.level;
    const nextLv = forceLevel ? Math.min(8, Math.max(unit.level, forceLevel)) : Math.min(8, unit.level + levels);

    if (prevLv >= 8 && !forceLevel) {
      // Golden Overcharge when already Lv.8
      unit.maxHp += 60;
      unit.hp = unit.maxHp;
      unit.dmg = Math.round(unit.dmg * 1.12);
      unit.isSultan = true;
      spawnExpandingRing(unit.group.position, 0xfacc15, 0.4, 2.0, 0.55, 0.90);
      spawnFloatingText(unit.group.position.clone().add(new THREE.Vector3(0, 2.3, 0)), '👑 OVERCHARGE!', '#facc15', 14);
      syncUnitHUDText(unit);
      return true;
    }

    unit.level = nextLv;
    unit.isVip = true;
    if (nextLv >= 8) unit.isSultan = true;
    const tierMeta = getTierMeta(nextLv, unit.track);
    unit.maxHp = Math.round((SURVIVORS.find((s) => s.id === unit.specId)?.baseHp || 260) * (1 + (nextLv - 1) * 0.16));
    unit.hp = unit.maxHp;

    if (unit.tierRingMat) {
      unit.tierRingMat.color.setHex(tierMeta.ringColor);
      unit.tierRingMat.opacity = nextLv >= 7 ? 0.95 : 0.72;
    }

    await equipSurvivorWeapon(unit, tierMeta.weaponId);
    syncUnitHUDText(unit);
    unit.hudEl.classList.toggle('sultan', unit.isSultan);

    // Rising vertical upgrade light column
    const beamMat = new THREE.MeshBasicMaterial({
      color: tierMeta.ringColor, transparent: true, opacity: 0.55, blending: THREE.AdditiveBlending, depthWrite: false,
    });
    const beam = new THREE.Mesh(new THREE.CylinderGeometry(0.45, 0.55, 4.2, 12, 1, true), beamMat);
    beam.position.set(unit.group.position.x, 2.1, unit.group.position.z);
    scene.add(beam);
    transientProps.push({
      mesh: beam, age: 0, maxAge: 0.65,
      onUpdate(t) {
        beamMat.opacity = 0.55 * (1 - t);
        beam.scale.set(1 + t * 0.5, 1 + t * 0.6, 1 + t * 0.5);
      },
      onDone() { beam.geometry.dispose(); beamMat.dispose(); },
    });

    spawnExpandingRing(unit.group.position, tierMeta.ringColor, 0.35, 1.9, 0.50, 0.85);
    spawnFloatingText(unit.group.position.clone().add(new THREE.Vector3(0, 2.35, 0)), `⬆ Lv.${nextLv} ${tierMeta.weapon.id.toUpperCase()}!`, tierMeta.badgeColor, 13);
    audio.playUpgradeFanfare();
    return true;
  }

  async function spawnEnemy({ specId = 'zombie_walker_shambler', ownerName = null, isBoss = false, isElite = false, waveMult = 1.0 } = {}) {
    const bossMeta = isBoss
      ? (MUTANT_BOSSES.find((b) => b.id === specId) || MUTANT_BOSSES[Math.floor(Math.random() * MUTANT_BOSSES.length)])
      : null;
    const meta = bossMeta || ZOMBIES[specId] || ZOMBIES.zombie_walker_shambler;

    const gltf = await loadGLB(meta.glb);
    const clone = SkeletonUtils.clone(gltf.scene);
    const sc = meta.scale || [1, 1, 1];
    clone.scale.set(sc[0], sc[1], sc[2]);
    prepShadows(clone, 1.25, true);

    const mixer = new THREE.AnimationMixer(clone);
    const clipsByName = {};
    for (const c of gltf.animations) clipsByName[c.name] = c;

    const group = new THREE.Group();
    group.add(clone);
    const shadow = addContactShadow(group, isBoss ? 1.50 : 0.76);

    const spawnX = (isBoss ? 7.6 : 6.6) + Math.random() * 2.2;
    const spawnZ = (Math.random() - 0.5) * 4.4;
    group.position.set(spawnX, 0, spawnZ);
    group.rotation.set(0, -Math.PI * 0.5, 0);
    scene.add(group);

    const hpScale = isBoss ? (1 + (waveMult - 1) * 0.25) : waveMult;
    const finalHp = Math.round(meta.hp * hpScale);

    const unit = {
      uid: nextUid++,
      team: 'enemy',
      kind: isBoss ? 'mutant' : 'zombie',
      specId: meta.id,
      ownerName,
      shortName: isBoss ? meta.title : meta.name,
      isBoss,
      isElite,
      group, model: clone, mixer, clipsByName, anims: meta.anims, shadow,
      bodyRadius: meta.bodyRadius || 0.38,
      corpseMats: null,
      hp: finalHp, maxHp: finalHp,
      speed: meta.speed,
      walkStride: meta.walkStride || 0.96,
      runStride: meta.runStride || meta.walkStride || 0.96,
      sprintSpeed: meta.sprintSpeed || null,
      ringScale: meta.ringScale || 1.0,
      vfxScale: meta.vfxScale || 1.0,
      range: meta.range,
      skillRange: meta.skillRange,
      cd: meta.cd,
      cooldown: Math.random() * 0.30,
      dmg: meta.dmg,
      skillDmg: meta.skillDmg,
      barricadeDmg: meta.barricadeDmg || meta.dmg,
      vfxGlb: meta.vfxGlb,
      vfxMode: meta.vfxMode,
      vfxProjColor: meta.vfxProjColor || null,
      attackCount: 0,
      vel: new THREE.Vector3(),
      pendingHit: null,
      dead: false, deadTimer: 0, corpseCleaned: false,
      hitFlash: 0,
      animJitter: 0.94 + Math.random() * 0.12,
      lockTimer: 0,
      height: meta.height || 1.82,
    };

    units.push(unit);
    createUnitHUD(unit);
    const startAct = playClip(unit, unit.anims.walk, false, 0.08, 1.0, true);
    if (startAct) startAct.time = Math.random() * (startAct.getClip().duration || 1.0);

    if (isBoss) {
      spawnExpandingRing(group.position, 0xef4444, 0.5, 3.4, 0.85, 0.92);
      triggerFlashLight(group.position.clone().add(new THREE.Vector3(0, 1.8, 0)), 0xef4444, 7.5, 0.35);
      cameraShake = Math.max(cameraShake, 0.20);
      audio.playBossHorn();
      triggerDramaticFocus(group.position, 1.15, 0.42);
    }
    return unit;
  }

  function getMuzzleWorldPos(unit) {
    if (unit.muzzleNode) {
      const p = new THREE.Vector3();
      unit.muzzleNode.getWorldPosition(p);
      return p;
    }
    const sock = unit.model.getObjectByName(unit.weaponClass === 'bow' ? 'WeaponSocket_L' : 'WeaponSocket_R');
    if (sock) {
      const p = new THREE.Vector3(0, unit.muzzleZ, -0.04);
      sock.localToWorld(p);
      return p;
    }
    const fwd = new THREE.Vector3(0, 0, 1).applyQuaternion(unit.group.quaternion);
    return unit.group.position.clone().add(new THREE.Vector3(0, 1.38, 0)).addScaledVector(fwd, 0.55);
  }

  function getEnemyAttackOrigin(unit) {
    const fwd = new THREE.Vector3(0, 0, 1).applyQuaternion(unit.group.quaternion);
    if (unit.vfxMode === 'ground_slam') {
      const lHand = unit.model.getObjectByName('Arm_L_Hand');
      const rHand = unit.model.getObjectByName('Arm_R_Hand');
      if (lHand && rHand) {
        const pL = new THREE.Vector3(); lHand.getWorldPosition(pL);
        const pR = new THREE.Vector3(); rHand.getWorldPosition(pR);
        return new THREE.Vector3(0.5 * (pL.x + pR.x), 0.03, 0.5 * (pL.z + pR.z)).addScaledVector(fwd, 0.25);
      }
      return unit.group.position.clone().addScaledVector(fwd, 1.0).setY(0.03);
    }
    if (unit.vfxMode === 'scythe_forward') {
      const sb = unit.model.getObjectByName('Scythe_Blade');
      if (sb) {
        const p = new THREE.Vector3(); sb.getWorldPosition(p);
        return p.addScaledVector(fwd, 0.25);
      }
    }
    const head = unit.model.getObjectByName('Head') || unit.model.getObjectByName('mixamorig:Head');
    if (head) {
      const p = new THREE.Vector3(); head.getWorldPosition(p);
      return p.addScaledVector(fwd, 0.24);
    }
    return unit.group.position.clone().add(new THREE.Vector3(0, unit.height * 0.65, 0)).addScaledVector(fwd, 0.45);
  }

  function applyDamage(target, amount, attacker, pushImpulse = 0.0, showText = true) {
    if (!target || target.dead) return;
    let dmg = amount;
    if (target.team === 'survivor' && squadShieldTimer > 0) {
      dmg = Math.max(1, Math.round(dmg * 0.45));
    }
    target.hp = Math.max(0, target.hp - dmg);

    const hitPos = target.group.position.clone().add(new THREE.Vector3(0, target.height * 0.62, 0));
    if (showText) {
      const col = target.team === 'enemy' ? '#fef08a' : '#f87171';
      spawnFloatingText(hitPos, `-${Math.round(dmg)}`, col, dmg >= 55 ? 15 : 12);
    }
    spawnTimedVfx(VFX_PATHS.blood, hitPos, new THREE.Vector3(0, 1, 0), { groundFlat: true, scale: 0.85, life: 0.26 });

    if (pushImpulse > 0 && attacker) {
      const kb = new THREE.Vector3().subVectors(target.group.position, attacker.group.position).setY(0);
      if (kb.lengthSq() > 1e-5) {
        kb.normalize();
        const massFactor = (target.maxHp > 400 || target.isBoss) ? 0.25 : 1.0;
        target.vel.addScaledVector(kb, pushImpulse * massFactor);
      }
    }
    audio.playHit(dmg >= 40, target.kind === 'mutant');

    if (target.hp <= 0) {
      target.hitFlash = 0;
      if (target.corpseMats) {
        for (const entry of target.corpseMats) {
          if (entry.origEmissive && entry.mat.emissive) entry.mat.emissive.copy(entry.origEmissive);
          if (entry.origEmissiveInt !== null) entry.mat.emissiveIntensity = entry.origEmissiveInt;
        }
      }
      target.dead = true;
      target.deadTimer = 0;
      target.pendingHit = null;
      target.lockTimer = 0;
      if (target.hudEl) target.hudEl.classList.add('dead');
      if (attacker && attacker.team === 'survivor') {
        attacker.kills = (attacker.kills || 0) + 1;
      }
      spawnDeathEffect(target, attacker);
      playClip(target, target.anims.death || target.anims.hit, true, 0.12, 1.0, true);
      if (callbacks.onUnitDied) callbacks.onUnitDied(target, attacker);
    } else {
      prepareCorpseMaterials(target);
      target.hitFlash = 0.09;
      if (dmg >= 45 || pushImpulse >= 2.2) {
        hitStopTimer = Math.max(hitStopTimer, 0.022);
      }
      if (target.lockTimer <= 0 && target.kind === 'zombie') {
        playClip(target, target.anims.hit, true, 0.08, 1.15);
        target.lockTimer = 0.22;
      }
    }
  }

  function nearestLivingOpponent(unit) {
    let best = null;
    let bestD = Infinity;
    for (const other of units) {
      if (other.dead || other.team === unit.team) continue;
      const d = unit.group.position.distanceTo(other.group.position);
      if (d < bestD) { bestD = d; best = other; }
    }
    return { target: best, dist: bestD };
  }

  function resolveUnitSeparation(dt) {
    if (dt <= 0) return;
    const n = units.length;
    for (let i = 0; i < n; i++) {
      const a = units[i];
      if (a.dead) continue;
      const rA = a.bodyRadius || 0.36;
      for (let j = i + 1; j < n; j++) {
        const b = units[j];
        if (b.dead) continue;
        const rB = b.bodyRadius || 0.36;
        const minDist = (rA + rB) * (a.team === b.team ? 0.88 : 0.76);
        let dx = a.group.position.x - b.group.position.x;
        let dz = a.group.position.z - b.group.position.z;
        const d2 = dx * dx + dz * dz;
        if (d2 >= minDist * minDist) continue;
        let dist = Math.sqrt(d2);
        if (dist < 1e-4) {
          const ang = (a.uid * 1.618 + b.uid * 2.718) % 6.283;
          dx = Math.cos(ang); dz = Math.sin(ang); dist = 1.0;
        }
        const push = Math.min(0.08, (minDist - dist) * Math.min(1.0, 7.0 * dt));
        const nx = dx / dist, nz = dz / dist;
        a.group.position.x = THREE.MathUtils.clamp(a.group.position.x + nx * push * 0.5, -4.4, 9.5);
        a.group.position.z = THREE.MathUtils.clamp(a.group.position.z + nz * push * 0.5, -2.75, 2.75);
        b.group.position.x = THREE.MathUtils.clamp(b.group.position.x - nx * push * 0.5, -4.4, 9.5);
        b.group.position.z = THREE.MathUtils.clamp(b.group.position.z - nz * push * 0.5, -2.75, 2.75);
      }
    }
  }

  function lookAtDir(unit, vec, dt) {
    if (vec.lengthSq() <= 1e-6) return;
    const lp = new THREE.Vector3(unit.group.position.x + vec.x, unit.group.position.y, unit.group.position.z + vec.z);
    _turnDummy.position.copy(unit.group.position);
    _turnDummy.lookAt(lp);
    unit.group.quaternion.slerp(_turnDummy.quaternion, Math.min(1.0, dt * 11.0));
  }

  function updateUnitAI(unit, dt) {
    unit.mixer.update(dt);

    if (unit.vel.lengthSq() > 1e-5 && dt > 0) {
      unit.group.position.addScaledVector(unit.vel, dt);
      unit.group.position.x = THREE.MathUtils.clamp(unit.group.position.x, -4.45, 9.8);
      unit.group.position.z = THREE.MathUtils.clamp(unit.group.position.z, -2.75, 2.75);
      unit.vel.multiplyScalar(Math.exp((unit.dead ? -13.0 : -8.5) * dt));
    }

    if (!unit.dead && unit.hitFlash > 0 && dt > 0 && unit.corpseMats) {
      unit.hitFlash = Math.max(0.0, unit.hitFlash - dt);
      const k = unit.hitFlash / 0.09;
      const flashCol = unit.team === 'survivor' ? _hitFlashColSurv : _hitFlashColEnemy;
      for (const entry of unit.corpseMats) {
        if (!entry.mat.emissive) continue;
        if (k > 0.001) {
          if (entry.origEmissive) entry.mat.emissive.copy(entry.origEmissive).lerp(flashCol, k);
          else entry.mat.emissive.copy(flashCol);
          entry.mat.emissiveIntensity = Math.max(entry.origEmissiveInt || 0.0, 1.30 * k);
        } else {
          if (entry.origEmissive) entry.mat.emissive.copy(entry.origEmissive);
          entry.mat.emissiveIntensity = entry.origEmissiveInt ?? 0.0;
        }
      }
    }

    if (unit.dead) {
      if (dt > 0) {
        unit.deadTimer += dt;
        const t = Math.min(1.0, unit.deadTimer / 1.35);
        if (unit.corpseMats) {
          for (const entry of unit.corpseMats) {
            if (entry.origColor && entry.mat.color) entry.mat.color.copy(entry.origColor).multiplyScalar(1.0 - 0.34 * t);
            if (entry.origRough !== null) entry.mat.roughness = Math.min(1.0, entry.origRough + 0.14 * t);
          }
        }
        if (unit.shadow) {
          const sc = unit.shadow.baseRad * 2.0 * (1.0 + 0.16 * t);
          unit.shadow.mesh.scale.set(sc, sc, 1);
          unit.shadow.mat.opacity = unit.shadow.baseOpacity * (1.0 - 0.38 * t);
        }
        if (unit.deadTimer > 4.2) {
          unit.group.position.y -= 0.75 * dt;
          if (unit.tierRingMat) unit.tierRingMat.opacity = Math.max(0, unit.tierRingMat.opacity - dt);
        }
      }
      return;
    }

    if (unit.tierRing && unit.team === 'survivor') {
      const pulse = 1.0 + 0.06 * Math.sin(performance.now() * 0.006 + unit.uid);
      unit.tierRing.scale.setScalar((unit.isSultan ? 1.25 : 1.0) * pulse);
    }

    // Pending melee / slam hit resolution
    if (unit.pendingHit && dt > 0) {
      unit.pendingHit.timer -= dt;
      if (unit.pendingHit.timer <= 0) {
        const ph = unit.pendingHit;
        unit.pendingHit = null;
        if (ph.kind === 'melee_surv') {
          const muz = getMuzzleWorldPos(unit);
          const fwd = new THREE.Vector3(0, 0, 1).applyQuaternion(unit.group.quaternion);
          spawnTimedVfx(VFX_PATHS.slash, muz, fwd, { groundFlat: false, scale: unit.slashScale || 1.05, life: 0.26 });
          audio.playMelee(ph.push > 2.0);
          if (ph.target && !ph.target.dead && unit.group.position.distanceTo(ph.target.group.position) <= unit.range + 1.4) {
            applyDamage(ph.target, ph.dmg, unit, ph.push || 1.6);
          }
        } else if (ph.kind === 'enemy_melee') {
          const fwd = new THREE.Vector3(0, 0, 1).applyQuaternion(unit.group.quaternion);
          const o2 = getEnemyAttackOrigin(unit);
          spawnTimedVfx(unit.vfxGlb, o2, fwd, { groundFlat: ph.isSlam, scale: (ph.isSlam ? 1.05 : 0.95) * (unit.vfxScale || 1.0), life: 0.44 });
          audio.playMonsterAttack(ph.isSlam);
          if (ph.attackBarricade) {
            spawnTimedVfx(VFX_PATHS.spark, new THREE.Vector3(BARRICADE_X + 0.35, 0.85, unit.group.position.z), new THREE.Vector3(1, 0, 0), { scale: 1.1, life: 0.25 });
            cameraShake = Math.max(cameraShake, unit.isBoss ? 0.14 : 0.05);
            if (callbacks.onBarricadeDamage) callbacks.onBarricadeDamage(unit.barricadeDmg, unit);
          } else if (ph.target && !ph.target.dead && unit.group.position.distanceTo(ph.target.group.position) <= ph.maxDist) {
            applyDamage(ph.target, ph.dmg, unit, ph.isSlam ? 2.8 : 1.6);
          }
        }
      }
    }

    if (unit.cooldown > 0) unit.cooldown -= dt;
    if (unit.lockTimer > 0) {
      unit.lockTimer -= dt;
      return;
    }

    if (unit.team === 'enemy') {
      const stormMult = stormTemporaryTimer > 0 ? 1.35 : 1.0;
      const { target, dist } = nearestLivingOpponent(unit);
      const distBarricade = Math.max(0, unit.group.position.x - ENEMY_STOP_X);
      const targetBarricade = !target || distBarricade < 0.75;

      const goalX = targetBarricade ? ENEMY_STOP_X : target.group.position.x;
      const goalZ = targetBarricade ? THREE.MathUtils.clamp(unit.group.position.z, -2.5, 2.5) : target.group.position.z;
      const dir = new THREE.Vector3(goalX - unit.group.position.x, 0, goalZ - unit.group.position.z);
      const effDist = targetBarricade ? distBarricade : dist;
      if (dir.lengthSq() > 1e-6) dir.normalize();

      const useSkill = !targetBarricade && (unit.attackCount % 2 === 1) && Boolean(unit.anims.skill);
      const engageRange = targetBarricade ? 0.55 : (useSkill ? unit.skillRange : unit.range);

      if (effDist > engageRange) {
        const isSprint = (effDist > engageRange + 2.8) && unit.anims.run && (unit.anims.run !== unit.anims.walk);
        const baseSpd = isSprint ? (unit.sprintSpeed || unit.speed * 1.40) : unit.speed;
        const moveSpd = baseSpd * stormMult;
        const moveClip = isSprint ? unit.anims.run : unit.anims.walk;
        const clipDur = (unit.clipsByName[moveClip]?.duration) || 1.0;
        const strideLen = (isSprint && unit.runStride) ? unit.runStride : (unit.walkStride || 0.96);
        const clipScale = THREE.MathUtils.clamp(((moveSpd * clipDur) / strideLen) * unit.animJitter, 0.7, 1.9);
        lookAtDir(unit, dir, dt);
        unit.group.position.addScaledVector(dir, moveSpd * dt);
        playClip(unit, moveClip, false, 0.14, clipScale);
      } else if (unit.cooldown <= 0) {
        lookAtDir(unit, targetBarricade ? new THREE.Vector3(-1, 0, 0) : dir, dt);
        unit.attackCount++;
        const clip = (useSkill ? unit.anims.skill : unit.anims.attack);
        const act = playClip(unit, clip, true, 0.12, 1.08);
        const dur = act ? Math.min(1.25, act.getClip().duration / 1.08) : 0.70;
        unit.lockTimer = dur * 0.72;
        unit.cooldown = Math.max(dur * 0.85, unit.cd);

        const dmg = useSkill ? unit.skillDmg : unit.dmg;
        const origin = getEnemyAttackOrigin(unit);
        if (!targetBarricade && useSkill && unit.skillRange > 3.5 && unit.vfxProjColor) {
          spawnTimedVfx(unit.vfxGlb, origin, dir, { groundFlat: false, scale: 0.92 * unit.vfxScale, life: 0.42 });
          triggerFlashLight(origin, unit.vfxProjColor, 4.0, 0.08);
          audio.playMonsterAttack(false);
          const hitPt = target.group.position.clone().add(new THREE.Vector3(0, 1.15, 0));
          spawnProjectile(origin, hitPt, unit.vfxProjColor, 14.0, () => applyDamage(target, dmg, unit, 1.2));
        } else {
          const isSlam = (unit.vfxMode === 'ground_slam');
          unit.pendingHit = {
            kind: 'enemy_melee',
            timer: dur * 0.38,
            target,
            dmg,
            isSlam,
            attackBarricade: targetBarricade,
            maxDist: engageRange + 1.25,
          };
        }
      } else {
        lookAtDir(unit, targetBarricade ? new THREE.Vector3(-1, 0, 0) : dir, dt);
        playClip(unit, unit.anims.idle, false, 0.16);
      }
      return;
    }

    // Survivor AI
    const rageMult = rageTimer > 0 ? 1.75 : 1.0;
    const rageDmgMult = rageTimer > 0 ? 1.25 : 1.0;
    const { target, dist } = nearestLivingOpponent(unit);
    if (!target) {
      lookAtDir(unit, new THREE.Vector3(1, 0, 0), dt);
      playClip(unit, unit.anims.aim || unit.anims.idle, false, 0.20);
      return;
    }

    const dir = new THREE.Vector3(target.group.position.x - unit.group.position.x, 0, target.group.position.z - unit.group.position.z);
    if (dir.lengthSq() > 1e-6) dir.normalize();

    if (unit.weaponClass === 'melee' && dist > unit.range && target.group.position.x < 3.6) {
      const moveSpd = 2.65;
      const moveClip = unit.anims.run || unit.anims.walk;
      const clipDur = (unit.clipsByName[moveClip]?.duration) || 1.0;
      const clipScale = THREE.MathUtils.clamp(((moveSpd * clipDur) / 1.35) * unit.animJitter, 0.75, 1.85);
      lookAtDir(unit, dir, dt);
      unit.group.position.addScaledVector(dir, moveSpd * dt);
      playClip(unit, moveClip, false, 0.14, clipScale);
    } else if (dist <= unit.range && unit.cooldown <= 0) {
      lookAtDir(unit, dir, dt);
      unit.attackCount++;
      const isHeavyMelee = (unit.weaponClass === 'melee') && (unit.attackCount % 2 === 0) && Boolean(unit.anims.skill);
      const atkClip = isHeavyMelee ? unit.anims.skill : unit.anims.attack;
      const act = playClip(unit, atkClip, true, 0.10, (unit.weaponClass === 'melee' ? 1.15 : 1.20) * Math.min(1.45, rageMult));
      const rawDur = act ? act.getClip().duration : 0.45;
      const dur = unit.weaponClass === 'melee' ? Math.min(0.95, rawDur / 1.15) : Math.min(0.36, rawDur * 0.62);
      unit.lockTimer = dur * 0.55;
      unit.cooldown = unit.cd / rageMult;

      const muz = getMuzzleWorldPos(unit);
      const aimPt = target.group.position.clone().add(new THREE.Vector3(0, target.height * 0.55, 0));
      const finalDmg = Math.round(unit.dmg * rageDmgMult);

      if (unit.weaponClass === 'melee') {
        unit.pendingHit = {
          kind: 'melee_surv',
          timer: dur * 0.36,
          target,
          dmg: isHeavyMelee ? Math.round(finalDmg * 1.28) : finalDmg,
          push: isHeavyMelee ? 2.6 : 1.5,
        };
      } else {
        spawnTimedVfx(`../output/vfx/vfx_${unit.vfxId}.glb`, muz, dir, { groundFlat: false, scale: 1.0, life: 0.16 });
        triggerFlashLight(muz, unit.weaponClass === 'bow' ? 0xf87171 : 0xffcc66, unit.weaponClass === 'bow' ? 2.2 : 5.2, 0.06);
        audio.playGun(unit.weaponClass);
        const pColor = unit.weaponClass === 'bow' ? 0xf87171 : (rageTimer > 0 ? 0xfacc15 : 0xffe680);
        spawnProjectile(muz, aimPt, pColor, unit.weaponClass === 'bow' ? 21.0 : 34.0, () => {
          applyDamage(target, finalDmg, unit, unit.weaponClass === 'bow' ? 0.9 : 0.4);
        });
      }
    } else {
      lookAtDir(unit, dir, dt);
      playClip(unit, unit.anims.aim || unit.anims.idle, false, 0.16);
    }
  }

  // Dramatic focus & gift spectacle methods
  function triggerDramaticFocus(worldPos, durationSec = 0.95, slowMo = 0.42) {
    dramaticFocus = {
      targetPos: worldPos.clone(),
      timer: durationSec,
      maxTimer: durationSec,
    };
    slowMoScale = slowMo;
    slowMoTimer = Math.min(0.55, durationSec * 0.65);
  }

  function triggerHealPulse({ amount = 35, shieldSec = 0, repairFlash = false } = {}) {
    const aliveSurvs = units.filter((u) => u.team === 'survivor' && !u.dead);
    if (shieldSec > 0) squadShieldTimer = Math.max(squadShieldTimer, shieldSec);
    for (const s of aliveSurvs) {
      const healed = Math.min(s.maxHp - s.hp, amount);
      s.hp = Math.min(s.maxHp, s.hp + amount);
      spawnExpandingRing(s.group.position, shieldSec > 0 ? 0x38bdf8 : 0x22c55e, 0.35, 1.55, 0.50, 0.85);
      if (healed > 0) {
        spawnFloatingText(s.group.position.clone().add(new THREE.Vector3(0, 2.05, 0)), `+${Math.round(healed)} HP`, '#4ade80', 13);
      }
    }
    if (repairFlash) {
      spawnExpandingRing(new THREE.Vector3(BARRICADE_X + 0.3, 0.04, 0), 0x38bdf8, 0.8, 3.2, 0.60, 0.85);
      spawnFloatingText(new THREE.Vector3(BARRICADE_X + 0.3, 2.2, 0), '🛡️ REPAIR +8%', '#38bdf8', 14);
    }
    audio.playHealPulse();
  }

  function triggerRageAura(durationSec = 7.0) {
    rageTimer = Math.max(rageTimer, durationSec);
    spawnExpandingRing(new THREE.Vector3(-3.0, 0.04, 0), 0xfacc15, 0.6, 3.6, 0.65, 0.90);
    spawnFloatingText(new THREE.Vector3(-3.0, 2.5, 0), '🔥 FRENZY 2x FIRE RATE!', '#facc15', 14);
    audio.playUpgradeFanfare();
  }

  async function triggerSupplyDrop(ownerName, onLanded) {
    try {
      const gltf = await loadGLB(ENV_PATHS.supplyCrate);
      const crate = SkeletonUtils.clone(gltf.scene);
      prepShadows(crate, 1.35, false);
      crate.position.set(-1.6, 13.5, 0.1);
      scene.add(crate);

      const beaconMat = new THREE.MeshBasicMaterial({
        color: 0xfacc15, transparent: true, opacity: 0.42, blending: THREE.AdditiveBlending, depthWrite: false,
      });
      const beacon = new THREE.Mesh(new THREE.CylinderGeometry(0.55, 0.65, 15.0, 12, 1, true), beaconMat);
      beacon.position.set(-1.6, 7.5, 0.1);
      scene.add(beacon);

      triggerDramaticFocus(new THREE.Vector3(-1.6, 1.2, 0.1), 1.15, 0.55);

      let landed = false;
      transientProps.push({
        mesh: crate, age: 0, maxAge: 4.0,
        onUpdate(t, dt) {
          if (!landed) {
            crate.position.y -= 14.5 * dt;
            crate.rotation.y += 1.6 * dt;
            if (crate.position.y <= 0.0) {
              crate.position.y = 0.0;
              crate.rotation.y = 0.25;
              landed = true;
              spawnExpandingRing(crate.position, 0xfacc15, 0.5, 3.5, 0.65, 0.92);
              spawnBurstParticles(crate.position.clone().add(new THREE.Vector3(0, 0.4, 0)), null, [0xfacc15, 0xfef08a, 0x38bdf8], 16, 1.1, false);
              triggerFlashLight(crate.position.clone().add(new THREE.Vector3(0, 1.4, 0)), 0xfacc15, 7.0, 0.25);
              cameraShake = Math.max(cameraShake, 0.16);
              if (onLanded) onLanded();
            }
          } else {
            beaconMat.opacity = Math.max(0, 0.42 * (1 - t * 1.4));
            if (t > 0.78) {
              const s = Math.max(0.05, 1 - (t - 0.78) / 0.22);
              crate.scale.setScalar(s);
            }
          }
        },
        onDone() {
          scene.remove(beacon);
          beacon.geometry.dispose();
          beaconMat.dispose();
        },
      });
    } catch (err) {
      console.warn('Supply crate error:', err);
      if (onLanded) onLanded();
    }
  }

  function triggerAirstrike(ownerName) {
    // Switch out of dark blackout storm when Sultan drops Money Gun Airstrike
    if (stormTemporaryTimer > 0) {
      stormTemporaryTimer = 0;
      applyWeatherPreset(baseWeatherId, false);
    }

    audio.playAirstrike();
    triggerDramaticFocus(new THREE.Vector3(1.8, 1.0, 0), 1.35, 0.40);

    const aliveEnm = units.filter((u) => u.team === 'enemy' && !u.dead);
    const strikes = [];
    for (let i = 0; i < 6; i++) {
      const targetUnit = aliveEnm.length > 0 ? aliveEnm[i % aliveEnm.length] : null;
      const tx = targetUnit
        ? THREE.MathUtils.clamp(targetUnit.group.position.x + (Math.random() - 0.5) * 1.4, -2.5, 8.0)
        : (-1.0 + i * 1.4);
      const tz = targetUnit
        ? THREE.MathUtils.clamp(targetUnit.group.position.z + (Math.random() - 0.5) * 1.2, -2.3, 2.3)
        : ((Math.random() - 0.5) * 3.6);
      strikes.push({ x: tx, z: tz, delay: 0.14 + i * 0.16 });
    }

    for (const st of strikes) {
      const ringMat = new THREE.MeshBasicMaterial({
        color: 0xff3b30, side: THREE.DoubleSide, transparent: true, opacity: 0.85, depthWrite: false,
      });
      const ring = new THREE.Mesh(dustRingGeo, ringMat);
      ring.rotation.x = -Math.PI / 2;
      ring.position.set(st.x, 0.03, st.z);
      ring.scale.setScalar(2.4);
      scene.add(ring);

      const rocketMat = new THREE.MeshBasicMaterial({ color: 0xffd166 });
      const rocket = new THREE.Mesh(new THREE.CylinderGeometry(0.10, 0.18, 1.2, 8), rocketMat);
      rocket.position.set(st.x, 18.0, st.z);
      scene.add(rocket);

      let detonated = false;
      transientProps.push({
        mesh: rocket, age: 0, maxAge: st.delay + 0.95,
        onUpdate(t, dt, rawElapsed) {
          if (rawElapsed < st.delay) {
            ring.scale.setScalar(2.2 + 0.4 * Math.sin(rawElapsed * 22));
            return;
          }
          if (!detonated) {
            rocket.position.y -= 36.0 * dt;
            if (rocket.position.y <= 0.15) {
              detonated = true;
              rocket.visible = false;
              ring.visible = false;
              const hitPos = new THREE.Vector3(st.x, 0.25, st.z);
              spawnExpandingRing(hitPos, 0xff7b1c, 0.6, 5.2, 0.52, 0.95);
              spawnBurstParticles(hitPos, null, [0xff5400, 0xffb703, 0x334155], 16, 1.45, false);
              triggerFlashLight(hitPos.clone().add(new THREE.Vector3(0, 1.6, 0)), 0xff9e2c, 9.5, 0.18);
              cameraShake = Math.max(cameraShake, 0.26);

              // Massive AoE blast damage to all enemies within radius 3.4m
              for (const u of units) {
                if (u.team !== 'enemy' || u.dead) continue;
                const d = Math.hypot(u.group.position.x - st.x, u.group.position.z - st.z);
                if (d <= 3.5) {
                  const blastDmg = u.isBoss ? 220 : 320;
                  applyDamage(u, blastDmg, null, 2.5, true);
                }
              }
            }
          }
        },
        onDone() {
          scene.remove(ring);
          ringMat.dispose();
          rocket.geometry.dispose();
          rocketMat.dispose();
        },
      });
    }
  }

  function triggerStormCurse(durationSec = 16.0) {
    stormTemporaryTimer = Math.min(24.0, Math.max(stormTemporaryTimer, durationSec));
    applyWeatherPreset('storm_rain', true);
    audio.playBossHorn();
    cameraShake = Math.max(cameraShake, 0.12);
    spawnFloatingText(new THREE.Vector3(0.5, 2.8, 0), '⛈️ BADAI BLACKOUT!', '#93c5fd', 15);
  }

  function resetUnitsAndFx() {
    clearDeathFx();
    for (const u of units) disposeUnit(u);
    units.length = 0;
    for (const v of activeVfx) scene.remove(v.mesh);
    activeVfx.length = 0;
    for (const p of activeProjectiles) scene.remove(p.mesh);
    activeProjectiles.length = 0;
    for (const fl of floatLabels) fl.el.remove();
    floatLabels.length = 0;
    for (const tp of transientProps) {
      scene.remove(tp.mesh);
      if (tp.onDone) tp.onDone();
    }
    transientProps.length = 0;
    rageTimer = 0;
    squadShieldTimer = 0;
    stormTemporaryTimer = 0;
    dramaticFocus = null;
    slowMoScale = 1.0;
    slowMoTimer = 0;
    cameraShake = 0;
    hitStopTimer = 0;
    applyWeatherPreset(baseWeatherId, false);
    setBarricadeVisual(1.0);
  }

  async function initEnvironment() {
    applyWeatherPreset(baseWeatherId, false);

    // Load Apocalypse Street diorama
    const streetGltf = await loadGLB(ENV_PATHS.streetScene);
    const envScene = streetGltf.scene.clone(true);
    envScene.traverse((o) => {
      if (o.isMesh || o.isSkinnedMesh) {
        const nm = o.name || (o.parent ? o.parent.name : '');
        const noCast = nm.includes('Env_DistantSkyline') || nm.includes('Env_BaseEarth') || nm.includes('Env_WetPuddles');
        o.castShadow = !noCast;
        o.receiveShadow = true;
        o.frustumCulled = false;
        const mats = Array.isArray(o.material) ? o.material : [o.material];
        for (const mt of mats) {
          if (mt && mt.name) {
            envMaterialRefs[mt.name] = mt;
            if (mt.name !== 'Mat_Env_PuddleWet' && mt.name !== 'Mat_Env_GlassBroken' && 'envMapIntensity' in mt) {
              mt.envMapIntensity = 0.70;
            }
          }
        }
      }
    });
    envGroup.add(envScene);

    // Clone two sandbag barricades across the lane at BARRICADE_X
    try {
      const sbGltf = await loadGLB(ENV_PATHS.sandbagBarricade);
      for (const zPos of [-1.45, 1.45]) {
        const sb = sbGltf.scene.clone(true);
        prepShadows(sb, 0.85, false);
        sb.rotation.y = Math.PI * 0.5;
        sb.position.set(0, 0, zPos);
        barricadeGroup.add(sb);
      }
    } catch (err) {
      console.warn('Sandbag load warning:', err);
    }

    applyWeatherPreset(baseWeatherId, false);
  }

  // Main Animation & Render Loop
  let prevTimeMs = performance.now();
  let fpsTimer = 0;
  let fpsFrames = 0;
  let currentFps = 60;
  let rafId = 0;
  const externalTickCallbacks = [];

  function animate() {
    rafId = requestAnimationFrame(animate);
    const nowMs = performance.now();
    const rawDt = Math.min(0.05, (nowMs - prevTimeMs) * 0.001);
    prevTimeMs = nowMs;

    fpsFrames++;
    fpsTimer += rawDt;
    if (fpsTimer >= 0.5) {
      currentFps = Math.round(fpsFrames / fpsTimer);
      fpsFrames = 0;
      fpsTimer = 0;
    }

    if (hitStopTimer > 0) hitStopTimer = Math.max(0, hitStopTimer - rawDt);
    if (slowMoTimer > 0) {
      slowMoTimer = Math.max(0, slowMoTimer - rawDt);
      if (slowMoTimer <= 0) slowMoScale = 1.0;
    }
    const simDt = (paused || hitStopTimer > 0) ? 0.0 : rawDt * slowMoScale;

    if (manualOrbitPause > 0) manualOrbitPause = Math.max(0, manualOrbitPause - rawDt);
    if (rageTimer > 0 && simDt > 0) rageTimer = Math.max(0, rageTimer - simDt);
    if (squadShieldTimer > 0 && simDt > 0) squadShieldTimer = Math.max(0, squadShieldTimer - simDt);
    if (stormTemporaryTimer > 0 && simDt > 0) {
      stormTemporaryTimer -= simDt;
      if (stormTemporaryTimer <= 0) {
        stormTemporaryTimer = 0;
        applyWeatherPreset(baseWeatherId, false);
      }
    }

    for (const fn of externalTickCallbacks) fn(simDt, rawDt);

    // Update units + cleanup sunken corpses
    for (let i = units.length - 1; i >= 0; i--) {
      const u = units[i];
      updateUnitAI(u, simDt);
      if (u.dead && u.deadTimer > 5.4 && !u.corpseCleaned) {
        u.corpseCleaned = true;
        disposeUnit(u);
        units.splice(i, 1);
      }
    }
    resolveUnitSeparation(simDt);

    // Death burst & decals
    for (let i = pendingDeathImpacts.length - 1; i >= 0; i--) {
      const imp = pendingDeathImpacts[i];
      if (simDt > 0) imp.timer -= simDt;
      if (imp.timer <= 0) {
        pendingDeathImpacts.splice(i, 1);
        if (!imp.unit.dead) continue;
        const pos = new THREE.Vector3(
          imp.unit.group.position.x + imp.fwd.x * imp.shift,
          0.018,
          imp.unit.group.position.z + imp.fwd.z * imp.shift
        );
        spawnExpandingRing(pos, imp.theme.dustColor || 0x9ca3af, 0.45 * imp.theme.dustScale, 2.25 * imp.theme.dustScale, 0.46, 0.56);
        spawnBurstParticles(pos.clone().setY(0.10), null, [imp.theme.dustColor || 0x9ca3af, 0x64748b], 7, 0.85, true);
        cameraShake = Math.max(cameraShake, imp.theme.shake);
        audio.playDeathThud(imp.theme.shake);
      }
    }

    for (let i = deathParticles.length - 1; i >= 0; i--) {
      const dp = deathParticles[i];
      dp.life -= simDt;
      if (dp.life <= 0) {
        scene.remove(dp.mesh);
        dp.mesh.material.dispose();
        deathParticles.splice(i, 1);
        continue;
      }
      if (simDt > 0) {
        dp.vy -= (dp.lowDust ? 4.2 : 14.5) * simDt;
        dp.mesh.position.x += dp.vx * simDt;
        dp.mesh.position.y += dp.vy * simDt;
        dp.mesh.position.z += dp.vz * simDt;
        dp.mesh.rotation.x += dp.rx * simDt;
        dp.mesh.rotation.y += dp.ry * simDt;
        if (dp.mesh.position.y < 0.032) {
          dp.mesh.position.y = 0.032;
          dp.vy = Math.abs(dp.vy) * 0.24;
          dp.vx *= 0.52; dp.vz *= 0.52;
        }
        const frac = dp.life / dp.maxLife;
        if (dp.lowDust) {
          dp.mesh.material.opacity = 0.72 * frac;
        } else if (frac < 0.28) {
          dp.mesh.scale.setScalar(dp.baseScale * Math.max(0.05, frac / 0.28));
        }
      }
    }

    for (let i = deathDecals.length - 1; i >= 0; i--) {
      const dd = deathDecals[i];
      if (simDt > 0) dd.age += simDt;
      if (dd.kind === 'puddle') {
        const p = Math.min(1.0, dd.age / dd.growDur);
        const ease = 1.0 - Math.pow(1.0 - p, 3.0);
        dd.mesh.scale.setScalar(0.22 + (dd.targetScale - 0.22) * ease);
      } else {
        const p = Math.min(1.0, dd.age / dd.maxLife);
        dd.mesh.scale.setScalar(dd.startScale + (dd.endScale - dd.startScale) * p);
        dd.mesh.material.opacity = dd.baseOpacity * (1.0 - p);
        if (dd.age >= dd.maxLife) {
          scene.remove(dd.mesh);
          dd.mesh.material.dispose();
          deathDecals.splice(i, 1);
        }
      }
    }

    for (let i = transientProps.length - 1; i >= 0; i--) {
      const tp = transientProps[i];
      tp.age += rawDt;
      const frac = Math.min(1.0, tp.age / tp.maxAge);
      if (tp.onUpdate) tp.onUpdate(frac, rawDt, tp.age);
      if (tp.age >= tp.maxAge) {
        scene.remove(tp.mesh);
        if (tp.onDone) tp.onDone();
        transientProps.splice(i, 1);
      }
    }

    for (let i = activeVfx.length - 1; i >= 0; i--) {
      const v = activeVfx[i];
      v.life -= rawDt;
      if (v.life <= 0) {
        scene.remove(v.mesh);
        activeVfx.splice(i, 1);
      }
    }

    for (let i = activeProjectiles.length - 1; i >= 0; i--) {
      const p = activeProjectiles[i];
      const step = p.speed * simDt;
      p.mesh.position.addScaledVector(p.dir, step);
      p.distLeft -= step;
      if (p.distLeft <= 0) {
        scene.remove(p.mesh);
        p.mesh.geometry.dispose();
        p.mesh.material.dispose();
        activeProjectiles.splice(i, 1);
        if (p.onImpact) p.onImpact();
      }
    }

    // Animate Barricade critical pulse
    const tNow = nowMs * 0.001;
    if (barricadeHpRatio < 0.28 && barricadeHpRatio > 0.001) {
      const flash = 0.5 + 0.5 * Math.sin(tNow * 10.5);
      shieldMat.opacity = 0.16 + 0.34 * flash;
      beaconOrbMat.emissiveIntensity = 1.2 + 2.4 * flash;
      barricadeSparkCooldown -= rawDt;
      if (barricadeSparkCooldown <= 0) {
        barricadeSparkCooldown = 0.65;
        spawnTimedVfx(VFX_PATHS.spark, new THREE.Vector3(BARRICADE_X + 0.25, 0.9, (Math.random() - 0.5) * 3.0), new THREE.Vector3(0, 1, 0), { scale: 0.9, life: 0.22 });
      }
    } else {
      shieldMat.opacity = squadShieldTimer > 0 ? 0.36 : 0.22;
      beaconOrbMat.emissiveIntensity = 1.8 + 0.4 * Math.sin(tNow * 3.0);
    }
    beaconOrb.rotation.y += rawDt * 1.4;

    // Atmosphere & Weather FX
    skyUniforms.uTime.value = tNow;
    skyDome.position.set(camera.position.x, 0, camera.position.z);
    const wPreset = WEATHER_PRESETS[activeWeatherId] || WEATHER_PRESETS.apoc_sunset;
    const fBase = wPreset.fireInt;
    const flickW = fBase * (0.86 + 0.14 * Math.sin(tNow * 8.2));
    const flickE = fBase * (0.86 + 0.14 * Math.cos(tNow * 8.9));
    fireLightW.intensity = flickW;
    fireLightE.intensity = flickE;
    fireHaloW.material.opacity = wPreset.fireHaloAlpha * (0.78 + 0.22 * (flickW / Math.max(0.2, fBase)));
    fireHaloE.material.opacity = wPreset.fireHaloAlpha * (0.78 + 0.22 * (flickE / Math.max(0.2, fBase)));

    const sirenWave = Math.sin(tNow * 6.4);
    const sirenPeak = (activeWeatherId === 'apoc_sunset' || activeWeatherId === 'storm_rain') ? 0.45 : 0.18;
    policeHaloRed.material.opacity = sirenPeak * (0.14 + 0.86 * Math.pow(Math.max(0, sirenWave), 1.6));
    policeHaloBlue.material.opacity = sirenPeak * (0.14 + 0.86 * Math.pow(Math.max(0, -sirenWave), 1.6));

    if (wPreset.lightning) {
      lightningState.timer -= rawDt;
      if (lightningState.timer <= 0) {
        lightningState.flash = 1.0;
        lightningState.timer = 4.2 + Math.random() * 5.0;
      }
      if (lightningState.flash > 0.001) {
        lightningState.flash = Math.max(0.0, lightningState.flash - rawDt * 3.0);
        const fp = Math.max(0, lightningState.flash);
        skyUniforms.uFlash.value = fp;
        rimLight.intensity = wPreset.rimInt + fp * 2.2;
        hemi.intensity = wPreset.hemiInt + fp * 0.8;
      } else {
        skyUniforms.uFlash.value = 0;
        rimLight.intensity = wPreset.rimInt;
        hemi.intensity = wPreset.hemiInt;
      }
    }

    const smArr = smokeGeo.attributes.position.array;
    for (let i = 0; i < SMOKE_COUNT; i++) {
      const sp = smokeMeta[i];
      sp.age += rawDt;
      if (sp.age >= sp.maxAge) sp.age = 0;
      const p = sp.age / sp.maxAge;
      const em = sp.emitter;
      smArr[i * 3 + 0] = em.x + sp.vx * sp.age + Math.sin(tNow * 1.4 + p * 4.0) * 0.22 * p;
      smArr[i * 3 + 1] = em.y + sp.age * 1.1;
      smArr[i * 3 + 2] = em.z + sp.vz * sp.age;
    }
    smokeGeo.attributes.position.needsUpdate = true;

    if (rainLines.visible) {
      const arr = rainGeo.attributes.position.array;
      for (let i = 0; i < RAIN_COUNT; i++) {
        const s3 = i * 3;
        let rx = rainSeeds[s3] + 2.8 * rawDt;
        let ry = rainSeeds[s3 + 1] - 20.0 * rawDt;
        let rz = rainSeeds[s3 + 2] + 0.7 * rawDt;
        if (ry < 0) {
          ry = 13.5 + Math.random() * 1.5;
          rx = (Math.random() - 0.5) * 38;
          rz = (Math.random() - 0.5) * 22;
        }
        if (rx > 19) rx -= 38;
        rainSeeds[s3] = rx; rainSeeds[s3 + 1] = ry; rainSeeds[s3 + 2] = rz;
        const i6 = i * 6;
        arr[i6] = rx; arr[i6 + 1] = ry; arr[i6 + 2] = rz;
        arr[i6 + 3] = rx - 0.10; arr[i6 + 4] = ry + 0.78; arr[i6 + 5] = rz - 0.03;
      }
      rainGeo.attributes.position.needsUpdate = true;
    }

    const drawN = Math.min(PARTICLE_MAX, wPreset.particleCount);
    const pArr = partGeo.attributes.position.array;
    for (let i = 0; i < drawN; i++) {
      const m = partMeta[i];
      const i3 = i * 3;
      pArr[i3 + 1] += (i % 3 === 0 ? m.spdY * 0.7 : -m.spdY * 0.4) * rawDt;
      pArr[i3] += m.spdX * rawDt;
      if (pArr[i3] > 16) pArr[i3] = -16;
      if (pArr[i3 + 1] < 0.05) pArr[i3 + 1] = 5.4;
      if (pArr[i3 + 1] > 6.2) pArr[i3 + 1] = 0.4;
    }
    partGeo.attributes.position.needsUpdate = true;

    // Smart 9:16 Director Camera
    if (manualOrbitPause <= 0) {
      const aliveEnm = units.filter((u) => u.team === 'enemy' && !u.dead);
      const hasBoss = aliveEnm.some((e) => e.isBoss);

      if (dramaticFocus && dramaticFocus.timer > 0) {
        dramaticFocus.timer -= rawDt;
        const tx = THREE.MathUtils.clamp(dramaticFocus.targetPos.x, -4.5, 6.0);
        const tz = dramaticFocus.targetPos.z;
        controls.target.lerp(new THREE.Vector3(tx, 1.35, tz * 0.4), 0.10);
        camera.position.lerp(new THREE.Vector3(tx - 0.8, 6.4, 15.0), 0.08);
      } else if (camMode === 'barricade') {
        controls.target.lerp(new THREE.Vector3(-3.0, 1.1, -0.2), 0.08);
        camera.position.lerp(new THREE.Vector3(-3.6, 7.6, 15.8), 0.08);
      } else if (camMode === 'frontline') {
        controls.target.lerp(new THREE.Vector3(0.4, 1.1, -0.2), 0.08);
        camera.position.lerp(new THREE.Vector3(-0.2, 6.9, 15.2), 0.08);
      } else if (camMode === 'wide') {
        controls.target.lerp(new THREE.Vector3(0.0, 1.0, -0.4), 0.08);
        camera.position.lerp(new THREE.Vector3(0.0, 10.2, 22.5), 0.08);
      } else {
        // Default 'auto': keep both Extraction Barricade (-5.0) & enemy frontline visible inside 9:16 portrait frame
        let enemyMinX = 3.5;
        if (aliveEnm.length > 0) {
          enemyMinX = aliveEnm.reduce((mn, e) => Math.min(mn, e.group.position.x), 7.5);
        }
        const focusX = THREE.MathUtils.clamp(-1.05 + Math.max(0, enemyMinX + 1.5) * 0.16, -1.35, -0.15);
        const zPull = hasBoss ? 22.8 : 21.4;
        const yPull = hasBoss ? 9.8 : 9.0;
        controls.target.lerp(new THREE.Vector3(focusX, 1.05, -0.35), 0.05);
        camera.position.lerp(new THREE.Vector3(focusX - 0.15, yPull, zPull), 0.05);
      }
    }

    if (combatFlash.timer > 0) {
      combatFlash.timer = Math.max(0, combatFlash.timer - rawDt);
      combatFlashLight.intensity = combatFlash.maxInt * (combatFlash.timer / combatFlash.dur);
    } else if (combatFlashLight.intensity > 0) {
      combatFlashLight.intensity = 0;
    }

    controls.update();

    // Exact 9:16 stage-container 3D -> 2D projections (never window.innerWidth)
    const { w: stageW, h: stageH } = getStageSize();
    for (const u of units) {
      if (!u.hudEl) continue;
      if (u.dead && u.deadTimer > 1.8) {
        u.hudEl.style.display = 'none';
        continue;
      }
      let anchorH = u.height + 0.28;
      if (u.dead) anchorH = THREE.MathUtils.lerp(u.height + 0.25, 0.55, Math.min(1, u.deadTimer / 0.7));
      _tmpVec.copy(u.group.position).add(new THREE.Vector3(0, anchorH, 0)).project(camera);
      if (_tmpVec.z > 1 || _tmpVec.x < -1.12 || _tmpVec.x > 1.12 || _tmpVec.y < -1.1 || _tmpVec.y > 1.1) {
        u.hudEl.style.display = 'none';
      } else {
        u.hudEl.style.display = 'block';
        u.hudEl.style.left = `${(_tmpVec.x * 0.5 + 0.5) * stageW}px`;
        u.hudEl.style.top = `${(-_tmpVec.y * 0.5 + 0.5) * stageH}px`;
        u.hpFillEl.style.width = `${Math.max(0, (u.hp / u.maxHp) * 100)}%`;
      }
    }

    for (let i = floatLabels.length - 1; i >= 0; i--) {
      const fd = floatLabels[i];
      fd.life -= rawDt;
      fd.pos.y += 1.15 * rawDt;
      if (fd.life <= 0) {
        fd.el.remove();
        floatLabels.splice(i, 1);
        continue;
      }
      _tmpVec.copy(fd.pos).project(camera);
      fd.el.style.left = `${(_tmpVec.x * 0.5 + 0.5) * stageW}px`;
      fd.el.style.top = `${(-_tmpVec.y * 0.5 + 0.5) * stageH}px`;
      fd.el.style.opacity = `${Math.max(0, fd.life / fd.maxLife)}`;
    }

    if (cameraShake > 0.002) {
      _shakeVec.set((Math.random() - 0.5) * cameraShake, (Math.random() - 0.5) * cameraShake * 0.65, (Math.random() - 0.5) * cameraShake);
      camera.position.add(_shakeVec);
      controls.target.addScaledVector(_shakeVec, 0.35);
      cameraShake = Math.max(0, cameraShake - rawDt * 0.85);
    } else {
      _shakeVec.set(0, 0, 0);
      cameraShake = 0;
    }

    if (bloomEnabled) composer.render();
    else renderer.render(scene, camera);

    if (_shakeVec.lengthSq() > 0) {
      camera.position.sub(_shakeVec);
      controls.target.addScaledVector(_shakeVec, -0.35);
    }
  }

  animate();

  return {
    initEnvironment,
    onTick(fn) {
      externalTickCallbacks.push(fn);
    },
    setPaused(val) {
      paused = Boolean(val);
    },
    isPaused() {
      return paused;
    },
    setCameraMode(mode) {
      camMode = mode;
      manualOrbitPause = 0;
    },
    setWeather(weatherId) {
      stormTemporaryTimer = 0;
      applyWeatherPreset(weatherId, false);
    },
    setBloom(val) {
      bloomEnabled = Boolean(val);
      syncBloomSkyMaterial();
    },
    setBarricadeVisual,
    spawnSurvivor,
    upgradeSurvivor,
    spawnEnemy,
    triggerHealPulse,
    triggerRageAura,
    triggerSupplyDrop,
    triggerAirstrike,
    triggerStormCurse,
    resetUnitsAndFx,
    getUnits() {
      return units;
    },
    getStats() {
      let survAlive = 0, enmAlive = 0;
      let topBoss = null;
      for (const u of units) {
        if (u.dead) continue;
        if (u.team === 'survivor') survAlive++;
        else {
          enmAlive++;
          if (u.isBoss && (!topBoss || u.hp > topBoss.hp)) topBoss = u;
        }
      }
      return {
        fps: currentFps,
        survAlive,
        enmAlive,
        topBoss,
        rageActive: rageTimer > 0,
        shieldActive: squadShieldTimer > 0,
        stormActive: stormTemporaryTimer > 0,
      };
    },
    destroy() {
      cancelAnimationFrame(rafId);
      resizeObs.disconnect();
      window.removeEventListener('resize', handleResize);
      renderer.dispose();
    },
  };
}
