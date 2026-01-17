import * as THREE from "three";

const PLAYER_COLORS = {
  A: 0x2f70c0,
  B: 0xe05a4f
};

function createPlayerMesh(color) {
  const group = new THREE.Group();

  const bodyGeometry = new THREE.CylinderGeometry(0.3, 0.3, 1, 16);
  const bodyMaterial = new THREE.MeshStandardMaterial({ color });
  const body = new THREE.Mesh(bodyGeometry, bodyMaterial);
  body.position.y = 0.5;
  group.add(body);

  const headGeometry = new THREE.SphereGeometry(0.15, 16, 16);
  const head = new THREE.Mesh(headGeometry, bodyMaterial);
  head.position.y = 0.95;
  group.add(head);

  group.userData.body = body;
  group.userData.head = head;

  return group;
}

function setPlayerHeight(group, height) {
  const body = group.userData.body;
  const head = group.userData.head;
  const bodyHeight = height * 0.8;

  body.scale.set(1, bodyHeight, 1);
  body.position.y = height * 0.4;
  head.position.y = height * 0.9;
}

export function createPlayerSystem() {
  const group = new THREE.Group();
  const players = new Map();

  function ensurePlayer(id) {
    if (players.has(id)) {
      return players.get(id);
    }
    const color = PLAYER_COLORS[id] || 0x888888;
    const mesh = createPlayerMesh(color);
    players.set(id, mesh);
    group.add(mesh);
    return mesh;
  }

  function update(playersFrame) {
    if (!playersFrame || !Array.isArray(playersFrame.players)) {
      return;
    }
    playersFrame.players.forEach((player) => {
      const mesh = ensurePlayer(player.id);
      mesh.position.set(player.x, 0, player.y);
      setPlayerHeight(mesh, player.height || 1.8);
    });
  }

  return { group, update };
}
