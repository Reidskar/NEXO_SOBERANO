import React, { useRef, useEffect } from 'react';
import * as THREE from 'three';

/**
 * ImpactScene — Phase 13 Pilar 6
 * Mini Three.js canvas showing the type of infrastructure that was hit.
 * Plays a 4-second sequence: normal → explosion → destroyed.
 */

const INFRASTRUCTURE_TYPES = {
  air_base:       buildAirBase,
  oil_refinery:   buildOilRefinery,
  naval_port:     buildNavalPort,
  missile_battery: buildMissileBattery,
  radar:          buildRadar,
  building:       buildBuilding,
  airbase:        buildAirBase,
  military:       buildMissileBattery,
  strike:         buildBuilding,
  naval_movement: buildNavalPort,
};

function buildAirBase(scene) {
  const mat = new THREE.MeshBasicMaterial({ color: 0x06b6d4, wireframe: true });
  // Runway
  const runway = new THREE.Mesh(new THREE.BoxGeometry(8, 0.1, 1.2), new THREE.MeshBasicMaterial({ color: 0x334155 }));
  runway.position.y = 0;
  scene.add(runway);
  // Hangars
  for (let i = -2; i <= 2; i++) {
    const hangar = new THREE.Mesh(new THREE.BoxGeometry(1, 0.8, 1.5), mat);
    hangar.position.set(i * 1.5, 0.4, 2);
    scene.add(hangar);
  }
  // Control tower
  const tower = new THREE.Mesh(new THREE.BoxGeometry(0.4, 2, 0.4), mat);
  tower.position.set(-3, 1, 2);
  scene.add(tower);
}

function buildOilRefinery(scene) {
  const mat = new THREE.MeshBasicMaterial({ color: 0xf97316, wireframe: true });
  for (let i = -2; i <= 2; i++) {
    const tank = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.5, 2, 8), mat);
    tank.position.set(i * 1.4, 1, 0);
    scene.add(tank);
  }
  const pipe = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.1, 8, 6), new THREE.MeshBasicMaterial({ color: 0x475569 }));
  pipe.rotation.z = Math.PI / 2;
  pipe.position.y = 0.5;
  scene.add(pipe);
}

function buildNavalPort(scene) {
  const mat = new THREE.MeshBasicMaterial({ color: 0x06b6d4, wireframe: true });
  // Pier
  const pier = new THREE.Mesh(new THREE.BoxGeometry(8, 0.2, 2), new THREE.MeshBasicMaterial({ color: 0x1e293b }));
  pier.position.y = -0.1;
  scene.add(pier);
  // Ship hull
  const hull = new THREE.Mesh(new THREE.BoxGeometry(3, 0.6, 1), mat);
  hull.position.set(0, 0.3, 0);
  scene.add(hull);
  // Bridge
  const bridge = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.8, 0.8), mat);
  bridge.position.set(-0.5, 1, 0);
  scene.add(bridge);
  // Mast
  const mast = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 1.5, 4), mat);
  mast.position.set(-0.5, 1.8, 0);
  scene.add(mast);
}

function buildMissileBattery(scene) {
  const mat = new THREE.MeshBasicMaterial({ color: 0xef4444, wireframe: true });
  // Launcher tubes pointing up-diagonal
  for (let i = -1; i <= 1; i++) {
    const tube = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.15, 2, 6), mat);
    tube.rotation.z = Math.PI / 5;
    tube.position.set(i * 1.2, 0.8, 0);
    scene.add(tube);
  }
  // Base vehicle
  const vehicle = new THREE.Mesh(new THREE.BoxGeometry(4, 0.5, 1.5), new THREE.MeshBasicMaterial({ color: 0x365314 }));
  vehicle.position.y = 0.25;
  scene.add(vehicle);
}

function buildRadar(scene) {
  const mat = new THREE.MeshBasicMaterial({ color: 0xa855f7, wireframe: true });
  const dome = new THREE.Mesh(new THREE.SphereGeometry(1.5, 12, 6, 0, Math.PI * 2, 0, Math.PI / 2), mat);
  dome.position.y = 0;
  scene.add(dome);
  const base = new THREE.Mesh(new THREE.CylinderGeometry(0.6, 0.8, 0.5, 8), new THREE.MeshBasicMaterial({ color: 0x1e293b }));
  base.position.y = -0.25;
  scene.add(base);
}

function buildBuilding(scene) {
  const mat = new THREE.MeshBasicMaterial({ color: 0x94a3b8, wireframe: true });
  for (let i = -1.5; i <= 1.5; i++) {
    const h = 1.5 + Math.abs(i);
    const bld = new THREE.Mesh(new THREE.BoxGeometry(0.8, h, 0.8), mat);
    bld.position.set(i * 1.3, h / 2, 0);
    scene.add(bld);
  }
}

