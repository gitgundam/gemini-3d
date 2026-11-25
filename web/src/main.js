import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

/**
 * Coordinate note (glTF Y-up export from Blender Z-up):
 *   Blender (X, Y, Z) -> Three.js (X, Z, -Y)
 * So:
 *   Three.x = Blender X  (West = -3..0, Corridor = 0..2.4, Desks = 2.6..8.6, East window = 9.4)
 *   Three.y = Blender Z  (Floor = 0, Eye height = 1.58, Ceiling = 3.15)
 *   Three.z = -Blender Y (South "夯爆了" = 0, Pantry = -0.5..-5.2, Row1 = -7.6, Row2/UserDesk = -10.2, North = -23.0)
 */
const B2T = (bx, by, bz) => new THREE.Vector3(bx, bz, -by);

// ---------------------------------------------------------------------------
// 1. Renderer, Scene & Dual Cameras (True Ortho Diorama + Eye-Level Walk-In)
// ---------------------------------------------------------------------------
const canvas = document.getElementById('scene-canvas');
const renderer = new THREE.WebGLRenderer({
  canvas,
  antialias: true,
  powerPreference: 'high-performance',
});
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.NoToneMapping; // Crisp authentic pixel-art colors like Image #1!

const scene = new THREE.Scene();
const BG_ISO = new THREE.Color(0xf4f5f7);
const BG_WALK = new THREE.Color(0xdfe8f0);
scene.background = BG_ISO.clone();

// Isometric Orthographic Camera (exact Image #1 architectural diorama projection!)
const frustumSize = 21.5;
const aspect = window.innerWidth / window.innerHeight;
const orthoCam = new THREE.OrthographicCamera(
  (-frustumSize * aspect) / 2,
  (frustumSize * aspect) / 2,
  frustumSize / 2,
  -frustumSize / 2,
  -80,
  160
);
orthoCam.position.copy(B2T(24.5, -7.5, 19.5));

// First-Person Walk-In Perspective Camera
const walkCam = new THREE.PerspectiveCamera(62, aspect, 0.08, 120);
walkCam.position.copy(B2T(1.25, 7.0, 1.58));

let activeCamera = orthoCam;
let mode = 'iso'; // 'iso' | 'walk'

// Smooth OrbitControls for Diorama Mode
const orbit = new OrbitControls(orthoCam, canvas);
orbit.enableDamping = true;
orbit.dampingFactor = 0.08;
orbit.target.copy(B2T(3.8, 11.2, 0.7));
orbit.minZoom = 0.45;
orbit.maxZoom = 4.6;
orbit.maxPolarAngle = Math.PI * 0.485;
orbit.minPolarAngle = 0.15;
orbit.update();

// ---------------------------------------------------------------------------
// 2. Studio & Interior Lighting (Warm Pastel Soft Shadows like Image #1!)
// ---------------------------------------------------------------------------
const hemiLight = new THREE.HemisphereLight(0xfffdf8, 0xcbd3df, 1.05);
scene.add(hemiLight);

const sunLight = new THREE.DirectionalLight(0xfff7ea, 1.25);
sunLight.position.copy(B2T(22, -6, 28));
sunLight.castShadow = true;
sunLight.shadow.mapSize.set(2048, 2048);
sunLight.shadow.camera.left = -20;
sunLight.shadow.camera.right = 20;
sunLight.shadow.camera.top = 20;
sunLight.shadow.camera.bottom = -20;
sunLight.shadow.camera.near = 2;
sunLight.shadow.camera.far = 70;
sunLight.shadow.bias = -0.0005;
sunLight.shadow.normalBias = 0.025;
sunLight.target.position.copy(B2T(4.0, 11.5, 0.0));
scene.add(sunLight);
scene.add(sunLight.target);

// Subtle cool opposite bounce fill so back faces stay crisp & legible
const fillLight = new THREE.DirectionalLight(0xdce8fa, 0.42);
fillLight.position.copy(B2T(-16, 26, 14));
scene.add(fillLight);

