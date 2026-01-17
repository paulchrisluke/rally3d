import * as THREE from "three";

const DEFAULT_DIMS = {
  half_width_singles: 4.115,
  half_length: 11.885,
  net_height: 0.914
};

export function createCourt(courtData) {
  const dims = (courtData && courtData.court_dims_m) || DEFAULT_DIMS;
  const halfWidth = dims.half_width_singles || DEFAULT_DIMS.half_width_singles;
  const halfLength = dims.half_length || DEFAULT_DIMS.half_length;
  const netHeight = dims.net_height || DEFAULT_DIMS.net_height;

  const group = new THREE.Group();

  const planeGeometry = new THREE.PlaneGeometry(halfWidth * 2, halfLength * 2, 1, 1);
  const planeMaterial = new THREE.MeshStandardMaterial({
    color: 0x4d8a5a,
    roughness: 0.9,
    metalness: 0.0
  });
  const plane = new THREE.Mesh(planeGeometry, planeMaterial);
  plane.rotation.x = -Math.PI / 2;
  group.add(plane);

  const lineMaterial = new THREE.LineBasicMaterial({ color: 0xf2f2f2 });
  const serviceLine = 6.4;

  const lines = [
    [
      [-halfWidth, -halfLength],
      [halfWidth, -halfLength]
    ],
    [
      [-halfWidth, halfLength],
      [halfWidth, halfLength]
    ],
    [
      [-halfWidth, -halfLength],
      [-halfWidth, halfLength]
    ],
    [
      [halfWidth, -halfLength],
      [halfWidth, halfLength]
    ],
    [
      [-halfWidth, -serviceLine],
      [halfWidth, -serviceLine]
    ],
    [
      [-halfWidth, serviceLine],
      [halfWidth, serviceLine]
    ],
    [
      [0, -serviceLine],
      [0, serviceLine]
    ],
    [
      [-halfWidth, 0],
      [halfWidth, 0]
    ]
  ];

  lines.forEach((segment) => {
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array([
      segment[0][0],
      0.01,
      segment[0][1],
      segment[1][0],
      0.01,
      segment[1][1]
    ]);
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    const line = new THREE.Line(geometry, lineMaterial);
    group.add(line);
  });

  const netGeometry = new THREE.PlaneGeometry(halfWidth * 2, netHeight, 1, 1);
  const netMaterial = new THREE.MeshStandardMaterial({
    color: 0xffffff,
    transparent: true,
    opacity: 0.6,
    side: THREE.DoubleSide
  });
  const net = new THREE.Mesh(netGeometry, netMaterial);
  net.position.set(0, netHeight / 2, 0);
  group.add(net);

  return group;
}
