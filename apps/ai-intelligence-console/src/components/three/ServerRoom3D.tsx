import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { Server } from '../../types/serverDashboard';
import {
  Eye,
  RotateCcw,
  Layers,
  Sparkles,
  Maximize2,
  Info,
  Zap,
  Activity,
  Cpu,
  HardDrive,
  RefreshCw,
} from 'lucide-react';

interface ServerRoom3DProps {
  servers: Server[];
  onSelectServer?: (server: Server) => void;
  selectedServerId?: string | null;
}

export function ServerRoom3D({
  servers,
  onSelectServer,
  selectedServerId,
}: ServerRoom3DProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoveredServer, setHoveredServer] = useState<Server | null>(null);
  const [selectedServer, setSelectedServer] = useState<Server | null>(null);
  const [isAutoRotate, setIsAutoRotate] = useState(true);
  const [cameraView, setCameraView] = useState<'overview' | 'rack_row' | 'top_down'>('overview');
  const [showDataFlow, setShowDataFlow] = useState(true);

  // References for Three.js cleanup & control
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const rackGroupsRef = useRef<Map<string, THREE.Group>>(new Map());

  // Keep selected server in sync
  useEffect(() => {
    if (selectedServerId) {
      const found = servers.find((s) => s.id === selectedServerId);
      if (found) setSelectedServer(found);
    }
  }, [selectedServerId, servers]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // --- 1. Scene, Camera, Renderer ---
    const width = container.clientWidth || 800;
    const height = container.clientHeight || 560;

    const scene = new THREE.Scene();
    sceneRef.current = scene;
    scene.background = new THREE.Color(0x090d16);
    scene.fog = new THREE.FogExp2(0x090d16, 0.025);

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    cameraRef.current = camera;
    camera.position.set(12, 10, 16);

    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // --- 2. Damped OrbitControls ---
    const controls = new OrbitControls(camera, renderer.domElement);
    controlsRef.current = controls;
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxPolarAngle = Math.PI / 2 - 0.02; // Don't go below floor
    controls.minDistance = 4;
    controls.maxDistance = 35;
    controls.target.set(0, 2, 0);

    // --- 3. Studio PBR Lighting ---
    // Warm Key Light
    const keyLight = new THREE.DirectionalLight(0xfff3e0, 2.2);
    keyLight.position.set(10, 15, 8);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.width = 2048;
    keyLight.shadow.mapSize.height = 2048;
    keyLight.shadow.camera.near = 0.5;
    keyLight.shadow.camera.far = 40;
    keyLight.shadow.camera.left = -15;
    keyLight.shadow.camera.right = 15;
    keyLight.shadow.camera.top = 15;
    keyLight.shadow.camera.bottom = -15;
    keyLight.shadow.bias = -0.0005;
    scene.add(keyLight);

    // Cool Fill Light (Hemisphere)
    const hemiLight = new THREE.HemisphereLight(0x38bdf8, 0x090d16, 1.2);
    scene.add(hemiLight);

    // Cyan & Amber Point Lights for Cyber Ambiance
    const cyanLight = new THREE.PointLight(0x06b6d4, 3, 20);
    cyanLight.position.set(-6, 4, 3);
    scene.add(cyanLight);

    const amberLight = new THREE.PointLight(0xf59e0b, 2.5, 20);
    amberLight.position.set(6, 4, -3);
    scene.add(amberLight);

    // --- 4. Procedural Floor Texture (Data Center Grid Tile) ---
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 512;
    const ctx = canvas.getContext('2d')!;
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, 512, 512);

    // Tile seams
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 4;
    ctx.strokeRect(0, 0, 512, 512);

    // Micro grid lines
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 1;
    for (let i = 64; i < 512; i += 64) {
      ctx.beginPath();
      ctx.moveTo(i, 0);
      ctx.lineTo(i, 512);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(0, i);
      ctx.lineTo(512, i);
      ctx.stroke();
    }

    const floorTexture = new THREE.CanvasTexture(canvas);
    floorTexture.wrapS = THREE.RepeatWrapping;
    floorTexture.wrapT = THREE.RepeatWrapping;
    floorTexture.repeat.set(12, 12);

    const floorGeo = new THREE.PlaneGeometry(50, 50);
    const floorMat = new THREE.MeshStandardMaterial({
      map: floorTexture,
      roughness: 0.4,
      metalness: 0.6,
    });
    const floor = new THREE.Mesh(floorGeo, floorMat);
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    scene.add(floor);

    // --- 5. Multi-Part Procedural Server Racks (Composite 3–12 Parts) ---
    const rackGroups = new Map<string, THREE.Group>();
    const interactiveMeshes: THREE.Mesh[] = [];

    // Reusable Materials
    const chassisMat = new THREE.MeshStandardMaterial({
      color: 0x1e293b,
      metalness: 0.85,
      roughness: 0.25,
    });
    const frameMat = new THREE.MeshStandardMaterial({
      color: 0x0f172a,
      metalness: 0.9,
      roughness: 0.2,
    });
    const panelMat = new THREE.MeshStandardMaterial({
      color: 0x334155,
      metalness: 0.7,
      roughness: 0.35,
    });
    const glassMat = new THREE.MeshPhysicalMaterial({
      color: 0x0284c7,
      metalness: 0.1,
      roughness: 0.1,
      transmission: 0.85,
      transparent: true,
      opacity: 0.35,
    });

    // Helper to build a composite procedural rack (8-10 distinct parts)
    const createProceduralRack = (server: Server, index: number, total: number) => {
      const rackGroup = new THREE.Group();
      rackGroup.name = `server_rack_${server.id}`;

      // Calculate position in 2 parallel rows
      const row = index % 2 === 0 ? -1 : 1;
      const col = Math.floor(index / 2) - total / 4;
      const posX = col * 2.8;
      const posZ = row * 3.8;
      rackGroup.position.set(posX, 0, posZ);

      // Part 1: Outer Cabinet Frame
      const frameGeo = new THREE.BoxGeometry(1.6, 4.4, 1.4);
      const frameMesh = new THREE.Mesh(frameGeo, frameMat);
      frameMesh.position.y = 2.2;
      frameMesh.castShadow = true;
      frameMesh.receiveShadow = true;
      rackGroup.add(frameMesh);

      // Part 2: Top Cap / Ventilation Hood
      const topCapGeo = new THREE.BoxGeometry(1.65, 0.15, 1.45);
      const topCap = new THREE.Mesh(topCapGeo, chassisMat);
      topCap.position.y = 4.45;
      rackGroup.add(topCap);

      // Part 3: Base Pedestal / Heavy Footer
      const baseGeo = new THREE.BoxGeometry(1.7, 0.2, 1.5);
      const baseMesh = new THREE.Mesh(baseGeo, frameMat);
      baseMesh.position.y = 0.1;
      rackGroup.add(baseMesh);

      // Part 4 & 5: Side Vented Panels
      const sidePanelGeo = new THREE.BoxGeometry(0.04, 3.8, 1.2);
      const leftPanel = new THREE.Mesh(sidePanelGeo, panelMat);
      leftPanel.position.set(-0.81, 2.2, 0);
      const rightPanel = new THREE.Mesh(sidePanelGeo, panelMat);
      rightPanel.position.set(0.81, 2.2, 0);
      rackGroup.add(leftPanel, rightPanel);

      // Part 6: Front Recessed Server Blades (Stacked 6 Blade Drawers)
      const bladeGeo = new THREE.BoxGeometry(1.4, 0.45, 1.15);
      const handleGeo = new THREE.BoxGeometry(0.12, 0.2, 0.08);

      // LED color based on server status
      const ledColor =
        server.status === 'healthy'
          ? 0x10b981
          : server.status === 'warning'
          ? 0xf59e0b
          : 0xef4444;

      const ledMat = new THREE.MeshBasicMaterial({ color: ledColor });

      for (let b = 0; b < 6; b++) {
        const bladeY = 0.7 + b * 0.58;
        const blade = new THREE.Mesh(bladeGeo, chassisMat);
        blade.position.set(0, bladeY, 0.05);
        rackGroup.add(blade);

        // Blade Handles (Left & Right)
        const handleL = new THREE.Mesh(handleGeo, panelMat);
        handleL.position.set(-0.55, bladeY, 0.65);
        const handleR = new THREE.Mesh(handleGeo, panelMat);
        handleR.position.set(0.55, bladeY, 0.65);
        rackGroup.add(handleL, handleR);

        // Part 7: Activity LEDs on each blade
        const ledGeo = new THREE.SphereGeometry(0.035, 8, 8);
        const led1 = new THREE.Mesh(ledGeo, ledMat);
        led1.position.set(0.35, bladeY, 0.65);
        const led2 = new THREE.Mesh(ledGeo, ledMat);
        led2.position.set(0.43, bladeY, 0.65);
        rackGroup.add(led1, led2);
      }

      // Part 8: Front Glass Door / Protective Grille
      const doorGeo = new THREE.BoxGeometry(1.5, 4.0, 0.06);
      const doorMesh = new THREE.Mesh(doorGeo, glassMat);
      doorMesh.position.set(0, 2.2, 0.71);
      doorMesh.castShadow = true;
      rackGroup.add(doorMesh);

      // Part 9: Overhead Cable Conduit Pipe
      const conduitGeo = new THREE.CylinderGeometry(0.04, 0.04, 1.2, 8);
      const conduit = new THREE.Mesh(conduitGeo, chassisMat);
      conduit.position.set(0, 5.05, 0);
      rackGroup.add(conduit);

      // Part 10: Radial Contact Shadow Plate
      const shadowGeo = new THREE.PlaneGeometry(2.4, 2.0);
      const shadowMat = new THREE.MeshBasicMaterial({
        color: 0x000000,
        transparent: true,
        opacity: 0.45,
      });
      const shadowMesh = new THREE.Mesh(shadowGeo, shadowMat);
      shadowMesh.rotation.x = -Math.PI / 2;
      shadowMesh.position.y = 0.01;
      rackGroup.add(shadowMesh);

      // Interactive Click/Raycast Anchor Box
      const hitBoxGeo = new THREE.BoxGeometry(1.8, 4.6, 1.6);
      const hitBoxMat = new THREE.MeshBasicMaterial({ visible: false });
      const hitBox = new THREE.Mesh(hitBoxGeo, hitBoxMat);
      hitBox.position.y = 2.3;
      hitBox.userData = { server };
      rackGroup.add(hitBox);
      interactiveMeshes.push(hitBox);

      rackGroups.set(server.id, rackGroup);
      scene.add(rackGroup);
    };

    servers.forEach((server, i) => createProceduralRack(server, i, servers.length));
    rackGroupsRef.current = rackGroups;

    // --- 6. Central Hologram Power Core & Particle Telemetry Stream ---
    const coreGroup = new THREE.Group();
    coreGroup.position.set(0, 0, 0);

    const coreGeo = new THREE.CylinderGeometry(0.8, 0.8, 4.8, 24, 1, true);
    const coreMat = new THREE.MeshStandardMaterial({
      color: 0x0284c7,
      emissive: 0x0369a1,
      emissiveIntensity: 0.6,
      wireframe: true,
      transparent: true,
      opacity: 0.5,
    });
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    coreMesh.position.y = 2.4;
    coreGroup.add(coreMesh);

    // Glowing Inner Plasma Cylinder
    const plasmaGeo = new THREE.CylinderGeometry(0.35, 0.35, 4.2, 16);
    const plasmaMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.8,
    });
    const plasmaMesh = new THREE.Mesh(plasmaGeo, plasmaMat);
    plasmaMesh.position.y = 2.4;
    coreGroup.add(plasmaMesh);

    scene.add(coreGroup);

    // Particle Data Flow
    const particleCount = 400;
    const particleGeo = new THREE.BufferGeometry();
    const particlePositions = new Float32Array(particleCount * 3);
    const particleSpeeds = new Float32Array(particleCount);

    for (let p = 0; p < particleCount; p++) {
      const angle = Math.random() * Math.PI * 2;
      const radius = 1.5 + Math.random() * 8.0;
      particlePositions[p * 3] = Math.cos(angle) * radius;
      particlePositions[p * 3 + 1] = 0.5 + Math.random() * 4.0;
      particlePositions[p * 3 + 2] = Math.sin(angle) * radius;
      particleSpeeds[p] = 0.02 + Math.random() * 0.04;
    }

    particleGeo.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
    const particleMat = new THREE.PointsMaterial({
      color: 0x38bdf8,
      size: 0.08,
      transparent: true,
      opacity: 0.7,
      blending: THREE.AdditiveBlending,
    });
    const particlePoints = new THREE.Points(particleGeo, particleMat);
    scene.add(particlePoints);

    // --- 7. Raycasting for Server Selection & Tooltips ---
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const onPointerMove = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(interactiveMeshes);

      if (intersects.length > 0) {
        const hitServer = intersects[0].object.userData.server as Server;
        setHoveredServer(hitServer);
        container.style.cursor = 'pointer';
      } else {
        setHoveredServer(null);
        container.style.cursor = 'default';
      }
    };

    const onClick = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(interactiveMeshes);

      if (intersects.length > 0) {
        const clickedServer = intersects[0].object.userData.server as Server;
        setSelectedServer(clickedServer);
        if (onSelectServer) onSelectServer(clickedServer);
      }
    };

    container.addEventListener('mousemove', onPointerMove);
    container.addEventListener('click', onClick);

    // --- 8. Lossless 60fps Animation Loop ---
    let animationFrameId: number;
    const clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);

      const delta = clock.getDelta();
      const time = clock.getElapsedTime();

      // Controls damping
      controls.autoRotate = isAutoRotate;
      controls.autoRotateSpeed = 0.6;
      controls.update();

      // Core rotation & pulse
      coreMesh.rotation.y = time * 0.4;
      plasmaMesh.scale.set(
        1 + Math.sin(time * 3) * 0.08,
        1,
        1 + Math.sin(time * 3) * 0.08
      );

      // Particle telemetry stream update
      if (showDataFlow) {
        const positions = particleGeo.attributes.position.array as Float32Array;
        for (let i = 0; i < particleCount; i++) {
          const idx = i * 3;
          positions[idx + 1] += particleSpeeds[i];
          if (positions[idx + 1] > 4.6) {
            positions[idx + 1] = 0.4;
          }
        }
        particleGeo.attributes.position.needsUpdate = true;
      }

      renderer.render(scene, camera);
    };

    animate();

    // Resize Observer
    const resizeObserver = new ResizeObserver(() => {
      if (!container) return;
      const newW = container.clientWidth;
      const newH = container.clientHeight;
      camera.aspect = newW / newH;
      camera.updateProjectionMatrix();
      renderer.setSize(newW, newH);
    });
    resizeObserver.observe(container);

    // Cleanup
    return () => {
      cancelAnimationFrame(animationFrameId);
      container.removeEventListener('mousemove', onPointerMove);
      container.removeEventListener('click', onClick);
      resizeObserver.disconnect();
      renderer.dispose();
      floorTexture.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [servers, isAutoRotate, showDataFlow, onSelectServer]);

  // Camera presets
  const setPresetCamera = (view: 'overview' | 'rack_row' | 'top_down') => {
    setCameraView(view);
    const camera = cameraRef.current;
    const controls = controlsRef.current;
    if (!camera || !controls) return;

    if (view === 'overview') {
      camera.position.set(12, 10, 16);
      controls.target.set(0, 2, 0);
    } else if (view === 'rack_row') {
      camera.position.set(0, 2.5, 7.5);
      controls.target.set(0, 2.2, 0);
    } else if (view === 'top_down') {
      camera.position.set(0.1, 22, 0.1);
      controls.target.set(0, 0, 0);
    }
  };

  return (
    <div className="relative w-full h-[620px] rounded-2xl overflow-hidden border border-slate-800 bg-slate-950 shadow-2xl">
      {/* 3D WebGL Canvas Container */}
      <div ref={containerRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

      {/* Viewport-First Floating HUD Dock (<= 15% viewport footprint) */}
      <div className="absolute top-4 right-4 z-10 flex flex-col gap-2">
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-2 shadow-xl backdrop-blur-md flex items-center gap-1.5 text-xs text-slate-300">
          <button
            onClick={() => setPresetCamera('overview')}
            className={`px-3 py-1.5 rounded-lg transition-colors font-medium flex items-center gap-1.5 ${
              cameraView === 'overview'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'hover:bg-slate-800 text-slate-400'
            }`}
          >
            <Eye className="w-3.5 h-3.5" />
            نظرة عامة
          </button>
          <button
            onClick={() => setPresetCamera('rack_row')}
            className={`px-3 py-1.5 rounded-lg transition-colors font-medium flex items-center gap-1.5 ${
              cameraView === 'rack_row'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'hover:bg-slate-800 text-slate-400'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            ممر الخوادم
          </button>
          <button
            onClick={() => setPresetCamera('top_down')}
            className={`px-3 py-1.5 rounded-lg transition-colors font-medium flex items-center gap-1.5 ${
              cameraView === 'top_down'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'hover:bg-slate-800 text-slate-400'
            }`}
          >
            <Maximize2 className="w-3.5 h-3.5" />
            مسقط رأسي
          </button>

          <div className="h-4 w-px bg-slate-800 mx-1" />

          {/* Auto Rotate Toggle */}
          <button
            onClick={() => setIsAutoRotate(!isAutoRotate)}
            title="تبديل الدوران التلقائي"
            className={`p-1.5 rounded-lg transition-colors ${
              isAutoRotate ? 'bg-emerald-500/20 text-emerald-400' : 'hover:bg-slate-800 text-slate-500'
            }`}
          >
            <RotateCcw className={`w-3.5 h-3.5 ${isAutoRotate ? 'animate-spin' : ''}`} />
          </button>

          {/* Particle Telemetry Toggle */}
          <button
            onClick={() => setShowDataFlow(!showDataFlow)}
            title="تبديل تدفق حزم البيانات"
            className={`p-1.5 rounded-lg transition-colors ${
              showDataFlow ? 'bg-cyan-500/20 text-cyan-400' : 'hover:bg-slate-800 text-slate-500'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Live Server Inspector Hover / Selected Drawer */}
      {(hoveredServer || selectedServer) && (
        <div className="absolute bottom-4 left-4 z-10 max-w-sm w-full bg-slate-900/95 border border-slate-700/80 rounded-xl p-4 shadow-2xl backdrop-blur-md animate-in fade-in slide-in-from-bottom-2 duration-200">
          {(() => {
            const current = hoveredServer || selectedServer!;
            const statusBg =
              current.status === 'healthy'
                ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                : current.status === 'warning'
                ? 'bg-amber-500/20 text-amber-400 border-amber-500/30'
                : 'bg-rose-500/20 text-rose-400 border-rose-500/30';

            const statusArabic =
              current.status === 'healthy'
                ? 'سليم ونشط'
                : current.status === 'warning'
                ? 'تحذير تشغيلي'
                : 'حرج / متعطل';

            return (
              <div className="space-y-3">
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <div className="flex items-center gap-2">
                    <span className="p-1.5 rounded-lg bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                      <Zap className="w-4 h-4" />
                    </span>
                    <div>
                      <h4 className="text-sm font-bold text-white flex items-center gap-2">
                        {current.name}
                        <span className="text-xs font-mono text-slate-400 font-normal">
                          ({current.ip})
                        </span>
                      </h4>
                      <p className="text-[11px] text-slate-400">
                        {current.region} • {current.type}
                      </p>
                    </div>
                  </div>
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded-full border font-semibold ${statusBg}`}
                  >
                    {statusArabic}
                  </span>
                </div>

                {/* Telemetry Metrics */}
                <div className="grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="bg-slate-800/60 p-2 rounded-lg border border-slate-700/50">
                    <div className="flex items-center justify-center gap-1 text-slate-400 text-[10px] mb-1">
                      <Cpu className="w-3 h-3 text-cyan-400" />
                      المعالج
                    </div>
                    <span className="font-mono font-bold text-white">{current.cpu}%</span>
                  </div>

                  <div className="bg-slate-800/60 p-2 rounded-lg border border-slate-700/50">
                    <div className="flex items-center justify-center gap-1 text-slate-400 text-[10px] mb-1">
                      <Activity className="w-3 h-3 text-purple-400" />
                      الذاكرة
                    </div>
                    <span className="font-mono font-bold text-white">{current.memory}%</span>
                  </div>

                  <div className="bg-slate-800/60 p-2 rounded-lg border border-slate-700/50">
                    <div className="flex items-center justify-center gap-1 text-slate-400 text-[10px] mb-1">
                      <HardDrive className="w-3 h-3 text-amber-400" />
                      القرص
                    </div>
                    <span className="font-mono font-bold text-white">{current.disk}%</span>
                  </div>
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
                  <span>زمن التشغيل: {current.uptimeDays} يوم</span>
                  <span className="text-cyan-400 font-mono">
                    الشبكة: {current.networkMbps} Mbps
                  </span>
                </div>
              </div>
            );
          })()}
        </div>
      )}

      {/* Bottom Right Helper Badge */}
      <div className="absolute bottom-4 right-4 z-10 flex items-center gap-2 bg-slate-900/80 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-400 pointer-events-none">
        <Info className="w-3.5 h-3.5 text-indigo-400" />
        انقر على أي خادم ثلاثي الأبعاد لفحصه وتحريك الكاميرا نحوه
      </div>
    </div>
  );
}