// Soft interior fill lights (boosted in Walk-In Mode when ceiling is ON!)
const interiorLightsGroup = new THREE.Group();
for (const [bx, by] of [
  [4.5, 3.0],
  [1.3, 9.0],
  [5.5, 10.2],
  [1.3, 15.0],
  [5.5, 15.4],
  [4.0, 21.0],
  [-1.5, 21.3],
]) {
  const pl = new THREE.PointLight(0xfffaf0, 0.0, 12, 1.4);
  pl.position.copy(B2T(bx, by, 2.65));
  interiorLightsGroup.add(pl);
}
scene.add(interiorLightsGroup);

// ---------------------------------------------------------------------------
// 3. Load Blender GLB + Apply Pixel-Art Nearest Filter & Crisp Ink Outlines!
// ---------------------------------------------------------------------------
const namedGroups = {};
const outlineLines = [];
const animatedChars = [];
const walkableFloors = [];

let showOutlines = true;
let showCeiling = false;
let showFrontWindows = false;
let showPins = true;

const inkLineMaterial = new THREE.LineBasicMaterial({
  color: 0x22252f,
  transparent: true,
  opacity: 0.78,
});

const loaderEl = document.getElementById('loader');
const loaderFill = document.getElementById('loader-fill');

const gltfLoader = new GLTFLoader();
gltfLoader.load(
  `${import.meta.env.BASE_URL}office_diorama.glb`,
  (gltf) => {
    const root = gltf.scene;
    scene.add(root);

    // Grab semantic groups exported from Blender
    for (const gName of [
      'ArchitectureGroup',
      'CutawayFrontGroup',
      'CeilingGroup',
      'HangingSignsGroup',
      'PantryGroup',
      'WorkstationsGroup',
      'UserDeskGroup',
      'HeroDetailsGroup',
      'CharactersGroup',
    ]) {
      const found = root.getObjectByName(gName);
      if (found) namedGroups[gName] = found;
    }

    // Collect characters for gentle idle living animation
    if (namedGroups.CharactersGroup) {
      for (const child of namedGroups.CharactersGroup.children) {
        animatedChars.push({
          obj: child,
          baseY: child.position.y,
          baseRotZ: child.rotation.z,
          baseRotY: child.rotation.y,
          phase: Math.random() * Math.PI * 2,
          isWalker: child.name.includes('Walk'),
          isRecliner: child.name.includes('Recliner'),
          baseZ: child.position.z,
        });
      }
    }

    // Traverse meshes: enforce CRISP nearest-neighbor pixel art + add Image #1 ink outlines!
    root.traverse((node) => {
      if (!node.isMesh) return;

      const mats = Array.isArray(node.material) ? node.material : [node.material];
      let isTransparentOrGlass = false;
      let isEmissiveOnly = false;

      for (const mat of mats) {
        if (!mat) continue;
        // Force razor-sharp nearest-neighbor pixel art on every texture!
        for (const mapKey of ['map', 'emissiveMap', 'alphaMap']) {
          const tex = mat[mapKey];
          if (tex) {
            tex.magFilter = THREE.NearestFilter;
            tex.minFilter = THREE.NearestFilter;
            tex.generateMipmaps = false;
            tex.anisotropy = 1;
            tex.needsUpdate = true;
          }
        }

        // Tactile illustrated matte finish (zero shiny plastic glare)
        if (typeof mat.roughness === 'number') {
          mat.roughness = Math.max(mat.roughness, 0.85);
        }
        if (typeof mat.metalness === 'number') {
          mat.metalness = Math.min(mat.metalness, 0.08);
        }

        const mName = mat.name || '';
        if (mName.includes('Pennant')) {
          mat.alphaTest = 0.45;
          mat.transparent = false;
          mat.depthWrite = true;
          mat.side = THREE.FrontSide;
          mat.needsUpdate = true;
        } else if (mName.includes('WuhanGlass') || mName.includes('GlassClear')) {
          mat.transparent = true;
          mat.depthWrite = false;
          mat.side = THREE.DoubleSide;
          mat.needsUpdate = true;
          isTransparentOrGlass = true;
        } else if (mName.includes('LedGlow')) {
          isEmissiveOnly = true;
        }
      }

      // Shadows
      const nName = node.name || '';
      const isFloor = nName.startsWith('Floor_') || nName.startsWith('Plinth_');
      node.receiveShadow = true;
      node.castShadow = !isFloor && !isTransparentOrGlass && !nName.startsWith('Ceiling_') && !nName.startsWith('Decal_');

      if (nName.startsWith('Floor_')) {
        walkableFloors.push(node);
      }

      // Crisp Image #1 Architectural Ink Outlines via EdgesGeometry!
      // Skip tiny casters, decals, glass panes, LED strips, and foliage leaves (keep outlines crisp, not noisy!)
      const skipOutline =
        isTransparentOrGlass ||
        isEmissiveOnly ||
        nName.includes('Wheel') ||
        nName.includes('Coil') ||
        nName.includes('Decal_') ||
        nName.includes('Pennant') ||
        nName.includes('Downlight') ||
        nName.includes('Wire') ||
        nName.includes('Baseboard') ||
        nName.includes('Mousepad') ||
        nName.includes('Soil');

      if (!skipOutline && node.geometry) {
        const edgesGeo = new THREE.EdgesGeometry(node.geometry, 28);
        const line = new THREE.LineSegments(edgesGeo, inkLineMaterial);
        line.renderOrder = 1;
        node.add(line);
        outlineLines.push(line);
      }
    });

    // Apply initial Diorama layer state
    applyLayerVisibility();

    // Hide loader completely
    loaderFill.style.width = '100%';
    setTimeout(() => {
      loaderEl.classList.add('fade-out');
      setTimeout(() => {
        loaderEl.style.display = 'none';
        window.__DIORAMA_READY__ = true;
      }, 380);
    }, 120);
  },
  (evt) => {
    if (evt.total > 0) {
      const pct = Math.min(95, Math.round((evt.loaded / evt.total) * 100));
      loaderFill.style.width = `${pct}%`;
    }
  },
  (err) => {
    console.error('Failed to load office_diorama.glb:', err);
    document.querySelector('.loader-title').textContent = '模型加载失败，请检查控制台';
  }
);

