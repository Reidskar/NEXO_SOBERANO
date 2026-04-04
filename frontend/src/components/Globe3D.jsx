import { useEffect, useRef, useState } from 'react';

/**
 * Globe3D — esfera de puntos 3D con rotación, atmósfera y pulse en alertas.
 * WebGL puro, sin dependencias externas.
 *
 * Props:
 *  - size: número, tamaño en px del canvas (default 420)
 *  - color: hex string del color base (default '#00e5ff')
 *  - speed: velocidad de rotación (default 0.003)
 *  - alerting: boolean — activa pulse rojo cuando hay alerta crítica
 *  - pulseColor: hex del color pulse (default '#ef4444')
 */
export default function Globe3D({
  size = 420,
  color = '#00e5ff',
  speed = 0.003,
  alerting = false,
  pulseColor = '#ef4444',
}) {
  const canvasRef = useRef(null);
  // Expose alerting state via ref so the animation loop reads it without re-creating GL context
  const alertingRef = useRef(alerting);
  useEffect(() => { alertingRef.current = alerting; }, [alerting]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const gl = canvas.getContext('webgl', { antialias: true, alpha: true });
    if (!gl) return;

    canvas.width = size;
    canvas.height = size;

    // ── Vertex Shader — size includes pulse scale uniform ────────────────────
    const vsSource = `
      attribute vec3 aPos;
      uniform mat4 uMVP;
      uniform float uSize;
      uniform float uPulse;
      varying float vAlpha;
      varying float vZ;
      void main(){
        vec4 p = uMVP * vec4(aPos, 1.0);
        gl_Position = p;
        float depth = 1.0 / (1.0 + p.z * 0.25);
        gl_PointSize = (uSize + uPulse * 1.5) * depth;
        vAlpha = 0.55 + 0.45 * aPos.y;
        vZ = p.z;
      }
    `;
    // ── Fragment Shader — soft circle with glow core ─────────────────────────
    const fsSource = `
      precision mediump float;
      uniform vec3 uColor;
      uniform vec3 uPulseColor;
      uniform float uPulse;
      varying float vAlpha;
      void main(){
        float d = length(gl_PointCoord - 0.5);
        if(d > 0.5) discard;
        // Soft glow falloff
        float core = smoothstep(0.45, 0.05, d);
        float glow = smoothstep(0.5, 0.25, d) * 0.4;
        float a = (core + glow) * vAlpha;
        // Mix alert color on pulse
        vec3 col = mix(uColor, uPulseColor, uPulse * 0.7);
        gl_FragColor = vec4(col, a);
      }
    `;

    // ── Atmosphere pass vertex shader (large translucent points) ─────────────
    const vsAtmo = `
      attribute vec3 aPos;
      uniform mat4 uMVP;
      varying float vAlpha;
      void main(){
        vec4 p = uMVP * vec4(aPos, 1.0);
        gl_Position = p;
        gl_PointSize = 14.0 / (1.0 + p.z * 0.6);
        vAlpha = 0.08 * (0.5 + 0.5 * aPos.y);
      }
    `;
    const fsAtmo = `
      precision mediump float;
      uniform vec3 uColor;
      varying float vAlpha;
      void main(){
        float d = length(gl_PointCoord - 0.5);
        if(d > 0.5) discard;
        float a = smoothstep(0.5, 0.0, d) * vAlpha;
        gl_FragColor = vec4(uColor, a);
      }
    `;

    const compile = (type, src) => {
      const s = gl.createShader(type);
      gl.shaderSource(s, src);
      gl.compileShader(s);
      return s;
    };

    // Track shaders for cleanup
    const shaders = [];
    const buildProg = (vs, fs) => {
      const vsShader = compile(gl.VERTEX_SHADER,   vs);
      const fsShader = compile(gl.FRAGMENT_SHADER, fs);
      shaders.push(vsShader, fsShader);
      const p = gl.createProgram();
      gl.attachShader(p, vsShader);
      gl.attachShader(p, fsShader);
      gl.linkProgram(p);
      return p;
    };

    const prog     = buildProg(vsSource, fsSource);
    const progAtmo = buildProg(vsAtmo,   fsAtmo);

    // ── Generate sphere points ───────────────────────────────────────────────
    const pts = [];
    const N = 480; // 480 Fibonacci points for denser, crisper sphere
    for (let i = 0; i < N; i++) {
      const phi   = Math.acos(1 - 2 * (i + 0.5) / N);
      const theta = Math.PI * (1 + Math.sqrt(5)) * i;
      pts.push(
        Math.sin(phi) * Math.cos(theta),
        Math.cos(phi),
        Math.sin(phi) * Math.sin(theta)
      );
    }
    // Equator ring accent (denser)
    for (let i = 0; i < 80; i++) {
      const t = (i / 80) * Math.PI * 2;
      pts.push(Math.cos(t), 0, Math.sin(t));
    }
    // Prime meridian accent
    for (let i = 0; i < 60; i++) {
      const t = (i / 60) * Math.PI * 2;
      pts.push(0, Math.cos(t), Math.sin(t));
    }
    // Second meridian (90°) accent
    for (let i = 0; i < 60; i++) {
      const t = (i / 60) * Math.PI * 2;
      pts.push(Math.cos(t), Math.sin(t), 0);
    }
    // Polar rings
    for (let lat = 30; lat <= 60; lat += 30) {
      const r2 = Math.cos(lat * Math.PI / 180);
      const y2 = Math.sin(lat * Math.PI / 180);
      for (let i = 0; i < 48; i++) {
        const t = (i / 48) * Math.PI * 2;
        pts.push(r2 * Math.cos(t), y2, r2 * Math.sin(t));
        pts.push(r2 * Math.cos(t), -y2, r2 * Math.sin(t));
      }
    }

    // Shared VBO
    const vbo = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(pts), gl.STATIC_DRAW);

    // Setup main program attributes
    gl.useProgram(prog);
    const aPos   = gl.getAttribLocation(prog, 'aPos');
    const uMVP   = gl.getUniformLocation(prog, 'uMVP');
    const uColor = gl.getUniformLocation(prog, 'uColor');
    const uSize  = gl.getUniformLocation(prog, 'uSize');
    const uPulse = gl.getUniformLocation(prog, 'uPulse');
    const uPulseColor = gl.getUniformLocation(prog, 'uPulseColor');

    // Setup atmosphere program attributes
    const aPosAtmo  = gl.getAttribLocation(progAtmo, 'aPos');
    const uMVPAtmo  = gl.getUniformLocation(progAtmo, 'uMVP');
    const uColAtmo  = gl.getUniformLocation(progAtmo, 'uColor');

    const parseHex = (hex) => [
      parseInt(hex.slice(1,3),16)/255,
      parseInt(hex.slice(3,5),16)/255,
      parseInt(hex.slice(5,7),16)/255,
    ];
    const [cr, cg, cb] = parseHex(color);
    const [pr, pg, pb] = parseHex(pulseColor);

    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    gl.viewport(0, 0, size, size);

    // ── Matrix helpers ───────────────────────────────────────────────────────
    const identity = () => {
      const m = new Float32Array(16);
      m[0] = m[5] = m[10] = m[15] = 1;
      return m;
    };
    const ortho = (out, l, r, b2, t, n, f) => {
      out[0]=2/(r-l); out[5]=2/(t-b2); out[10]=-2/(f-n);
      out[12]=-(r+l)/(r-l); out[13]=-(t+b2)/(t-b2); out[14]=-(f+n)/(f-n); out[15]=1;
    };
    const rotY = (out, a) => {
      out[0]=Math.cos(a); out[2]=Math.sin(a); out[8]=-Math.sin(a); out[10]=Math.cos(a);
    };
    const rotX = (out, a) => {
      out[5]=Math.cos(a); out[6]=-Math.sin(a); out[9]=Math.sin(a); out[10]=Math.cos(a);
    };
    const mul = (a, b) => {
      const o = new Float32Array(16);
      for (let i=0;i<4;i++) for (let j=0;j<4;j++)
        for (let k=0;k<4;k++) o[j*4+i]+=a[k*4+i]*b[j*4+k];
      return o;
    };

    const proj = identity();
    ortho(proj, -1.45, 1.45, -1.45, 1.45, -2, 2);

    let angle = 0, tiltAngle = 0.3;
    let pulseAnim = 0; // 0..1 oscillation driven by sin
    // Rate at which pulse fades when not alerting (frames per step)
    const PULSE_DECAY_RATE = 0.02;
    let raf;

    const draw = () => {
      angle += speed;
      tiltAngle = 0.28 + Math.sin(angle * 0.25) * 0.07;

      // Pulse oscillation: when alerting → fast sin wave amplitude 1, else decay to 0
      if (alertingRef.current) {
        pulseAnim = 0.5 + 0.5 * Math.sin(angle * 8);
      } else {
        pulseAnim = Math.max(0, pulseAnim - PULSE_DECAY_RATE);
      }

      gl.clear(gl.COLOR_BUFFER_BIT);

      const ry = identity(); const rx = identity();
      rotY(ry, angle);
      rotX(rx, tiltAngle);
      const mvp = mul(proj, mul(rx, ry));

      // ── Pass 1: Atmosphere (large blurry points) ─────────────────────────
      gl.useProgram(progAtmo);
      gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
      gl.enableVertexAttribArray(aPosAtmo);
      gl.vertexAttribPointer(aPosAtmo, 3, gl.FLOAT, false, 0, 0);
      gl.uniformMatrix4fv(uMVPAtmo, false, mvp);
      // Atmosphere color: base color tinted
      const atmoR = alertingRef.current ? pr * 0.4 + cr * 0.6 : cr;
      const atmoG = alertingRef.current ? pg * 0.4 + cg * 0.6 : cg;
      const atmoB = alertingRef.current ? pb * 0.4 + cb * 0.6 : cb;
      gl.uniform3f(uColAtmo, atmoR, atmoG, atmoB);
      gl.drawArrays(gl.POINTS, 0, pts.length / 3);

      // ── Pass 2: Main sphere points ────────────────────────────────────────
      gl.useProgram(prog);
      gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
      gl.enableVertexAttribArray(aPos);
      gl.vertexAttribPointer(aPos, 3, gl.FLOAT, false, 0, 0);
      gl.uniformMatrix4fv(uMVP, false, mvp);
      gl.uniform3f(uColor, cr, cg, cb);
      gl.uniform3f(uPulseColor, pr, pg, pb);
      gl.uniform1f(uPulse, pulseAnim);
      gl.uniform1f(uSize, 2.8 + pulseAnim * 0.6);
      gl.drawArrays(gl.POINTS, 0, pts.length / 3);

      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => {
      cancelAnimationFrame(raf);
      // Clean up all compiled shaders first, then programs and buffer
      shaders.forEach(s => gl.deleteShader(s));
      gl.deleteBuffer(vbo);
      gl.deleteProgram(prog);
      gl.deleteProgram(progAtmo);
    };
  }, [size, color, speed, pulseColor]);

  // CSS drop-shadow transitions color when alerting
  const shadowColor = alerting
    ? 'rgba(239,68,68,0.5)'
    : 'rgba(0,229,255,0.35)';

  return (
    <canvas
      ref={canvasRef}
      style={{
        width: size, height: size,
        display: 'block',
        filter: `drop-shadow(0 0 40px ${shadowColor}) drop-shadow(0 0 80px ${shadowColor.replace('0.5','0.15').replace('0.35','0.12')})`,
        background: 'transparent',
        userSelect: 'none',
        pointerEvents: 'none',
        transition: 'filter 0.8s ease',
      }}
    />
  );
}
