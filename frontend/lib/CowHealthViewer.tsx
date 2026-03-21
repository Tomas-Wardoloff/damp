'use client';

/**
 * CowHealthViewer
 * Modelo en: /public/cow.glb
 * npm install three @types/three
 *
 * Bounds reales del modelo centrado:
 *   X: -0.983 → +0.983  (cabeza en X+)
 *   Y: -0.583 → +0.583  (patas en Y-, lomo en Y+)
 *   Z: -0.230 → +0.230  (ancho)
 */

import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

export type CowHealthStatus = 'healthy' | 'mastitis' | 'fever' | 'estrus' | 'digestive';
export interface CowConfig { id: string; name: string; status: CowHealthStatus; }

// ─────────────────────────────────────────────
// ZONAS — en coordenadas locales del modelo
// El modelo se centra en su bounding box center,
// luego se eleva para que las patas toquen el piso.
// Después de elevar: patas en Y≈0, lomo en Y≈1.166
// ─────────────────────────────────────────────
const ZONES = {
    // FIEBRE: cabeza (extremo X+), con blend suave en cuello
    head: { xMin: 0.42, xMax: 0.983, zMin: -0.230, zMax: 0.230 },

    // MASTITIS: ubres — cuelgan entre las 4 patas, justo debajo del vientre
    // Las patas llegan hasta Y≈0.45, las ubres empiezan donde terminan las patas
    // Ubres entre patas TRASERAS (X negativo = lado cola)
    udder: { yMin: 0.25, yMax: 0.50, xMin: -1.62, xMax: -0.20, zMin: -0.14, zMax: 0.15 },

    // DIGESTIVO: vientre central — banda media del tronco
    // Panza central, sin tocar pecho ni ubres
    belly: { yMin: -0.52, yMax: 0.85, xMin: -0.50, xMax: 0.30, zMin: -0.25, zMax: 0.25 },
};

const DEBUG_ZONES = false

export const STATUS_META: Record<CowHealthStatus, { label: string; baseColor: string; description: string }> = {
    healthy: { label: 'Sana', baseColor: '#52a477', description: 'Sin patologías detectadas' },
    mastitis: { label: 'Mastitis', baseColor: '#00ccff', description: 'Inflamación en ubres' },
    fever: { label: 'Fiebre', baseColor: '#00ccff', description: 'Temperatura elevada' },
    estrus: { label: 'En celo', baseColor: '#b15a8b', description: 'Período de fertilidad' },
    digestive: { label: 'Prob. digestivo', baseColor: '#00ccff', description: 'Disturbio gastrointestinal' },
};

/**
 * Mapea los estados que vienen del backend a los estados internos del visor 3D
 */
export function mapBackendStatusTo3D(status: string | null | undefined): CowHealthStatus {
    if (!status) return 'healthy';
    const s = status.toUpperCase();
    if (s.includes('MASTITIS')) return 'mastitis';
    if (s.includes('FEBRIL') || s.includes('SUBCLINICA') || s.includes('FIEBRE')) return 'fever';
    if (s.includes('CELO')) return 'estrus';
    if (s.includes('DIGESTIVO')) return 'digestive';
    return 'healthy';
}