function applyLayerVisibility() {
  if (namedGroups.CeilingGroup) namedGroups.CeilingGroup.visible = showCeiling;
  if (namedGroups.HangingSignsGroup) namedGroups.HangingSignsGroup.visible = showCeiling;
  if (namedGroups.CutawayFrontGroup) namedGroups.CutawayFrontGroup.visible = showFrontWindows;
  for (const l of outlineLines) l.visible = showOutlines;

  // Adjust lighting smoothly when ceiling is on vs off
  const interiorPower = showCeiling ? 1.55 : 0.0;
  for (const pl of interiorLightsGroup.children) {
    pl.intensity = interiorPower;
  }
  hemiLight.intensity = showCeiling ? 1.25 : 1.05;

  // Sync UI chip active states
  document.getElementById('btn-toggle-outlines').classList.toggle('active', showOutlines);
  document.getElementById('btn-toggle-ceiling').classList.toggle('active', showCeiling);
  document.getElementById('btn-toggle-windows').classList.toggle('active', showFrontWindows);
  document.getElementById('btn-toggle-pins').classList.toggle('active', showPins);
  document.getElementById('pins-layer').classList.toggle('hidden', !showPins || mode === 'walk');
}

// ---------------------------------------------------------------------------
// 4. Landmark Pins & Quick-Jump Camera Bookmarks (Diorama + Walk-In!)
// ---------------------------------------------------------------------------
const SPOTS = {
  overview: {
    label: '全景微缩',
    preferredMode: 'iso',
    isoPos: B2T(24.5, -7.5, 19.5),
    isoTarget: B2T(3.8, 11.2, 0.7),
    isoZoom: 1.05,
    walkPos: B2T(1.3, 6.8, 1.58),
    walkLook: B2T(1.8, 16.0, 1.45),
  },
  hangbaole: {
    label: '🚩 夯爆了门 & 躺平同事',
    pinPos: B2T(2.5, 0.9, 2.35),
    preferredMode: 'walk',
    isoPos: B2T(15.0, -4.5, 10.5),
    isoTarget: B2T(3.5, 1.6, 1.0),
    isoZoom: 2.4,
    walkPos: B2T(5.2, 3.5, 1.54),
    walkLook: B2T(2.3, 1.2, 1.26),
  },
  pantry: {
    label: '☕ 茶水间',
    pinPos: B2T(2.6, 3.6, 2.55),
    preferredMode: 'walk',
    isoPos: B2T(15.0, -3.5, 11.0),
    isoTarget: B2T(3.6, 3.5, 1.0),
    isoZoom: 2.3,
    walkPos: B2T(5.0, 4.6, 1.56),
    walkLook: B2T(2.4, 3.4, 1.25),
  },
  honor: {
    label: '🏆 HONOR 25项软著',
    pinPos: B2T(0.2, 8.8, 2.65),
    preferredMode: 'walk',
    isoPos: B2T(14.5, 1.0, 11.0),
    isoTarget: B2T(1.6, 8.6, 1.3),
    isoZoom: 2.3,
    walkPos: B2T(2.0, 6.7, 1.56),
    walkLook: B2T(0.0, 9.2, 1.50),
  },
  mydesk: {
    label: '💻 我的工位',
    pinPos: B2T(7.65, 9.9, 1.65),
    preferredMode: 'walk',
    isoPos: B2T(16.5, 2.0, 9.0),
    isoTarget: B2T(7.65, 9.8, 0.9),
    isoZoom: 3.1,
    walkPos: B2T(7.35, 8.78, 1.54),
    walkLook: B2T(7.72, 9.95, 0.92),
  },
  corridor: {
    label: '🪴 绿萝矮柜长廊',
    pinPos: B2T(2.56, 14.0, 1.65),
    preferredMode: 'walk',
    isoPos: B2T(18.0, 2.0, 13.0),
    isoTarget: B2T(2.2, 13.5, 1.0),
    isoZoom: 1.7,
    walkPos: B2T(1.25, 7.6, 1.58),
    walkLook: B2T(1.8, 18.5, 1.45),
  },
  wuhan: {
    label: '🏢 武汉会议室',
    pinPos: B2T(-1.4, 21.3, 2.6),
    preferredMode: 'walk',
    isoPos: B2T(12.5, 11.0, 11.5),
    isoTarget: B2T(0.8, 21.0, 1.0),
    isoZoom: 2.1,
    walkPos: B2T(1.4, 18.8, 1.58),
    walkLook: B2T(-0.6, 21.5, 1.45),
  },
  tvcorner: {
    label: '📺 东北角 TV',
    pinPos: B2T(8.5, 22.0, 2.2),
    preferredMode: 'walk',
    isoPos: B2T(17.5, 12.0, 10.5),
    isoTarget: B2T(7.4, 21.2, 1.1),
    isoZoom: 2.2,
    walkPos: B2T(6.0, 19.3, 1.58),
    walkLook: B2T(8.5, 22.2, 1.38),
  },
};

