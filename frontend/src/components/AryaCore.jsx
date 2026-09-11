import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

/**
 * 3D Interactive Audio/Visual Core (ARYA Holographic Orb)
 * Built with Three.js WebGL. Reacts to agent states:
 * - IDLE: Calm breathing cyan/blue rotation
 * - LISTENING: Dynamic teal waveform oscillation & particle expansion
 * - THINKING: Golden/amber dual-axis vortex and core energy pulsing
 * - EXECUTING: Neon purple/crimson matrix telemetry particle bursts
 * - SPEAKING: Harmonically oscillating soundwave frequency rings
 */
export default function AryaCore({ state = 'idle', audioLevel = 0 }) {
  const mountRef = useRef(null);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || 400;
    const height = container.clientHeight || 400;

    // 1. Scene & Camera
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.z = 7;

    // 2. Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // 3. Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
    scene.add(ambientLight);

    const pointLight = new THREE.PointLight(0x00f2fe, 3, 50);
    pointLight.position.set(0, 0, 0);
    scene.add(pointLight);

    // 4. Central Hologram Core (Wireframe Icosahedron)
    const coreGeo = new THREE.IcosahedronGeometry(1.35, 2);
    const coreMat = new THREE.MeshBasicMaterial({
      color: 0x00f2fe,
      wireframe: true,
      transparent: true,
      opacity: 0.65,
    });
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    scene.add(coreMesh);

    // Inner Solid Glow Sphere
    const innerGeo = new THREE.SphereGeometry(0.85, 32, 32);
    const innerMat = new THREE.MeshBasicMaterial({
      color: 0x00a8ff,
      transparent: true,
      opacity: 0.4,
    });
    const innerMesh = new THREE.Mesh(innerGeo, innerMat);
    scene.add(innerMesh);

    // 5. Gyroscopic Orbital Rings
    const createRing = (radius, tube, color) => {
      const geo = new THREE.TorusGeometry(radius, tube, 16, 100);
      const mat = new THREE.MeshBasicMaterial({
        color: color,
        transparent: true,
        opacity: 0.7,
      });
      return new THREE.Mesh(geo, mat);
    };

    const ring1 = createRing(2.0, 0.015, 0x00f2fe);
    const ring2 = createRing(2.35, 0.012, 0x7f00ff);
    const ring3 = createRing(2.7, 0.018, 0x00ffd5);

    ring1.rotation.x = Math.PI / 4;
    ring2.rotation.y = Math.PI / 3;
    ring3.rotation.x = Math.PI / 6;

    scene.add(ring1);
    scene.add(ring2);
    scene.add(ring3);

    // 6. Particle Halo (Stars / Data Sparks)
    const particleCount = 700;
    const particleGeo = new THREE.BufferGeometry();
    const particlePositions = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount * 3; i += 3) {
      const u = Math.random();
      const v = Math.random();
      const theta = u * 2.0 * Math.PI;
      const phi = Math.acos(2.0 * v - 1.0);
      const r = 1.8 + Math.random() * 1.5;

      particlePositions[i] = r * Math.sin(phi) * Math.cos(theta);
      particlePositions[i + 1] = r * Math.sin(phi) * Math.sin(theta);
      particlePositions[i + 2] = r * Math.cos(phi);
    }

    particleGeo.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));

    const particleMat = new THREE.PointsMaterial({
      color: 0x00f2fe,
      size: 0.035,
      transparent: true,
      opacity: 0.75,
      blending: THREE.AdditiveBlending,
    });
    const particles = new THREE.Points(particleGeo, particleMat);
    scene.add(particles);

    // Mouse Interaction
    let mouseX = 0;
    let mouseY = 0;
    const onMouseMove = (e) => {
      const rect = container.getBoundingClientRect();
      mouseX = ((e.clientX - rect.left) / width) * 2 - 1;
      mouseY = -(((e.clientY - rect.top) / height) * 2 - 1);
    };
    container.addEventListener('mousemove', onMouseMove);

    // Window Resize Handler
    const handleResize = () => {
      if (!container) return;
      const newW = container.clientWidth;
      const newH = container.clientHeight;
      camera.aspect = newW / newH;
      camera.updateProjectionMatrix();
      renderer.setSize(newW, newH);
    };
    window.addEventListener('resize', handleResize);

    // 7. Animation Loop
    let animationId;
    let clock = new THREE.Clock();

    const animate = () => {
      animationId = requestAnimationFrame(animate);
      const elapsed = clock.getElapsedTime();

      // State-driven color & speed parameters
      let targetColor = new THREE.Color(0x00f2fe);
      let ringColor2 = new THREE.Color(0x7f00ff);
      let rotSpeed = 0.008;
      let pulseAmp = 0.08;
      let pulseFreq = 2.0;

      if (state === 'listening') {
        targetColor.setHex(0x00ffd5); // Bright Electric Teal
        ringColor2.setHex(0x00f2fe);
        rotSpeed = 0.02;
        pulseAmp = 0.25 + audioLevel * 0.4;
        pulseFreq = 6.0;
      } else if (state === 'thinking') {
        targetColor.setHex(0xf6d365); // Golden Amber
        ringColor2.setHex(0xffaa00);
        rotSpeed = 0.045; // Rapid calculation vortex
        pulseAmp = 0.18;
        pulseFreq = 4.5;
      } else if (state === 'executing') {
        targetColor.setHex(0xa855f7); // Neon Purple
        ringColor2.setHex(0xff0844); // Crimson
        rotSpeed = 0.035;
        pulseAmp = 0.22;
        pulseFreq = 5.0;
      } else if (state === 'speaking') {
        targetColor.setHex(0x38bdf8); // Sky Blue
        ringColor2.setHex(0x00f2fe);
        rotSpeed = 0.015;
        pulseAmp = 0.3 + audioLevel * 0.3;
        pulseFreq = 7.0;
      }

      // Smooth color transitions
      coreMat.color.lerp(targetColor, 0.08);
      innerMat.color.lerp(targetColor, 0.08);
      particleMat.color.lerp(targetColor, 0.08);
      ring1.material.color.lerp(targetColor, 0.08);
      ring2.material.color.lerp(ringColor2, 0.08);
      ring3.material.color.lerp(targetColor, 0.08);

      // Core pulsation
      const scaleFactor = 1 + Math.sin(elapsed * pulseFreq) * pulseAmp;
      coreMesh.scale.set(scaleFactor, scaleFactor, scaleFactor);
      innerMesh.scale.set(scaleFactor * 0.9, scaleFactor * 0.9, scaleFactor * 0.9);

      // Rotations
      coreMesh.rotation.x += rotSpeed;
      coreMesh.rotation.y += rotSpeed * 1.3;

      innerMesh.rotation.x -= rotSpeed * 0.8;
      innerMesh.rotation.y -= rotSpeed * 0.6;

      ring1.rotation.x += rotSpeed * 1.5;
      ring1.rotation.y += rotSpeed * 0.8;

      ring2.rotation.y += rotSpeed * 1.2;
      ring2.rotation.z += rotSpeed * 0.9;

      ring3.rotation.x -= rotSpeed * 1.1;
      ring3.rotation.z += rotSpeed * 1.4;

      particles.rotation.y = elapsed * 0.05;
      particles.rotation.x = elapsed * 0.02;

      // Subtle mouse parallax
      scene.rotation.y += (mouseX * 0.3 - scene.rotation.y) * 0.05;
      scene.rotation.x += (-mouseY * 0.3 - scene.rotation.x) * 0.05;

      renderer.render(scene, camera);
    };

    animate();

    // Cleanup
    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener('resize', handleResize);
      container.removeEventListener('mousemove', onMouseMove);
      renderer.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [state, audioLevel]);

  return (
    <div className="relative w-full h-[360px] md:h-[440px] flex items-center justify-center">
      {/* Three.js Canvas Container */}
      <div ref={mountRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

      {/* Holographic Status Ring Overlay */}
      <div className="absolute pointer-events-none flex flex-col items-center bottom-2">
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-arya-card/80 border border-slate-700/60 backdrop-blur-md">
          <span
            className={`w-2 h-2 rounded-full animate-ping ${
              state === 'idle'
                ? 'bg-amber-500'
                : state === 'listening'
                ? 'bg-emerald-400'
                : state === 'thinking'
                ? 'bg-amber-400'
                : state === 'executing'
                ? 'bg-purple-400'
                : 'bg-sky-400'
            }`}
          />
          <span className="text-xs font-mono uppercase tracking-wider text-slate-300">
            CORE STATE: <strong className="text-white">{state}</strong>
          </span>
        </div>
      </div>
    </div>
  );
}
