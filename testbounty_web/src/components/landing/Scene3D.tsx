"use client";

import { Canvas, useFrame } from '@react-three/fiber';
import { Stars, Sparkles } from '@react-three/drei';
import { useRef, useMemo } from 'react';
import * as THREE from 'three';

// Floating particles
function FloatingParticles() {
    const count = 100;
    const ref = useRef<THREE.Points>(null);

    const positions = useMemo(() => {
        const pos = new Float32Array(count * 3);
        for (let i = 0; i < count; i++) {
            pos[i * 3] = (Math.random() - 0.5) * 30;
            pos[i * 3 + 1] = (Math.random() - 0.5) * 20;
            pos[i * 3 + 2] = (Math.random() - 0.5) * 15 - 5;
        }
        return pos;
    }, []);

    useFrame((state) => {
        if (ref.current) {
            ref.current.rotation.y = state.clock.elapsedTime * 0.02;
            ref.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.1) * 0.1;
        }
    });

    return (
        <points ref={ref}>
            <bufferGeometry>
                <bufferAttribute
                    attach="attributes-position"
                    count={count}
                    array={positions}
                    itemSize={3}
                />
            </bufferGeometry>
            <pointsMaterial
                color="#00D4AA"
                size={0.05}
                transparent
                opacity={0.6}
                sizeAttenuation
            />
        </points>
    );
}

// Neural network nodes
function NeuralNode({ position }: { position: [number, number, number] }) {
    const ref = useRef<THREE.Mesh>(null);

    useFrame((state) => {
        if (ref.current) {
            ref.current.scale.setScalar(0.1 + Math.sin(state.clock.elapsedTime * 2 + position[0]) * 0.03);
        }
    });

    return (
        <mesh ref={ref} position={position}>
            <sphereGeometry args={[0.1, 16, 16]} />
            <meshBasicMaterial color="#00D4AA" />
        </mesh>
    );
}

// Network connections with flowing data
function NetworkConnections() {
    const nodes = useMemo(() => {
        const positions: [number, number, number][] = [];
        for (let i = 0; i < 15; i++) {
            positions.push([
                (Math.random() - 0.5) * 20,
                (Math.random() - 0.5) * 12,
                (Math.random() - 0.5) * 8 - 8
            ]);
        }
        return positions;
    }, []);

    const connections = useMemo(() => {
        const conns: [number, number][] = [];
        nodes.forEach((_, i) => {
            const nearNodes = nodes
                .map((_, j) => j)
                .filter(j => j !== i)
                .sort((a, b) => {
                    const distA = Math.hypot(
                        nodes[a][0] - nodes[i][0],
                        nodes[a][1] - nodes[i][1],
                        nodes[a][2] - nodes[i][2]
                    );
                    const distB = Math.hypot(
                        nodes[b][0] - nodes[i][0],
                        nodes[b][1] - nodes[i][1],
                        nodes[b][2] - nodes[i][2]
                    );
                    return distA - distB;
                })
                .slice(0, 2);
            nearNodes.forEach(j => {
                if (!conns.find(c => (c[0] === i && c[1] === j) || (c[0] === j && c[1] === i))) {
                    conns.push([i, j]);
                }
            });
        });
        return conns;
    }, [nodes]);

    return (
        <group>
            {nodes.map((pos, i) => (
                <NeuralNode key={i} position={pos} />
            ))}
            {connections.map((conn, i) => (
                <line key={i}>
                    <bufferGeometry>
                        <bufferAttribute
                            attach="attributes-position"
                            count={2}
                            array={new Float32Array([...nodes[conn[0]], ...nodes[conn[1]]])}
                            itemSize={3}
                        />
                    </bufferGeometry>
                    <lineBasicMaterial color="#00D4AA" transparent opacity={0.15} />
                </line>
            ))}
        </group>
    );
}

// Grid floor
function GridFloor() {
    return (
        <group position={[0, -6, 0]} rotation={[-Math.PI / 2, 0, 0]}>
            <gridHelper args={[60, 60, '#00D4AA', '#0a1a15']} rotation={[Math.PI / 2, 0, 0]} />
        </group>
    );
}

// Main scene content
function SceneContent() {
    return (
        <>
            <FloatingParticles />
            <NetworkConnections />
            <GridFloor />

            <Stars radius={100} depth={50} count={1500} factor={3} saturation={0} fade speed={0.5} />

            <Sparkles
                count={30}
                scale={15}
                size={2}
                speed={0.2}
                opacity={0.3}
                color="#00D4AA"
            />

            <ambientLight intensity={0.1} />
            <pointLight position={[0, 5, 0]} intensity={0.5} color="#00D4AA" distance={20} />

            <fog attach="fog" args={['#000000', 5, 40]} />
        </>
    );
}

export default function Scene3D() {
    return (
        <div className="absolute inset-0 z-0">
            <Canvas
                camera={{ position: [0, 0, 12], fov: 50 }}
                gl={{ antialias: true, alpha: true }}
                style={{ background: 'transparent' }}
            >
                <SceneContent />
            </Canvas>
        </div>
    );
}