// ─────────────────────────────────────────────
// SHADER HOLOGRAMA
// Solo la zona afectada late. El resto es cyan suave estático.
// ─────────────────────────────────────────────
function createHologramMaterial(status: CowHealthStatus): THREE.ShaderMaterial {
    type Cfg = { base: THREE.Vector3; zone: THREE.Vector3; useZone: number; zoneType: number };
    const map: Record<CowHealthStatus, Cfg> = {
        healthy: { base: new THREE.Vector3(0.08, 0.45, 0.22), zone: new THREE.Vector3(0.08, 0.45, 0.22), useZone: 0, zoneType: 0 },
        mastitis: { base: new THREE.Vector3(0.01, 0.12, 0.22), zone: new THREE.Vector3(1.0, 0.02, 0.02), useZone: 1, zoneType: 1 },
        fever: { base: new THREE.Vector3(0.01, 0.12, 0.22), zone: new THREE.Vector3(1.0, 0.02, 0.02), useZone: 1, zoneType: 0 },
        estrus: { base: new THREE.Vector3(0.45, 0.08, 0.32), zone: new THREE.Vector3(0.45, 0.08, 0.32), useZone: 0, zoneType: 0 },
        digestive: { base: new THREE.Vector3(0.01, 0.12, 0.22), zone: new THREE.Vector3(1.0, 0.02, 0.02), useZone: 1, zoneType: 2 },
    };
    const cfg = map[status];

    return new THREE.ShaderMaterial({
        uniforms: {
            uTime: { value: 0 },
            uBaseColor: { value: cfg.base },
            uZoneColor: { value: cfg.zone },
            uUseZone: { value: cfg.useZone },
            uZoneType: { value: cfg.zoneType },
            // head
            uHeadMinX: { value: ZONES.head.xMin },
            uHeadMaxX: { value: ZONES.head.xMax },
            uHeadMinZ: { value: ZONES.head.zMin },
            uHeadMaxZ: { value: ZONES.head.zMax },
            // udder
            uUdderMinY: { value: ZONES.udder.yMin },
            uUdderMaxY: { value: ZONES.udder.yMax },
            uUdderMinX: { value: ZONES.udder.xMin },
            uUdderMaxX: { value: ZONES.udder.xMax },
            uUdderMinZ: { value: ZONES.udder.zMin },
            uUdderMaxZ: { value: ZONES.udder.zMax },
            // belly
            uBellyMinY: { value: ZONES.belly.yMin },
            uBellyMaxY: { value: ZONES.belly.yMax },
            uBellyMinX: { value: ZONES.belly.xMin },
            uBellyMaxX: { value: ZONES.belly.xMax },
            uBellyMinZ: { value: ZONES.belly.zMin },
            uBellyMaxZ: { value: ZONES.belly.zMax },
        },
        vertexShader: /* glsl */`
      varying vec3 vPosition;
      varying vec3 vNormal;
      void main() {
        vPosition   = position;
        vNormal     = normalize(normalMatrix * normal);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
        fragmentShader: /* glsl */`
      uniform float uTime;
      uniform vec3  uBaseColor;
      uniform vec3  uZoneColor;
      uniform float uUseZone;
      uniform float uZoneType;

      uniform float uHeadMinX; uniform float uHeadMaxX;
      uniform float uHeadMinZ; uniform float uHeadMaxZ;

      uniform float uUdderMinY; uniform float uUdderMaxY;
      uniform float uUdderMinX; uniform float uUdderMaxX;
      uniform float uUdderMinZ; uniform float uUdderMaxZ;

      uniform float uBellyMinY; uniform float uBellyMaxY;
      uniform float uBellyMinX; uniform float uBellyMaxX;
      uniform float uBellyMinZ; uniform float uBellyMaxZ;

      varying vec3 vPosition;
      varying vec3 vNormal;

      void main() {
        // Fresnel: brillo solo en bordes
        vec3  viewDir = normalize(cameraPosition - vPosition);
        float rim     = clamp(abs(dot(vNormal, viewDir)), 0.0, 1.0);
        float fresnel = pow(1.0 - rim, 3.5);

        // Scanlines estáticas (sin animación de tiempo)
        float scan = sin(vPosition.y * 70.0) * 0.012 + 0.988;

        // ── Detección de zonas ──

        // FIEBRE — cabeza: blend suave en X, filtro duro en Z
        float headInZ   = step(uHeadMinZ, vPosition.z) * step(vPosition.z, uHeadMaxZ);
        float headBlend = smoothstep(uHeadMinX - 0.06, uHeadMinX + 0.10, vPosition.x) * headInZ;

        // MASTITIS — ubres: check X, Y y Z con blend suave en los tres ejes
        float udderW = 0.0;
        if (vPosition.y > uUdderMinY && vPosition.y < uUdderMaxY
         && vPosition.x > uUdderMinX && vPosition.x < uUdderMaxX
         && vPosition.z > uUdderMinZ && vPosition.z < uUdderMaxZ) {
          float bx = smoothstep(uUdderMinX, uUdderMinX + 0.12, vPosition.x)
                   * smoothstep(uUdderMaxX, uUdderMaxX - 0.12, vPosition.x);
          float by = smoothstep(uUdderMinY, uUdderMinY + 0.05, vPosition.y)
                   * smoothstep(uUdderMaxY, uUdderMaxY - 0.05, vPosition.y);
          float bz = smoothstep(uUdderMinZ, uUdderMinZ + 0.04, vPosition.z)
                   * smoothstep(uUdderMaxZ, uUdderMaxZ - 0.04, vPosition.z);
          udderW = bx * by * bz;
        }

        // DIGESTIVO — panza: check X, Y y Z con blend suave en los tres ejes
        float bellyW = 0.0;
        if (vPosition.y > uBellyMinY && vPosition.y < uBellyMaxY
         && vPosition.x > uBellyMinX && vPosition.x < uBellyMaxX
         && vPosition.z > uBellyMinZ && vPosition.z < uBellyMaxZ) {
          float bx = smoothstep(uBellyMinX, uBellyMinX + 0.15, vPosition.x)
                   * smoothstep(uBellyMaxX, uBellyMaxX - 0.15, vPosition.x);
          float by = smoothstep(uBellyMinY, uBellyMinY + 0.06, vPosition.y)
                   * smoothstep(uBellyMaxY, uBellyMaxY - 0.06, vPosition.y);
          float bz = smoothstep(uBellyMinZ, uBellyMinZ + 0.05, vPosition.z)
                   * smoothstep(uBellyMaxZ, uBellyMaxZ - 0.05, vPosition.z);
          bellyW = bx * by * bz * (1.0 - udderW); // no solapar con ubres
        }

        // ── Pulso de latido — solo para la zona afectada ──
        float t    = mod(uTime * 0.8, 1.0);
        float beat = exp(-10.0 * t) * (1.0 - exp(-30.0 * t));
        float pulse = 0.55 + beat * 0.45;

        // ── Color final ──
        vec3  color        = uBaseColor;
        float zoneAlphaMod = 0.0;

        if (uUseZone > 0.5) {
          if (uZoneType < 0.5) {
            // FIEBRE — cabeza
            float weight = headBlend * pulse;
            color = mix(uBaseColor, uZoneColor, weight);
            zoneAlphaMod = weight * 0.55;
          } else if (uZoneType < 1.5) {
            // MASTITIS — ubres
            float weight = udderW * pulse;
            color = mix(uBaseColor, uZoneColor, weight);
            zoneAlphaMod = weight * 0.65;
          } else {
            // DIGESTIVO — panza
            float weight = bellyW * pulse;
            color = mix(uBaseColor, uZoneColor, weight);
            zoneAlphaMod = weight * 0.50;
          }
        }

        // Glow de borde (fresnel)
        color += fresnel * uBaseColor * 0.45;
        color *= scan;

        // Alpha: interior más denso para efecto "volumen"
        // Al usar DoubleSide, el solapamiento de caras frontales y traseras
        // crea una sensación de relleno.
        float alpha = 0.35 + fresnel * 0.50 + zoneAlphaMod;

        gl_FragColor = vec4(color, alpha);
      }
    `,
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        side: THREE.DoubleSide,
    });
}

function createWireframeMaterial(status: CowHealthStatus): THREE.ShaderMaterial {
    const colors: Record<CowHealthStatus, string> = {
        healthy: '#00ff88', mastitis: '#00ccff',
        fever: '#00ccff', estrus: '#ff44aa', digestive: '#00ccff',
    };
    const c = new THREE.Color(colors[status]);
    return new THREE.ShaderMaterial({
        uniforms: {
            uTime: { value: 0 },
            uColor: { value: new THREE.Vector3(c.r, c.g, c.b) },
        },
        vertexShader: `void main() { gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
        fragmentShader: `
      uniform vec3 uColor;
      void main() {
        gl_FragColor = vec4(uColor, 0.032);
      }
    `,
        transparent: true,
        wireframe: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
    });
}

// ─────────────────────────────────────────────
// CANVAS 3D
// ─────────────────────────────────────────────
function CowCanvas({ status }: { status: CowHealthStatus }) {
    const mountRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const container = mountRef.current;
        if (!container) return;

        const W = container.clientWidth || 300;
        const H = container.clientHeight || 280;

        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setSize(W, H);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.setClearColor(0x000000, 0);
        container.appendChild(renderer.domElement);

        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(38, W / H, 0.01, 100);
        camera.position.set(1.5, 1.0, 1.5);
        camera.lookAt(0, 0.5, 0);

        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.07;
        controls.enablePan = false;
        controls.autoRotate = true;
        controls.autoRotateSpeed = 0.3;
        controls.target.set(0, 0.5, 0);
        controls.minDistance = 1.8;
        controls.maxDistance = 8.5;

        scene.add(new THREE.AmbientLight(0x0a1a2e, 1.5));
        const rimCol = new THREE.Color(STATUS_META[status].baseColor);
        const rim = new THREE.DirectionalLight(rimCol, 0.25);
        rim.position.set(-3, 4, -2);
        scene.add(rim);

        // Grid en Y=0 (piso)
        const grid = new THREE.GridHelper(6, 28, 0x002a44, 0x001a2e);
        grid.position.y = 0;
        scene.add(grid);

        // Ring en el piso
        const ringMat = new THREE.MeshBasicMaterial({
            color: STATUS_META[status].baseColor, transparent: true, opacity: 0.22,
        });
        const ring = new THREE.Mesh(new THREE.TorusGeometry(1.4, 0.006, 6, 64), ringMat);
        ring.rotation.x = Math.PI / 2;
        ring.position.y = 0.01;
        scene.add(ring);

        // Partículas
        const N = 40;
        const pPos = new Float32Array(N * 3);
        for (let i = 0; i < N; i++) {
            pPos[i * 3] = (Math.random() - 0.5) * 3.0;
            pPos[i * 3 + 1] = Math.random() * 1.8;
            pPos[i * 3 + 2] = (Math.random() - 0.5) * 3.0;
        }
        const pGeo = new THREE.BufferGeometry();
        pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3));
        const pMat = new THREE.PointsMaterial({
            color: STATUS_META[status].baseColor, size: 0.012,
            transparent: true, opacity: 0.28,
            blending: THREE.AdditiveBlending, depthWrite: false,
        });
        scene.add(new THREE.Points(pGeo, pMat));

        // ─────────────────────────────────────────────
        // PASTO — 10 clústeres dentro del círculo (radio ~1.2)
        // Geometría procedural, sin archivos externos
        // ─────────────────────────────────────────────
        const grassGroup = new THREE.Group();
        const grassMat = new THREE.ShaderMaterial({
            uniforms: {
                uColor: { value: new THREE.Vector3(0.05, 1.0, 0.35) },
            },
            vertexShader: /* glsl */`
                varying float vY;
                void main() {
                    vY = position.y;
                    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
                }
            `,
            fragmentShader: /* glsl */`
                uniform vec3 uColor;
                varying float vY;
                void main() {
                    float alpha = 0.75 + vY * 0.25;
                    gl_FragColor = vec4(uColor * (0.85 + vY * 0.5), alpha);
                }
            `,
            transparent: true,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
            side: THREE.DoubleSide,
        });

        // 10 clústeres distribuidos dentro del círculo (evitando el centro donde está la vaca)
        const clusterPositions: [number, number, number][] = [
            [-0.85, 0.0, 0.70],
            [0.90, 0.0, -0.75],
            [-1.05, 0.0, -0.40],
            [0.70, 0.0, 0.90],
            [-0.30, 0.0, -1.05],
            [1.10, 0.0, 0.30],
            [-1.15, 0.0, 0.20],
            [0.40, 0.0, 1.10],
            [-0.60, 0.0, -0.95],
            [0.95, 0.0, 0.70],
        ];

        clusterPositions.forEach(([cx, , cz]) => {
            const bladesCount = 10 + Math.floor(Math.random() * 6); // 10–15 hojas por clúster
            for (let b = 0; b < bladesCount; b++) {
                const h = 0.22 + Math.random() * 0.16;       // altura 0.22–0.38 (más alto)
                const w = 0.025 + Math.random() * 0.015;     // ancho más generoso
                const lean = (Math.random() - 0.5) * 0.55;     // inclinación lateral
                const rotY = Math.random() * Math.PI;           // rotación aleatoria

                // Hoja: triángulo (base ancha, punta inclinada)
                const geo = new THREE.BufferGeometry();
                const verts = new Float32Array([
                    -w, 0, 0,  // base izquierda
                    w, 0, 0,  // base derecha
                    lean, h, 0,  // punta
                ]);
                const uvs = new Float32Array([0, 0, 1, 0, 0.5, 1]);
                geo.setAttribute('position', new THREE.BufferAttribute(verts, 3));
                geo.setAttribute('uv', new THREE.BufferAttribute(uvs, 2));

                const blade = new THREE.Mesh(geo, grassMat);
                blade.position.set(
                    cx + (Math.random() - 0.5) * 0.28,
                    0.0,
                    cz + (Math.random() - 0.5) * 0.28,
                );
                blade.rotation.y = rotY;
                grassGroup.add(blade);
            }
        });

        scene.add(grassGroup);
        // ─────────────────────────────────────────────

        // Debug: cajas para visualizar zonas
        if (DEBUG_ZONES) {
            // Zona ubres (rojo)
            const udderHelper = new THREE.Mesh(
                new THREE.BoxGeometry(
                    ZONES.udder.xMax - ZONES.udder.xMin,
                    ZONES.udder.yMax - ZONES.udder.yMin,
                    ZONES.udder.zMax - ZONES.udder.zMin,
                ),
                new THREE.MeshBasicMaterial({ color: 0xff0000, wireframe: true, opacity: 0.5, transparent: true })
            );
            udderHelper.position.set(
                (ZONES.udder.xMin + ZONES.udder.xMax) / 2,
                (ZONES.udder.yMin + ZONES.udder.yMax) / 2,
                (ZONES.udder.zMin + ZONES.udder.zMax) / 2,
            );
            scene.add(udderHelper);

            // Zona panza (naranja)
            const bellyHelper = new THREE.Mesh(
                new THREE.BoxGeometry(
                    ZONES.belly.xMax - ZONES.belly.xMin,
                    ZONES.belly.yMax - ZONES.belly.yMin,
                    ZONES.belly.zMax - ZONES.belly.zMin,
                ),
                new THREE.MeshBasicMaterial({ color: 0xff8800, wireframe: true, opacity: 0.5, transparent: true })
            );
            bellyHelper.position.set(
                (ZONES.belly.xMin + ZONES.belly.xMax) / 2,
                (ZONES.belly.yMin + ZONES.belly.yMax) / 2,
                (ZONES.belly.zMin + ZONES.belly.zMax) / 2,
            );
            scene.add(bellyHelper);

            // Zona cabeza (amarillo)
            const headHelper = new THREE.Mesh(
                new THREE.BoxGeometry(
                    ZONES.head.xMax - ZONES.head.xMin,
                    0.5,
                    ZONES.head.zMax - ZONES.head.zMin,
                ),
                new THREE.MeshBasicMaterial({ color: 0xffff00, wireframe: true, opacity: 0.5, transparent: true })
            );
            headHelper.position.set(
                (ZONES.head.xMin + ZONES.head.xMax) / 2,
                0.8,
                (ZONES.head.zMin + ZONES.head.zMax) / 2,
            );
            scene.add(headHelper);
        }

        const holoMat = createHologramMaterial(status);
        const wireMat = createWireframeMaterial(status);

        const loader = new GLTFLoader();
        loader.load(
            '/cow.glb',
            (gltf) => {
                const model = gltf.scene;

                // 1. Centrar horizontalmente (X y Z)
                const box = new THREE.Box3().setFromObject(model);
                const center = box.getCenter(new THREE.Vector3());
                const size = box.getSize(new THREE.Vector3());

                model.position.x -= center.x;
                model.position.z -= center.z;
                // 2. Elevar para que las patas queden en Y=0
                model.position.y -= box.min.y;

                // 3. Escalar si supera 2.2 unidades
                const maxDim = Math.max(size.x, size.y, size.z);
                if (maxDim > 2.2) {
                    const s = 2.2 / maxDim;
                    model.scale.setScalar(s);
                    // Reajustar Y después de escalar
                    model.position.y = 0;
                    const box2 = new THREE.Box3().setFromObject(model);
                    model.position.y -= box2.min.y;
                }

                if (process.env.NODE_ENV === 'development') {
                    const b2 = new THREE.Box3().setFromObject(model);
                    console.log('[CowHealthViewer] Bounds finales (después de elevar y escalar):', {
                        xMin: b2.min.x.toFixed(3), xMax: b2.max.x.toFixed(3),
                        yMin: b2.min.y.toFixed(3), yMax: b2.max.y.toFixed(3),
                        zMin: b2.min.z.toFixed(3), zMax: b2.max.z.toFixed(3),
                    });
                }

                model.traverse((child) => {
                    if ((child as THREE.Mesh).isMesh) {
                        const mesh = child as THREE.Mesh;
                        mesh.material = holoMat;
                        mesh.renderOrder = 1;
                        const wc = new THREE.Mesh(mesh.geometry, wireMat);
                        wc.renderOrder = 2;
                        mesh.parent?.add(wc);
                    }
                });

                scene.add(model);
            },
            undefined,
            (err) => console.error('[CowHealthViewer] Error al cargar /cow.glb:', err)
        );

        let rafId: number;
        const startTime = performance.now();
        const animate = () => {
            rafId = requestAnimationFrame(animate);
            const t = (performance.now() - startTime) / 1000;

            holoMat.uniforms.uTime.value = t;
            ringMat.opacity = 0.20;

            const pos = pGeo.attributes.position as THREE.BufferAttribute;
            for (let i = 0; i < N; i++) {
                const y = pos.getY(i) + 0.002;
                pos.setY(i, y > 1.8 ? 0 : y);
            }
            pos.needsUpdate = true;

            controls.update();
            renderer.render(scene, camera);
        };
        animate();

        const onResize = () => {
            const w = container.clientWidth;
            const h = container.clientHeight;
            camera.aspect = w / h;
            camera.updateProjectionMatrix();
            renderer.setSize(w, h);
        };
        window.addEventListener('resize', onResize);

        return () => {
            cancelAnimationFrame(rafId);
            window.removeEventListener('resize', onResize);
            controls.dispose();
            renderer.dispose();
            if (container.contains(renderer.domElement)) container.removeChild(renderer.domElement);
        };
    }, [status]);

    return <div ref={mountRef} style={{ width: '100%', height: '100%' }} />;
}

