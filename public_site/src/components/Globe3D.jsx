/**
 * Globe3D — Globo terrestre 3D interactivo
 * Three.js via @react-three/fiber + @react-three/drei
 */
import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Sphere, Points, PointMaterial } from '@react-three/drei'
import * as THREE from 'three'

// Puntos de calor geopolítico (lat/lon → 3D)
const HOT_SPOTS = [
  { name: 'Taiwán',    lat: 25.0,  lon: 121.5 },
  { name: 'Ucrania',   lat: 49.0,  lon: 32.0  },
  { name: 'Irán',      lat: 32.0,  lon: 53.0  },
  { name: 'Gaza',      lat: 31.5,  lon: 34.5  },
  { name: 'Venezuela', lat: 8.0,   lon: -66.0 },
  { name: 'Corea N.',  lat: 40.0,  lon: 127.0 },
  { name: 'Sudán',     lat: 12.0,  lon: 30.0  },
  { name: 'Myanmar',   lat: 21.0,  lon: 96.0  },
  { name: 'Etiopía',   lat: 9.0,   lon: 40.0  },
  { name: 'Sahel',     lat: 15.0,  lon: -0.0  },
]

function latLonToVec3(lat, lon, r = 1.02) {
  const phi   = (90 - lat)  * (Math.PI / 180)
  const theta = (lon + 180) * (Math.PI / 180)
  return new THREE.Vector3(
    -r * Math.sin(phi) * Math.cos(theta),
     r * Math.cos(phi),
     r * Math.sin(phi) * Math.sin(theta)
  )
}

// Partículas de fondo (campo estelar)
function StarField() {
  const positions = useMemo(() => {
    const arr = new Float32Array(3000 * 3)
    for (let i = 0; i < 3000; i++) {
      arr[i * 3]     = (Math.random() - 0.5) * 60
      arr[i * 3 + 1] = (Math.random() - 0.5) * 60
      arr[i * 3 + 2] = (Math.random() - 0.5) * 60
    }
    return arr
  }, [])
  return (
    <Points positions={positions}>
      <PointMaterial size={0.03} color="#c8a96e" transparent opacity={0.4} sizeAttenuation />
    </Points>
  )
}

// Puntos de zona caliente pulsantes
function HotSpotMarker({ lat, lon }) {
  const meshRef = useRef()
  const pos = latLonToVec3(lat, lon)
  useFrame(({ clock }) => {
    if (meshRef.current) {
      const s = 1 + 0.4 * Math.sin(clock.getElapsedTime() * 2.5 + lat)
      meshRef.current.scale.setScalar(s)
      meshRef.current.material.opacity = 0.5 + 0.3 * Math.sin(clock.getElapsedTime() * 2 + lon)
    }
  })
  return (
    <mesh ref={meshRef} position={[pos.x, pos.y, pos.z]}>
      <sphereGeometry args={[0.018, 8, 8]} />
      <meshBasicMaterial color="#ff4444" transparent opacity={0.7} />
    </mesh>
  )
}

// Líneas de latitud (wireframe atmosférico)
function GlobeGrid() {
  const geo = useMemo(() => new THREE.SphereGeometry(1.001, 36, 18), [])
  return (
    <mesh geometry={geo}>
      <meshBasicMaterial color="#00d4ff" wireframe transparent opacity={0.04} />
    </mesh>
  )
}

// El globo principal
function GlobeMesh() {
  const globeRef = useRef()
  const atmosRef = useRef()

  useFrame(({ clock }) => {
    if (globeRef.current) globeRef.current.rotation.y = clock.getElapsedTime() * 0.06
    if (atmosRef.current) atmosRef.current.rotation.y = clock.getElapsedTime() * 0.04
  })

  return (
    <group ref={globeRef}>
      {/* Core sphere */}
      <Sphere args={[1, 64, 64]}>
        <meshStandardMaterial
          color="#0a1628"
          emissive="#001133"
          emissiveIntensity={0.4}
          roughness={0.9}
          metalness={0.1}
        />
      </Sphere>

      {/* Wire grid */}
      <GlobeGrid />

      {/* Atmósfera exterior */}
      <mesh ref={atmosRef}>
        <sphereGeometry args={[1.08, 32, 32]} />
        <meshBasicMaterial color="#00d4ff" transparent opacity={0.035} side={THREE.BackSide} />
      </mesh>

      {/* Puntos calientes */}
      {HOT_SPOTS.map(h => (
        <HotSpotMarker key={h.name} lat={h.lat} lon={h.lon} />
      ))}
    </group>
  )
}

export default function Globe3D({ style }) {
  return (
    <Canvas
      camera={{ position: [0, 0, 2.8], fov: 45 }}
      style={{ background: 'transparent', ...style }}
      gl={{ antialias: true, alpha: true }}
    >
      <ambientLight intensity={0.3} />
      <pointLight position={[5, 5, 5]} intensity={1.2} color="#c8a96e" />
      <pointLight position={[-5, -3, -5]} intensity={0.4} color="#003366" />
      <StarField />
      <GlobeMesh />
    </Canvas>
  )
}