// Create 3D Pin DOM elements
const pinsLayer = document.getElementById('pins-layer');
const pinEntries = [];
for (const [key, spot] of Object.entries(SPOTS)) {
  if (!spot.pinPos) continue;
  const el = document.createElement('button');
  el.className = 'pin-tag';
  el.textContent = spot.label;
  el.addEventListener('click', () => jumpToSpot(key, false));
  pinsLayer.appendChild(el);
  pinEntries.push({ el, worldPos: spot.pinPos, key });
}

// Smooth camera transition tween
let tween = null;
function startTween(config) {
  tween = { start: performance.now(), duration: config.duration || 650, ...config };
}

function setMode(newMode) {
  if (mode === newMode) return;
  mode = newMode;
  tween = null;

  document.getElementById('btn-mode-iso').classList.toggle('active', mode === 'iso');
  document.getElementById('btn-mode-walk').classList.toggle('active', mode === 'walk');
  document.getElementById('walk-hint').classList.toggle('hidden', mode !== 'walk');

  if (mode === 'iso') {
    activeCamera = orthoCam;
    orbit.enabled = true;
    scene.background = BG_ISO.clone();
    showCeiling = false;
    showFrontWindows = false;
  } else {
    activeCamera = walkCam;
    orbit.enabled = false;
    scene.background = BG_WALK.clone();
    showCeiling = true;
    showFrontWindows = true;
  }
  applyLayerVisibility();
}

// ---------------------------------------------------------------------------
// 5. First-Person Walk-In Controller (WASD + Mouse Drag Look + Click-to-Walk!)
// ---------------------------------------------------------------------------
let walkYaw = 0; // Radians around Y (0 = looking -Z / Blender +Y North!)
let walkPitch = -0.06;
const EYE_HEIGHT = 1.56;
const keysPressed = new Set();
let walkMoveTarget = null;