// ─────────────────────────────────────────────
// CARD
// ─────────────────────────────────────────────
function CowCard({ cow, isSelected, onClick }: { cow: CowConfig; isSelected: boolean; onClick: () => void }) {
    const meta = STATUS_META[cow.status];

    return (
        <button
            onClick={onClick}
            className={`
                relative p-4 rounded-xl text-left transition-all duration-200
                ${isSelected
                    ? `bg-gradient-to-br from-[${meta.baseColor}1a] to-transparent border border-[${meta.baseColor}55] shadow-lg`
                    : 'bg-[#08121d] border border-[#ffffff0a] hover:border-[#ffffff1a]'
                }
            `}
        >
            <div className="flex items-center justify-between mb-1">
                <span className={`font-bold text-sm ${isSelected ? 'text-white' : 'text-white/70'}`}>{cow.name}</span>
                <span className="text-xs text-white/30 font-mono">#{cow.id}</span>
            </div>
            <p className={`text-xs ${isSelected ? 'text-white/60' : 'text-white/40'}`}>{meta.description}</p>
            <div className="absolute top-4 right-4 w-2 h-2 rounded-full" style={{ backgroundColor: meta.baseColor }} />
        </button>
    );
}

/**
 * Visor para una sola vaca, ideal para páginas de detalle
 */
