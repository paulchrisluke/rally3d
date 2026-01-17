import * as THREE from "three";

export function createBall() {
  const geometry = new THREE.SphereGeometry(0.033, 16, 16);
  const material = new THREE.MeshStandardMaterial({ color: 0xf4d03f });
  const mesh = new THREE.Mesh(geometry, material);
  return mesh;
}