function setWalkLookAt(fromPos, targetPos) {
  walkCam.position.copy(fromPos);
  const dir = new THREE.Vector3().subVectors(targetPos, fromPos).normalize();
  walkYaw = Math.atan2(-dir.x, -dir.z);
  walkPitch = Math.asin(THREE.MathUtils.clamp(dir.y, -0.85, 0.85));
  applyWalkOrientation();
}

function applyWalkOrientation() {
  const euler = new THREE.Euler(walkPitch, walkYaw, 0, 'YXZ');
  walkCam.quaternion.setFromEuler(euler);
}

// Initialize walk camera facing down the corridor
setWalkLookAt(SPOTS.overview.walkPos, SPOTS.overview.walkLook);

// Drag-to-look & click-to-walk on canvas
let isDragging = false;
let dragMoved = 0;
let lastPointerX = 0;
let lastPointerY = 0;
const raycaster = new THREE.Raycaster();
const pointerNdc = new THREE.Vector2();

canvas.addEventListener('pointerdown', (e) => {
  if (mode !== 'walk') return;
  isDragging = true;
  dragMoved = 0;
  lastPointerX = e.clientX;
  lastPointerY = e.clientY;
});

window.addEventListener('pointermove', (e) => {
  if (mode !== 'walk' || !isDragging) return;
  const dx = e.clientX - lastPointerX;
  const dy = e.clientY - lastPointerY;
  lastPointerX = e.clientX;
  lastPointerY = e.clientY;
  dragMoved += Math.abs(dx) + Math.abs(dy);

  walkYaw -= dx * 0.0042;
  walkPitch = THREE.MathUtils.clamp(walkPitch - dy * 0.0036, -1.15, 0.95);
  applyWalkOrientation();
});

window.addEventListener('pointerup', (e) => {
  if (mode !== 'walk') return;
  if (isDragging && dragMoved < 6 && walkableFloors.length > 0) {
    // Short click on floor -> smoothly walk there!
    const rect = canvas.getBoundingClientRect();
    pointerNdc.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    pointerNdc.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(pointerNdc, walkCam);
    const hits = raycaster.intersectObjects(walkableFloors, false);
    if (hits.length > 0) {
      const pt = hits[0].point;
      walkMoveTarget = clampWalkPosition(new THREE.Vector3(pt.x, EYE_HEIGHT, pt.z));
    }
  }
  isDragging = false;
});

window.addEventListener('keydown', (e) => {
  if (e.code === 'Escape' && mode === 'walk') {
    setMode('iso');
    return;
  }
  keysPressed.add(e.code);
  if (['KeyW', 'KeyA', 'KeyS', 'KeyD', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.code)) {
    walkMoveTarget = null;
  }
});

window.addEventListener('keyup', (e) => {
  keysPressed.delete(e.code);
});

function clampWalkPosition(pos) {
  // Keep user cleanly inside the office interior boundaries!
  // Blender Y = -pos.z, Blender X = pos.x
  const by = THREE.MathUtils.clamp(-pos.z, 0.55, 22.45);
  let minBx = 0.35;
  if (by < 5.3) {
    minBx = 2.95; // Pantry counter boundary in South Bay
  } else if (by > 19.7) {
    minBx = -2.65; // Can step right into Wuhan Conference Room!
  }
  const bx = THREE.MathUtils.clamp(pos.x, minBx, 8.95);
  return new THREE.Vector3(bx, EYE_HEIGHT, -by);
}

// ---------------------------------------------------------------------------
// 6. Spot Navigation & UI Wiring
// ---------------------------------------------------------------------------
function highlightSpot(spotKey) {
  document.querySelectorAll('.spot-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.spot === spotKey);
  });
}

