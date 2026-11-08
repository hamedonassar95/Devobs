import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { Gamepad2, Play, RotateCcw, Shield, Zap, AlertTriangle, Trophy, Volume2, VolumeX, Pause, ArrowLeft } from 'lucide-react';

interface GameState {
  status: 'title' | 'playing' | 'paused' | 'gameover' | 'victory';
  score: number;
  health: number;
  wave: number;
  quarantinedCount: number;
  highScore: number;
}

export function CyberDefenseGame() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [gameState, setGameState] = useState<GameState>({
    status: 'title',
    score: 0,
    health: 100,
    wave: 1,
    quarantinedCount: 0,
    highScore: 0,
  });
  const [isMuted, setIsMuted] = useState(false);

  // Audio Synth Context
  const audioCtxRef = useRef<AudioContext | null>(null);

  const playSynthSound = (type: 'laser' | 'hit' | 'quarantine' | 'gameover' | 'start') => {
    if (isMuted) return;
    try {
      if (!audioCtxRef.current) {
        audioCtxRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
      }
      const ctx = audioCtxRef.current;
      if (ctx.state === 'suspended') {
        ctx.resume();
      }
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);

      const now = ctx.currentTime;
      if (type === 'laser') {
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(880, now);
        osc.frequency.exponentialRampToValueAtTime(220, now + 0.15);
        gain.gain.setValueAtTime(0.2, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.15);
        osc.start(now);
        osc.stop(now + 0.15);
      } else if (type === 'quarantine') {
        osc.type = 'sine';
        osc.frequency.setValueAtTime(300, now);
        osc.frequency.exponentialRampToValueAtTime(900, now + 0.2);
        gain.gain.setValueAtTime(0.3, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.2);
        osc.start(now);
        osc.stop(now + 0.2);
      } else if (type === 'hit') {
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(150, now);
        osc.frequency.exponentialRampToValueAtTime(40, now + 0.2);
        gain.gain.setValueAtTime(0.4, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.2);
        osc.start(now);
        osc.stop(now + 0.2);
      } else if (type === 'start') {
        osc.type = 'square';
        osc.frequency.setValueAtTime(440, now);
        osc.frequency.setValueAtTime(554.37, now + 0.1);
        osc.frequency.setValueAtTime(659.25, now + 0.2);
        gain.gain.setValueAtTime(0.2, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.35);
        osc.start(now);
        osc.stop(now + 0.35);
      } else if (type === 'gameover') {
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(300, now);
        osc.frequency.exponentialRampToValueAtTime(60, now + 0.6);
        gain.gain.setValueAtTime(0.4, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.6);
        osc.start(now);
        osc.stop(now + 0.6);
      }
    } catch (e) {
      // Audio not permitted without user gesture
    }
  };

  // Mutable Game Loop State
  const loopState = useRef({
    status: 'title' as GameState['status'],
    playerX: 0,
    playerTargetX: 0,
    lasers: [] as { mesh: THREE.Mesh; z: number }[],
    threats: [] as {
      group: THREE.Group;
      type: 'malware' | 'ddos' | 'ransomware';
      speed: number;
      x: number;
      z: number;
      rotationSpeed: number;
    }[],
    particles: [] as { mesh: THREE.Mesh; vx: number; vy: number; vz: number; life: number }[],
    lastShotTime: 0,
    keys: { left: false, right: false, space: false },
    score: 0,
    health: 100,
    wave: 1,
    quarantinedCount: 0,
    spawnTimer: 0,
  });

  useEffect(() => {
    loopState.current.status = gameState.status;
  }, [gameState.status]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // 1. Scene, Camera, Renderer Setup
    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || 600;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x050811);
    scene.fog = new THREE.FogExp2(0x050811, 0.035);

    const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 100);
    camera.position.set(0, 7, 12);
    camera.lookAt(0, 1, -4);

    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(renderer.domElement);

    // 2. Lighting (Studio PBR)
    const ambientLight = new THREE.AmbientLight(0x0a192f, 1.5);
    scene.add(ambientLight);

    const hemiLight = new THREE.HemisphereLight(0x38bdf8, 0x0f172a, 1.2);
    scene.add(hemiLight);

    const dirLight = new THREE.DirectionalLight(0x60a5fa, 2.5);
    dirLight.position.set(5, 15, 10);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 1024;
    dirLight.shadow.mapSize.height = 1024;
    scene.add(dirLight);

    // 3. Cyber Grid Floor with glowing pathways
    const gridHelper = new THREE.GridHelper(60, 40, 0x06b6d4, 0x1e293b);
    gridHelper.position.y = 0;
    scene.add(gridHelper);

    // Ground plane with subtle reflection
    const floorGeo = new THREE.PlaneGeometry(60, 60);
    const floorMat = new THREE.MeshStandardMaterial({
      color: 0x030712,
      roughness: 0.2,
      metalness: 0.8,
    });
    const floor = new THREE.Mesh(floorGeo, floorMat);
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    scene.add(floor);

    // 4. Procedural SRE Security Drone (Composite 7-part model)
    const playerGroup = new THREE.Group();
    scene.add(playerGroup);

    // Drone Core Body
    const bodyGeo = new THREE.BoxGeometry(1.4, 0.35, 1.2);
    const bodyMat = new THREE.MeshStandardMaterial({
      color: 0x1e293b,
      metalness: 0.9,
      roughness: 0.2,
    });
    const droneBody = new THREE.Mesh(bodyGeo, bodyMat);
    droneBody.castShadow = true;
    droneBody.position.y = 0.6;
    playerGroup.add(droneBody);

    // Glowing Neon Center Reactor
    const reactorGeo = new THREE.CylinderGeometry(0.3, 0.3, 0.45, 16);
    const reactorMat = new THREE.MeshBasicMaterial({ color: 0x00f0ff });
    const reactor = new THREE.Mesh(reactorGeo, reactorMat);
    reactor.position.set(0, 0.65, 0);
    playerGroup.add(reactor);

    // Left & Right Armor Wings
    const wingGeo = new THREE.BoxGeometry(0.8, 0.15, 0.9);
    const wingMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, metalness: 0.8, roughness: 0.3 });
    const leftWing = new THREE.Mesh(wingGeo, wingMat);
    leftWing.position.set(-1.1, 0.6, 0);
    playerGroup.add(leftWing);

    const rightWing = new THREE.Mesh(wingGeo, wingMat);
    rightWing.position.set(1.1, 0.6, 0);
    playerGroup.add(rightWing);

    // Left & Right Plasma Cannons
    const cannonGeo = new THREE.CylinderGeometry(0.08, 0.08, 1.1, 12);
    const cannonMat = new THREE.MeshStandardMaterial({ color: 0x64748b, metalness: 0.9, roughness: 0.1 });
    const leftCannon = new THREE.Mesh(cannonGeo, cannonMat);
    leftCannon.rotation.x = Math.PI / 2;
    leftCannon.position.set(-1.3, 0.55, -0.2);
    playerGroup.add(leftCannon);

    const rightCannon = new THREE.Mesh(cannonGeo, cannonMat);
    rightCannon.rotation.x = Math.PI / 2;
    rightCannon.position.set(1.3, 0.55, -0.2);
    playerGroup.add(rightCannon);

    // Shield Dome (pulsing)
    const shieldGeo = new THREE.SphereGeometry(1.6, 24, 16);
    const shieldMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.15,
      wireframe: true,
    });
    const shieldDome = new THREE.Mesh(shieldGeo, shieldMat);
    shieldDome.position.y = 0.6;
    playerGroup.add(shieldDome);

    playerGroup.position.set(0, 0, 5);

    // Shared Geometries & Materials for Laser & Threats
    const laserGeo = new THREE.CylinderGeometry(0.06, 0.06, 1.2, 8);
    laserGeo.rotateX(Math.PI / 2);
    const laserMat = new THREE.MeshBasicMaterial({ color: 0x00f0ff });

    const particleGeo = new THREE.BoxGeometry(0.12, 0.12, 0.12);
    const particleMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8 });

    // Function to create composite 3D threat (Malware, DDoS Bug, Ransomware Block)
    const createThreatModel = (type: 'malware' | 'ddos' | 'ransomware') => {
      const g = new THREE.Group();
      if (type === 'malware') {
        // Spiky Virus Octahedron + Ring
        const coreGeo = new THREE.OctahedronGeometry(0.7, 1);
        const coreMat = new THREE.MeshStandardMaterial({ color: 0xef4444, metalness: 0.7, roughness: 0.2 });
        const core = new THREE.Mesh(coreGeo, coreMat);
        g.add(core);

        const ringGeo = new THREE.TorusGeometry(1.0, 0.06, 8, 24);
        const ringMat = new THREE.MeshBasicMaterial({ color: 0xf43f5e });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = Math.PI / 3;
        g.add(ring);
      } else if (type === 'ddos') {
        // Fast Pulsing Swarm Tetrahedron
        const tetGeo = new THREE.TetrahedronGeometry(0.8);
        const tetMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, metalness: 0.8, roughness: 0.3 });
        const tet = new THREE.Mesh(tetGeo, tetMat);
        g.add(tet);
      } else {
        // Heavy Armored Ransomware Box with glowing locks
        const boxGeo = new THREE.BoxGeometry(1.1, 1.1, 1.1);
        const boxMat = new THREE.MeshStandardMaterial({ color: 0x8b5cf6, metalness: 0.9, roughness: 0.2 });
        const box = new THREE.Mesh(boxGeo, boxMat);
        g.add(box);

        const lockGeo = new THREE.TorusGeometry(0.5, 0.08, 8, 16);
        const lockMat = new THREE.MeshBasicMaterial({ color: 0xa855f7 });
        const lock = new THREE.Mesh(lockGeo, lockMat);
        g.add(lock);
      }
      return g;
    };

    // Keyboard controls
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === 'ArrowLeft' || e.code === 'KeyA') loopState.current.keys.left = true;
      if (e.code === 'ArrowRight' || e.code === 'KeyD') loopState.current.keys.right = true;
      if (e.code === 'Space') {
        e.preventDefault();
        loopState.current.keys.space = true;
      }
      if (e.code === 'Escape') {
        setGameState((prev) => ({
          ...prev,
          status: prev.status === 'playing' ? 'paused' : prev.status === 'paused' ? 'playing' : prev.status,
        }));
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.code === 'ArrowLeft' || e.code === 'KeyA') loopState.current.keys.left = false;
      if (e.code === 'ArrowRight' || e.code === 'KeyD') loopState.current.keys.right = false;
      if (e.code === 'Space') loopState.current.keys.space = false;
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    // Animation Loop
    let lastTime = performance.now();
    let animationFrameId: number;

    const animate = (time: number) => {
      animationFrameId = requestAnimationFrame(animate);
      const dt = Math.min((time - lastTime) / 1000, 0.05);
      lastTime = time;

      const ls = loopState.current;

      // Rotate Shield Dome & Pulsing effect
      shieldDome.rotation.y += 0.02;

      if (ls.status === 'playing') {
        // Player Movement (Damped Horizontal)
        const moveSpeed = 12 * dt;
        if (ls.keys.left) ls.playerTargetX = Math.max(ls.playerTargetX - moveSpeed, -6);
        if (ls.keys.right) ls.playerTargetX = Math.min(ls.playerTargetX + moveSpeed, 6);

        ls.playerX += (ls.playerTargetX - ls.playerX) * (1 - Math.exp(-15 * dt));
        playerGroup.position.x = ls.playerX;
        playerGroup.rotation.z = (ls.playerTargetX - ls.playerX) * -0.15; // Banking angle

        // Laser Firing
        if (ls.keys.space && time - ls.lastShotTime > 180) {
          ls.lastShotTime = time;
          playSynthSound('laser');

          // Left laser
          const leftL = new THREE.Mesh(laserGeo, laserMat);
          leftL.position.set(ls.playerX - 1.3, 0.55, playerGroup.position.z - 0.6);
          scene.add(leftL);
          ls.lasers.push({ mesh: leftL, z: leftL.position.z });

          // Right laser
          const rightL = new THREE.Mesh(laserGeo, laserMat);
          rightL.position.set(ls.playerX + 1.3, 0.55, playerGroup.position.z - 0.6);
          scene.add(rightL);
          ls.lasers.push({ mesh: rightL, z: rightL.position.z });
        }

        // Update Lasers
        for (let i = ls.lasers.length - 1; i >= 0; i--) {
          const l = ls.lasers[i];
          l.z -= 35 * dt;
          l.mesh.position.z = l.z;

          if (l.z < -25) {
            scene.remove(l.mesh);
            ls.lasers.splice(i, 1);
          }
        }

        // Spawn Threats
        ls.spawnTimer += dt;
        const spawnInterval = Math.max(1.8 - ls.wave * 0.15, 0.6);
        if (ls.spawnTimer > spawnInterval) {
          ls.spawnTimer = 0;
          const types: ('malware' | 'ddos' | 'ransomware')[] = ['malware', 'ddos', 'ransomware'];
          const chosenType = types[Math.floor(Math.random() * types.length)];
          const threatGroup = createThreatModel(chosenType);

          const spawnX = (Math.random() - 0.5) * 11;
          const speed = chosenType === 'ddos' ? 9 + ls.wave * 0.8 : chosenType === 'malware' ? 6 + ls.wave * 0.5 : 4 + ls.wave * 0.3;

          threatGroup.position.set(spawnX, 0.8, -25);
          scene.add(threatGroup);

          ls.threats.push({
            group: threatGroup,
            type: chosenType,
            speed,
            x: spawnX,
            z: -25,
            rotationSpeed: Math.random() * 2 + 1,
          });
        }

        // Update Threats and Collisions
        for (let tIdx = ls.threats.length - 1; tIdx >= 0; tIdx--) {
          const t = ls.threats[tIdx];
          t.z += t.speed * dt;
          t.group.position.z = t.z;
          t.group.rotation.x += t.rotationSpeed * dt;
          t.group.rotation.y += t.rotationSpeed * 0.7 * dt;

          // Check Laser Hit
          let hit = false;
          for (let lIdx = ls.lasers.length - 1; lIdx >= 0; lIdx--) {
            const l = ls.lasers[lIdx];
            const dist = Math.hypot(l.mesh.position.x - t.x, l.z - t.z);
            if (dist < 1.1) {
              hit = true;
              scene.remove(l.mesh);
              ls.lasers.splice(lIdx, 1);
              break;
            }
          }

          if (hit) {
            // Quarantine & Destroy
            playSynthSound('quarantine');
            ls.score += t.type === 'ransomware' ? 250 : t.type === 'malware' ? 100 : 150;
            ls.quarantinedCount++;

            // Create explosion particles
            for (let p = 0; p < 8; p++) {
              const part = new THREE.Mesh(particleGeo, particleMat);
              part.position.set(t.x, 0.8, t.z);
              scene.add(part);
              ls.particles.push({
                mesh: part,
                vx: (Math.random() - 0.5) * 8,
                vy: Math.random() * 6 + 1,
                vz: (Math.random() - 0.5) * 8,
                life: 0.5,
              });
            }

            scene.remove(t.group);
            ls.threats.splice(tIdx, 1);

            // Wave progression
            if (ls.quarantinedCount % 10 === 0) {
              ls.wave++;
            }

            setGameState((prev) => ({
              ...prev,
              score: ls.score,
              quarantinedCount: ls.quarantinedCount,
              wave: ls.wave,
              highScore: Math.max(prev.highScore, ls.score),
            }));
            continue;
          }

          // Threat reaching player or base
          if (t.z > playerGroup.position.z - 0.5 && Math.abs(t.x - ls.playerX) < 1.8) {
            // Player Collision Hit
            playSynthSound('hit');
            ls.health = Math.max(0, ls.health - 25);
            scene.remove(t.group);
            ls.threats.splice(tIdx, 1);

            setGameState((prev) => ({ ...prev, health: ls.health }));

            if (ls.health <= 0) {
              playSynthSound('gameover');
              ls.status = 'gameover';
              setGameState((prev) => ({ ...prev, status: 'gameover' }));
            }
            continue;
          }

          // Threat passed through server line
          if (t.z > 8) {
            ls.health = Math.max(0, ls.health - 15);
            scene.remove(t.group);
            ls.threats.splice(tIdx, 1);
            setGameState((prev) => ({ ...prev, health: ls.health }));

            if (ls.health <= 0) {
              playSynthSound('gameover');
              ls.status = 'gameover';
              setGameState((prev) => ({ ...prev, status: 'gameover' }));
            }
          }
        }

        // Update Particle Bursts
        for (let pIdx = ls.particles.length - 1; pIdx >= 0; pIdx--) {
          const p = ls.particles[pIdx];
          p.life -= dt;
          p.mesh.position.x += p.vx * dt;
          p.mesh.position.y += p.vy * dt;
          p.mesh.position.z += p.vz * dt;
          p.vy -= 15 * dt; // gravity

          if (p.life <= 0) {
            scene.remove(p.mesh);
            ls.particles.splice(pIdx, 1);
          }
        }
      } else {
        // Idle camera panning in Title / Game Over
        camera.position.x = Math.sin(time * 0.0008) * 3;
        camera.lookAt(0, 1, 0);
      }

      renderer.render(scene, camera);
    };

    animationFrameId = requestAnimationFrame(animate);

    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight || 600;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
      cancelAnimationFrame(animationFrameId);

      // Cleanup 3D meshes
      loopState.current.lasers.forEach((l) => scene.remove(l.mesh));
      loopState.current.threats.forEach((t) => scene.remove(t.group));
      loopState.current.particles.forEach((p) => scene.remove(p.mesh));
      renderer.dispose();
      if (renderer.domElement.parentNode) {
        renderer.domElement.parentNode.removeChild(renderer.domElement);
      }
    };
  }, []);

  const handleStartGame = () => {
    playSynthSound('start');
    const ls = loopState.current;
    ls.health = 100;
    ls.score = 0;
    ls.wave = 1;
    ls.quarantinedCount = 0;
    ls.playerX = 0;
    ls.playerTargetX = 0;
    ls.lasers.forEach((l) => l.mesh.parent?.remove(l.mesh));
    ls.threats.forEach((t) => t.group.parent?.remove(t.group));
    ls.particles.forEach((p) => p.mesh.parent?.remove(p.mesh));
    ls.lasers = [];
    ls.threats = [];
    ls.particles = [];
    ls.status = 'playing';

    setGameState({
      status: 'playing',
      score: 0,
      health: 100,
      wave: 1,
      quarantinedCount: 0,
      highScore: gameState.highScore,
    });
  };

  return (
    <div className="relative w-full h-[650px] rounded-3xl overflow-hidden bg-slate-950 border border-slate-800 shadow-2xl select-none">
      {/* 3D WebGL Canvas Container */}
      <div ref={containerRef} className="absolute inset-0 w-full h-full" />

      {/* Persistent Perimeter Status Clusters (Low-Occlusion UI) */}
      {gameState.status === 'playing' && (
        <div className="absolute top-4 inset-x-6 flex items-center justify-between pointer-events-none z-20">
          <div className="flex items-center gap-4 bg-slate-900/80 backdrop-blur-md px-4 py-2 rounded-2xl border border-slate-700/60 shadow-lg pointer-events-auto">
            <div className="flex items-center gap-2">
              <Shield className={`w-4 h-4 ${gameState.health > 40 ? 'text-emerald-400' : 'text-rose-500 animate-pulse'}`} />
              <div className="w-28 h-2 bg-slate-800 rounded-full overflow-hidden border border-slate-700">
                <div
                  className={`h-full transition-all duration-300 ${
                    gameState.health > 50 ? 'bg-emerald-500' : gameState.health > 25 ? 'bg-amber-500' : 'bg-rose-500'
                  }`}
                  style={{ width: `${gameState.health}%` }}
                />
              </div>
              <span className="text-xs font-mono font-bold text-white tabular-nums">{gameState.health}%</span>
            </div>

            <div className="w-px h-4 bg-slate-700" />

            <div className="flex items-center gap-1.5 text-xs text-sky-400 font-mono">
              <Zap className="w-3.5 h-3.5" />
              <span>موجة {gameState.wave}</span>
            </div>
          </div>

          <div className="flex items-center gap-3 bg-slate-900/80 backdrop-blur-md px-4 py-2 rounded-2xl border border-slate-700/60 shadow-lg pointer-events-auto">
            <div className="text-right">
              <p className="text-[10px] text-slate-400 font-medium">النقاط المحققة</p>
              <p className="text-base font-extrabold text-cyan-400 font-mono tabular-nums leading-none">
                {gameState.score}
              </p>
            </div>

            <button
              onClick={() => setIsMuted(!isMuted)}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
              title={isMuted ? 'تشغيل الصوت' : 'كتم الصوت'}
            >
              {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
            </button>
          </div>
        </div>
      )}

      {/* Control Hint Line during Play */}
      {gameState.status === 'playing' && (
        <div className="absolute bottom-4 inset-x-0 flex justify-center pointer-events-none z-20">
          <div className="bg-slate-900/70 backdrop-blur-sm px-4 py-1.5 rounded-full border border-slate-800 text-[11px] font-mono text-slate-400 shadow-md">
            تحريك: <span className="text-white font-bold">A / D</span> أو <span className="text-white font-bold">← / →</span> · إطلاق ليزر العزل: <span className="text-cyan-400 font-bold">SPACE</span> · إيقاف مؤقت: <span className="text-slate-300 font-bold">ESC</span>
          </div>
        </div>
      )}

      {/* Title Screen Overlay */}
      {gameState.status === 'title' && (
        <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-md flex flex-col items-center justify-center p-6 text-center z-30">
          <div className="w-16 h-16 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 flex items-center justify-center mb-4 shadow-lg shadow-cyan-500/20">
            <Gamepad2 className="w-9 h-9" />
          </div>

          <h2 className="text-3xl sm:text-4xl font-black text-white tracking-tight mb-2">
            الدفاع السيبراني المتقدم: <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500">Cyber Shield 3D</span>
          </h2>
          <p className="text-sm text-slate-400 max-w-md mb-6 leading-relaxed">
            محاكاة ثلاثية الأبعاد للدفاع عن مراكز البيانات ضد هجمات البرمجيات الخبيثة وهجمات حجب الخدمة (DDoS). تحكّم بمركبة الـ SRE واحمِ البنية التحتية.
          </p>

          <button
            onClick={handleStartGame}
            className="flex items-center gap-3 px-8 py-3.5 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold text-sm rounded-2xl shadow-xl shadow-cyan-500/25 transition-all hover:scale-105 active:scale-95"
          >
            <Play className="w-5 h-5 fill-current" />
            <span>ابدأ محاكاة الدفاع (Space / Enter)</span>
          </button>

          <div className="mt-8 flex items-center gap-6 text-xs text-slate-500 font-mono">
            <span>التحكم: أسهم الاتجاهات / A-D</span>
            <span>·</span>
            <span>الليزر: مسطرة المسافة (Space)</span>
          </div>
        </div>
      )}

      {/* Game Over Screen */}
      {gameState.status === 'gameover' && (
        <div className="absolute inset-0 bg-black/85 backdrop-blur-md flex flex-col items-center justify-center p-6 text-center z-30 animate-fadeIn">
          <div className="w-16 h-16 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-500 flex items-center justify-center mb-4 shadow-lg shadow-rose-500/20">
            <AlertTriangle className="w-9 h-9" />
          </div>

          <h3 className="text-2xl sm:text-3xl font-extrabold text-white mb-1">تم اختراق حاجز البنية التحتية</h3>
          <p className="text-xs text-rose-400 mb-6 font-mono">CRITICAL_INFRASTRUCTURE_BREACH</p>

          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 w-64 mb-6 space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-slate-400">النقاط المحققة:</span>
              <span className="font-bold text-white font-mono">{gameState.score}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-slate-400">التهديدات المعزولة:</span>
              <span className="font-bold text-cyan-400 font-mono">{gameState.quarantinedCount}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-slate-400">أعلى رقم مسجل:</span>
              <span className="font-bold text-amber-400 font-mono">{gameState.highScore}</span>
            </div>
          </div>

          <button
            onClick={handleStartGame}
            className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-rose-600 to-rose-700 hover:from-rose-500 hover:to-rose-600 text-white font-bold text-xs rounded-xl shadow-lg shadow-rose-600/30 transition-all hover:scale-105"
          >
            <RotateCcw className="w-4 h-4" />
            <span>إعادة محاكاة الدفاع</span>
          </button>
        </div>
      )}

      {/* Paused Modal */}
      {gameState.status === 'paused' && (
        <div className="absolute inset-0 bg-black/75 backdrop-blur-sm flex flex-col items-center justify-center p-6 text-center z-30">
          <div className="w-12 h-12 rounded-xl bg-slate-800 text-slate-300 flex items-center justify-center mb-3">
            <Pause className="w-6 h-6" />
          </div>
          <h3 className="text-xl font-bold text-white mb-4">المحاكاة موقوفة مؤقتاً</h3>
          <button
            onClick={() => setGameState((prev) => ({ ...prev, status: 'playing' }))}
            className="px-6 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs rounded-xl shadow-lg shadow-cyan-600/20 transition-all"
          >
            استئناف المحاكاة (ESC)
          </button>
        </div>
      )}
    </div>
  );
}
