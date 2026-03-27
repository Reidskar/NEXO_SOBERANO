import { useEffect, useRef } from 'react';

/**
 * Globe3D — esfera de puntos 3D con rotación y conexiones.
 * WebGL puro, sin dependencias externas.
 */
export default function Globe3D({ size = 420, color = '#00e5ff', speed = 0.003 }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const gl = canvas.getContext('webgl', { antialias: true, alpha: true });
    if (!gl) return;

    canvas.width = size;
    canvas.height = size;

    // ── Vertex Shader ────────────────────────────────────────────────────────
    const vsSource = `
      attribute vec3 aPos;
      uniform mat4 uMVP;
      uniform float uSize;
      varying float vAlpha;
      void main(){
        vec4 p = uMVP * vec4(aPos, 1.0);
        gl_Position = p;
        gl_PointSize = uSize * (1.0 / (1.0 + p.z * 0.3));
        vAlpha = 0.6 + 0.4 * aPos.z;
      }
    `;
    // ── Fragment Shader ──────────────────────────────────────────────────────
    const fsSource = `
      precision mediump float;
      uniform vec3 uColor;
      varying float vAlpha;
      void main(){
        float d = length(gl_PointCoord - 0.5);
        if(d > 0.5) discard;
        float a = smoothstep(0.5, 0.1, d) * vAlpha;
        gl_FragColor = vec4(uColor, a);
      }
    `;

    const compile = (type, src) => {
      const s = gl.createShader(type);
      gl.shaderSource(s, src); gl.compileShader(s); return s;
    };
    const prog = gl.createProgram();
    gl.attachShader(prog, compile(gl.VERTEX_SHADER, vsSource));
    gl.attachShader(prog, compile(gl.FRAGMENT_SHADER, fsSource));
    gl.linkProgram(prog);
    gl.useProgram(prog);

    // ── Generate sphere points ───────────────────────────────────────────────
    const pts = [];
    const N = 320;
    for (let i = 0; i < N; i++) {
      const phi = Math.acos(1 - 2 * (i + 0.5) / N);
      const theta = Math.PI * (1 + Math.sqrt(5)) * i;
      pts.push(
        Math.sin(phi) * Math.cos(theta),
        Math.cos(phi),
        Math.sin(phi) * Math.sin(theta)
      );
    }
    // Add equator ring accent
    for (let i = 0; i < 64; i++) {
      const t = (i / 64) * Math.PI * 2;
      pts.push(Math.cos(t), 0, Math.sin(t));
    }
    // Add meridian accent
    for (let i = 0; i < 48; i++) {
      const t = (i / 48) * Math.PI * 2;
      pts.push(0, Math.cos(t), Math.sin(t));
    }

    const vbo = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(pts), gl.STATIC_DRAW);

    const aPos = gl.getAttribLocation(prog, 'aPos');
    gl.enableVertexAttribArray(aPos);
    gl.vertexAttribPointer(aPos, 3, gl.FLOAT, false, 0, 0);

    const uMVP   = gl.getUniformLocation(prog, 'uMVP');
    const uColor = gl.getUniformLocation(prog, 'uColor');
    const uSize  = gl.getUniformLocation(prog, 'uSize');

    const r = parseInt(color.slice(1,3),16)/255;
    const g = parseInt(color.slice(3,5),16)/255;
    const b = parseInt(color.slice(5,7),16)/255;
    gl.uniform3f(uColor, r, g, b);
    gl.uniform1f(uSize, 3.2);

    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    gl.viewport(0, 0, size, size);

    // ── Matrix helpers ───────────────────────────────────────────────────────
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

    const proj = new Float32Array(16); proj[0]=proj[5]=proj[10]=proj[15]=1;
    ortho(proj, -1.4, 1.4, -1.4, 1.4, -2, 2);

    let angle = 0, tiltAngle = 0.3, raf;
    const draw = () => {
      angle += speed;
      tiltAngle = 0.3 + Math.sin(angle * 0.3) * 0.08;

      gl.clear(gl.COLOR_BUFFER_BIT);

      const ry = new Float32Array(16); ry[0]=ry[5]=ry[10]=ry[15]=1;
      const rx = new Float32Array(16); rx[0]=rx[5]=rx[10]=rx[15]=1;
      rotY(ry, angle);
      rotX(rx, tiltAngle);
      const mvp = mul(proj, mul(rx, ry));
      gl.uniformMatrix4fv(uMVP, false, mvp);
      gl.drawArrays(gl.POINTS, 0, pts.length / 3);
      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, [size, color, speed]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        width: size, height: size,
        display: 'block',
        filter: 'drop-shadow(0 0 32px rgba(0,229,255,0.35))',
        background: 'transparent',
        userSelect: 'none',
        pointerEvents: 'none',
      }}
    />
  );
}