function jumpToSpot(spotKey, keepCurrentMode = true) {
  const spot = SPOTS[spotKey];
  if (!spot) return;
  highlightSpot(spotKey);

  if (spotKey === 'overview') {
    setMode('iso');
  } else if (!keepCurrentMode && spot.preferredMode) {
    setMode(spot.preferredMode);
  }

  walkMoveTarget = null;

  if (mode === 'iso') {
    startTween({
      type: 'iso',
      fromPos: orthoCam.position.clone(),
      toPos: spot.isoPos.clone(),
      fromTarget: orbit.target.clone(),
      toTarget: spot.isoTarget.clone(),
      fromZoom: orthoCam.zoom,
      toZoom: spot.isoZoom,
    });
  } else {
    const startPos = walkCam.position.clone();
    const startYaw = walkYaw;
    const startPitch = walkPitch;
    const dir = new THREE.Vector3().subVectors(spot.walkLook, spot.walkPos).normalize();
    let targetYaw = Math.atan2(-dir.x, -dir.z);
    // Shortest angular path
    let diff = ((targetYaw - startYaw + Math.PI) % (2 * Math.PI)) - Math.PI;
    if (diff < -Math.PI) diff += 2 * Math.PI;
    targetYaw = startYaw + diff;
    const targetPitch = Math.asin(THREE.MathUtils.clamp(dir.y, -0.85, 0.85));

    startTween({
      type: 'walk',
      fromPos: startPos,
      toPos: spot.walkPos.clone(),
      fromYaw: startYaw,
      toYaw: targetYaw,
      fromPitch: startPitch,
      toPitch: targetPitch,
      duration: 620,
    });
  }
}

document.getElementById('btn-mode-iso').addEventListener('click', () => setMode('iso'));
document.getElementById('btn-mode-walk').addEventListener('click', () => {
  setMode('walk');
  // Smoothly position inside corridor facing the office if just entering
  jumpToSpot('corridor', true);
});

document.getElementById('btn-toggle-outlines').addEventListener('click', () => {
  showOutlines = !showOutlines;
  applyLayerVisibility();
});
document.getElementById('btn-toggle-ceiling').addEventListener('click', () => {
  showCeiling = !showCeiling;
  applyLayerVisibility();
});
document.getElementById('btn-toggle-windows').addEventListener('click', () => {
  showFrontWindows = !showFrontWindows;
  applyLayerVisibility();
});
document.getElementById('btn-toggle-pins').addEventListener('click', () => {
  showPins = !showPins;
  applyLayerVisibility();
});
document.getElementById('btn-reset').addEventListener('click', () => jumpToSpot('overview', false));

document.querySelectorAll('.spot-btn').forEach((btn) => {
  btn.addEventListener('click', () => {
    const key = btn.dataset.spot;
    // Overview always returns to iso; other spots stay in current mode (or enter walk if already in walk, zoom in iso if in iso!)
    jumpToSpot(key, true);
  });
});

// Resize handler
window.addEventListener('resize', () => {
  const w = window.innerWidth;
  const h = window.innerHeight;
  const a = w / h;
  renderer.setSize(w, h);
  orthoCam.left = (-frustumSize * a) / 2;
  orthoCam.right = (frustumSize * a) / 2;
  orthoCam.top = frustumSize / 2;
  orthoCam.bottom = -frustumSize / 2;
  orthoCam.updateProjectionMatrix();
  walkCam.aspect = a;
  walkCam.updateProjectionMatrix();
});

// ---------------------------------------------------------------------------
// 7. Main Render Loop (Smooth Movement, Subtle Living Animations, 3D Pins)
// ---------------------------------------------------------------------------
const clock = new THREE.Clock();
const tmpProj = new THREE.Vector3();
const forwardVec = new THREE.Vector3();
const rightVec = new THREE.Vector3();