export function SingleCowViewer({ status }: { status: CowHealthStatus }) {
    const meta = STATUS_META[status];

    return (
        <div className="relative w-full h-[400px] bg-[#020b11] rounded-3xl overflow-hidden border border-[#ffffff0a] shadow-2xl">
            <CowCanvas status={status} />

            {/* Overlay Info */}
            <div className="absolute bottom-6 left-6 right-6 flex items-end justify-between pointer-events-none">
                <div>
                    <h3 className="text-white text-xl font-bold mb-1 flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full animate-pulse" style={{ backgroundColor: meta.baseColor }} />
                        {meta.label}
                    </h3>
                    <p className="text-white/40 text-sm">{meta.description}</p>
                </div>
            </div>
        </div>
    );
}

// ─────────────────────────────────────────────
// PRINCIPAL
// ─────────────────────────────────────────────
const DEFAULT_COWS: CowConfig[] = [
    { id: 'A-001', name: 'Lola', status: 'healthy' },
    { id: 'A-002', name: 'Mora', status: 'mastitis' },
    { id: 'A-003', name: 'Dulce', status: 'fever' },
    { id: 'A-004', name: 'Bonita', status: 'estrus' },
    { id: 'A-005', name: 'Negra', status: 'digestive' },
];

export default function CowHealthViewer({ cows = DEFAULT_COWS }: { cows?: CowConfig[] }) {
    const [selectedCow, setSelectedCow] = useState<CowConfig>(cows[0] || DEFAULT_COWS[0]);

    return (
        <div className="flex flex-col lg:flex-row gap-6 p-6 bg-[#01080e] min-h-[500px] rounded-3xl border border-[#ffffff05]">
            {/* Sidebar con lista de vacas */}
            <div className="w-full lg:w-80 flex flex-col gap-3">
                <div className="px-2 mb-2">
                    <h2 className="text-white text-lg font-bold">Monitor Grupal</h2>
                    <p className="text-white/30 text-xs uppercase tracking-widest">Seleccione unidad</p>
                </div>

                <div className="flex flex-col gap-2 overflow-y-auto max-h-[600px] pr-2 custom-scrollbar">
                    {cows.map((cow) => (
                        <CowCard
                            key={cow.id}
                            cow={cow}
                            isSelected={selectedCow.id === cow.id}
                            onClick={() => setSelectedCow(cow)}
                        />
                    ))}
                </div>
            </div>

            {/* Visor Principal */}
            <div className="flex-1 relative min-h-[400px]">
                <SingleCowViewer status={selectedCow.status} />
            </div>
        </div>
    );
}