// ─── Explosion Particles ─────────────────────────────────────────────────────
function spawnExplosion(scene) {
  const particles = [];
  for (let i = 0; i < 60; i++) {
    const p = new THREE.Mesh(
      new THREE.SphereGeometry(0.05 + Math.random() * 0.1, 4, 4),
      new THREE.MeshBasicMaterial({
        color: Math.random() > 0.5 ? 0xff4444 : 0xff8800,
        transparent: true, opacity: 1,
      })
    );
    p.position.set(
      (Math.random() - 0.5) * 2,
      Math.random() * 2,
      (Math.random() - 0.5) * 2
    );
    p.userData.vel = new THREE.Vector3(
      (Math.random() - 0.5) * 0.12,
      Math.random() * 0.08 + 0.02,
      (Math.random() - 0.5) * 0.12
    );
    scene.add(p);
    particles.push(p);
  }
  return particles;
}

export default function ImpactScene({ eventType = 'strike', targetType, style = {} }) {
  const mountRef = useRef(null);
  const animRef  = useRef(null);

  useEffect(() => {
    if (!mountRef.current) return;

    const W = mountRef.current.clientWidth  || 380;
    const H = mountRef.current.clientHeight || 200;

    // ── Renderer ─────────────────────────────────────────────────────────
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(W, H);
    renderer.setPixelRatio(window.devicePixelRatio);
    mountRef.current.appendChild(renderer.domElement);

    // ── Scene & Camera ───────────────────────────────────────────────────
    const scene  = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, W / H, 0.1, 100);
    camera.position.set(0, 4, 10);
    camera.lookAt(0, 1, 0);

    scene.add(new THREE.AmbientLight(0xffffff, 0.3));
    const dLight = new THREE.DirectionalLight(0x06b6d4, 1.5);
    dLight.position.set(5, 10, 5);
    scene.add(dLight);

    // Grid floor
    scene.add(new THREE.GridHelper(16, 16, 0x1e293b, 0x0f172a));

    // ── Build infrastructure ─────────────────────────────────────────────
    const buildFn = INFRASTRUCTURE_TYPES[targetType] || INFRASTRUCTURE_TYPES[eventType] || buildBuilding;
    buildFn(scene);

    // ── Animation phases ─────────────────────────────────────────────────
    let phase     = 'normal';   // normal → explosion → destroyed
    let elapsed   = 0;
    let particles = [];
    let frame     = 0;

    const animate = () => {
      animRef.current = requestAnimationFrame(animate);
      elapsed += 0.016;
      frame++;

      // Phase transitions
      if (phase === 'normal' && elapsed > 1.5) {
        phase = 'explosion';
        particles = spawnExplosion(scene);
        // Remove building meshes to simulate destruction
        scene.children
          .filter(c => c.isMesh && !(c.geometry instanceof THREE.PlaneGeometry))
          .forEach(c => { c.material.opacity = 1; c.material.transparent = true; });
      }

      if (phase === 'explosion') {
        // Animate particles
        particles.forEach(p => {
          p.position.add(p.userData.vel);
          p.userData.vel.y -= 0.003;
          p.material.opacity = Math.max(0, p.material.opacity - 0.018);
          p.scale.multiplyScalar(0.98);
        });
        if (elapsed > 3.5) phase = 'done';
      }

      // Gentle camera orbit
      camera.position.x = Math.sin(frame * 0.005) * 10;
      camera.position.z = Math.cos(frame * 0.005) * 10;
      camera.lookAt(0, 1, 0);

      renderer.render(scene, camera);
    };

    animate();

    return () => {
      cancelAnimationFrame(animRef.current);
      renderer.dispose();
      if (mountRef.current && renderer.domElement.parentNode === mountRef.current) {
        mountRef.current.removeChild(renderer.domElement);
      }
    };
  }, [eventType, targetType]);

  return (
    <div
      ref={mountRef}
      style={{
        width: '100%',
        height: 200,
        borderRadius: 8,
        overflow: 'hidden',
        border: '1px solid rgba(6,182,212,0.2)',
        background: '#020917',
        position: 'relative',
        ...style,
      }}
    >
      <div style={{
        position: 'absolute', top: 6, left: 8, zIndex: 10,
        fontSize: 9, color: '#06b6d4', fontFamily: 'monospace', letterSpacing: 1,
        textShadow: '0 0 8px #06b6d4',
      }}>
        ▶ SIMULACIÓN 3D — {(targetType || eventType || 'TARGET').toUpperCase()}
      </div>
    </div>
  );
}