function animate() {
  requestAnimationFrame(animate);
  const dt = Math.min(clock.getDelta(), 0.05);
  const elapsed = clock.elapsedTime;

  // 1) Camera tweening
  if (tween) {
    const t = Math.min(1, (performance.now() - tween.start) / tween.duration);
    const ease = 1 - Math.pow(1 - t, 3);
    if (tween.type === 'iso') {
      orthoCam.position.lerpVectors(tween.fromPos, tween.toPos, ease);
      orbit.target.lerpVectors(tween.fromTarget, tween.toTarget, ease);
      orthoCam.zoom = THREE.MathUtils.lerp(tween.fromZoom, tween.toZoom, ease);
      orthoCam.updateProjectionMatrix();
    } else if (tween.type === 'walk') {
      walkCam.position.lerpVectors(tween.fromPos, tween.toPos, ease);
      walkYaw = THREE.MathUtils.lerp(tween.fromYaw, tween.toYaw, ease);
      walkPitch = THREE.MathUtils.lerp(tween.fromPitch, tween.toPitch, ease);
      applyWalkOrientation();
    }
    if (t >= 1) tween = null;
  }

  // 2) First-person walking movement
  if (mode === 'walk' && !tween) {
    const speed = keysPressed.has('ShiftLeft') || keysPressed.has('ShiftRight') ? 4.8 : 3.0;
    forwardVec.set(-Math.sin(walkYaw), 0, -Math.cos(walkYaw)).normalize();
    rightVec.set(Math.cos(walkYaw), 0, -Math.sin(walkYaw)).normalize();

    const deltaMove = new THREE.Vector3();
    if (keysPressed.has('KeyW') || keysPressed.has('ArrowUp')) deltaMove.add(forwardVec);
    if (keysPressed.has('KeyS') || keysPressed.has('ArrowDown')) deltaMove.sub(forwardVec);
    if (keysPressed.has('KeyD') || keysPressed.has('ArrowRight')) deltaMove.add(rightVec);
    if (keysPressed.has('KeyA') || keysPressed.has('ArrowLeft')) deltaMove.sub(rightVec);

    if (deltaMove.lengthSq() > 0) {
      deltaMove.normalize().multiplyScalar(speed * dt);
      walkCam.position.copy(clampWalkPosition(walkCam.position.clone().add(deltaMove)));
    } else if (walkMoveTarget) {
      const toTarget = new THREE.Vector3().subVectors(walkMoveTarget, walkCam.position);
      toTarget.y = 0;
      const dist = toTarget.length();
      if (dist < 0.08) {
        walkMoveTarget = null;
      } else {
        toTarget.normalize().multiplyScalar(Math.min(dist, 3.8 * dt));
        walkCam.position.copy(clampWalkPosition(walkCam.position.clone().add(toTarget)));
      }
    }
  } else if (mode === 'iso') {
    orbit.update();
  }

  // 3) Subtle living diorama character animations!
  for (const ch of animatedChars) {
    if (ch.isWalker) {
      // Gentle stroll bob along corridor
      ch.obj.position.y = ch.baseY + Math.abs(Math.sin(elapsed * 4.5 + ch.phase)) * 0.035;
      ch.obj.position.z = ch.baseZ + Math.sin(elapsed * 0.45 + ch.phase) * 1.4;
    } else if (ch.isRecliner) {
      // Cozy gentle chair sway while scrolling phone!
      ch.obj.rotation.y = ch.baseRotY + Math.sin(elapsed * 1.2) * 0.05;
    } else {
      // Subtle typing / breathing bob
      ch.obj.position.y = ch.baseY + Math.sin(elapsed * 3.0 + ch.phase) * 0.008;
    }
  }

  // 4) Project 3D Landmark Pins (Diorama Mode)
  if (mode === 'iso' && showPins) {
    const w = window.innerWidth;
    const h = window.innerHeight;
    for (const pin of pinEntries) {
      tmpProj.copy(pin.worldPos).project(orthoCam);
      const sx = (tmpProj.x * 0.5 + 0.5) * w;
      const sy = (-tmpProj.y * 0.5 + 0.5) * h;
      const onScreen = sx > 40 && sx < w - 40 && sy > 60 && sy < h - 70;
      pin.el.style.display = onScreen ? 'block' : 'none';
      pin.el.style.left = `${sx}px`;
      pin.el.style.top = `${sy}px`;
    }
  }

  renderer.render(scene, activeCamera);
}

animate();

// Expose tiny debug hook for automated visual QA screenshots
window.__DIORAMA__ = {
  setMode,
  jumpToSpot,
  toggleOutlines: () => { showOutlines = !showOutlines; applyLayerVisibility(); },
  setView: (pos, target, zoom) => {
    setMode('iso');
    tween = null;
    orthoCam.position.set(...pos);
    orbit.target.set(...target);
    if (zoom) {
      orthoCam.zoom = zoom;
      orthoCam.updateProjectionMatrix();
    }
    orbit.update();
  },
};
