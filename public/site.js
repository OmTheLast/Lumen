const canvas = document.getElementById("orb");
const statusCard = document.querySelector(".status-card");
const localState = document.getElementById("localState");
const localDetail = document.getElementById("localDetail");
const checkLocal = document.getElementById("checkLocal");
const openLocal = document.getElementById("openLocal");
const toast = document.getElementById("toast");
const pointer = { x: 0, y: 0, tx: 0, ty: 0 };
const scene = buildNeuralField();

function showToast(message) {
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add("visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove("visible"), 2200);
}

async function copyText(value) {
  try {
    await navigator.clipboard.writeText(value);
    showToast("Copied to clipboard.");
  } catch {
    showToast("Copy failed. Select the command manually.");
  }
}

async function checkLocalLumen() {
  if (!statusCard || !localState || !localDetail || !openLocal) return;
  localState.textContent = "Checking";
  localDetail.textContent = "Looking for Lumen at 127.0.0.1:8765.";
  statusCard.classList.remove("online", "offline");
  openLocal.setAttribute("aria-disabled", "true");

  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 900);
  try {
    const response = await fetch("http://127.0.0.1:8765/state", {
      cache: "no-store",
      signal: controller.signal,
    });
    const state = await response.json();
    window.clearTimeout(timeout);
    statusCard.classList.add("online");
    localState.textContent = "Online";
    localDetail.textContent = state.message || "Local Lumen console is running.";
    openLocal.removeAttribute("aria-disabled");
  } catch {
    window.clearTimeout(timeout);
    statusCard.classList.add("offline");
    localState.textContent = "Offline";
    localDetail.textContent = "Start Lumen locally, then check again.";
  }
}

function buildNeuralField() {
  const nodes = [];
  const links = [];
  const paths = [];
  let seed = 7;
  const random = () => {
    seed = (seed * 1664525 + 1013904223) >>> 0;
    return seed / 4294967296;
  };

  for (let i = 0; i < 156; i++) {
    const z = 1 - (2 * i + 1) / 156;
    const theta = i * 2.399963 + random() * 0.16;
    const ring = Math.sqrt(1 - z * z);
    const surfaceBias = 0.82 + random() * 0.18;
    nodes.push({
      x: Math.cos(theta) * ring * surfaceBias,
      y: z * 0.92 + Math.sin(theta * 2.1) * 0.025,
      z: Math.sin(theta) * ring * surfaceBias,
      weight: 0.45 + random() * 1.5,
      phase: random() * Math.PI * 2,
      shell: true,
    });
  }

  for (let i = 0; i < 46; i++) {
    const theta = random() * Math.PI * 2;
    const phi = Math.acos(2 * random() - 1);
    const r = 0.18 + Math.pow(random(), 0.7) * 0.54;
    nodes.push({
      x: Math.sin(phi) * Math.cos(theta) * r,
      y: Math.cos(phi) * r * 0.92,
      z: Math.sin(phi) * Math.sin(theta) * r,
      weight: 0.8 + random() * 1.9,
      phase: random() * Math.PI * 2,
      shell: false,
    });
  }

  for (let i = 0; i < nodes.length; i++) {
    const distances = [];
    for (let j = 0; j < nodes.length; j++) {
      if (i === j) continue;
      const a = nodes[i];
      const b = nodes[j];
      const dist = Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
      if (dist < 0.28) distances.push({ index: j, dist });
    }
    distances.sort((a, b) => a.dist - b.dist);
    for (const target of distances.slice(0, nodes[i].shell ? 3 : 5)) {
      if (i < target.index) links.push({ from: i, to: target.index, length: target.dist });
    }
  }

  for (let i = 0; i < 18; i++) {
    const start = Math.floor(random() * nodes.length);
    let current = start;
    const path = [current];
    for (let step = 0; step < 7; step++) {
      const candidates = links
        .filter((link) => link.from === current || link.to === current)
        .map((link) => (link.from === current ? link.to : link.from))
        .filter((index) => !path.includes(index));
      if (!candidates.length) break;
      current = candidates[Math.floor(random() * candidates.length)];
      path.push(current);
    }
    if (path.length > 2) paths.push({ nodes: path, phase: random() * 1.0 });
  }

  return { nodes, links, paths };
}

function tone(alpha, channel = "orange") {
  if (channel === "white") return `rgba(255, 248, 209, ${alpha})`;
  if (channel === "amber") return `rgba(255, 196, 91, ${alpha})`;
  if (channel === "deep") return `rgba(255, 93, 31, ${alpha})`;
  return `rgba(255, 143, 45, ${alpha})`;
}

function rotate(point, time) {
  const ay = time * 0.00042 + pointer.x * 1.05;
  const ax = Math.sin(time * 0.00028) * 0.24 + pointer.y * 0.58;
  const az = Math.cos(time * 0.00021) * 0.18 + pointer.x * pointer.y * 0.12;
  let { x, y, z } = point;

  let c = Math.cos(ay), s = Math.sin(ay);
  [x, z] = [x * c - z * s, x * s + z * c];
  c = Math.cos(ax); s = Math.sin(ax);
  [y, z] = [y * c - z * s, y * s + z * c];
  c = Math.cos(az); s = Math.sin(az);
  [x, y] = [x * c - y * s, x * s + y * c];

  return { x, y, z };
}

function project(point, time, radius) {
  const p = rotate(point, time);
  const depth = 2.35 / (2.35 - p.z);
  return {
    x: p.x * radius * depth,
    y: p.y * radius * depth,
    z: p.z,
    depth,
  };
}

function drawNeuralShell(ctx, time, radius) {
  for (let strand = 0; strand < 11; strand++) {
    const points = [];
    const offset = strand * 0.31;
    for (let i = 0; i <= 128; i++) {
      const t = i / 128;
      const a = t * Math.PI * 2;
      points.push(project({
        x: Math.cos(a + offset) * (0.92 + Math.sin(a * 3 + time * 0.001) * 0.025),
        y: Math.sin(a * (strand % 2 ? 1.0 : 1.7) + offset) * (strand % 3 === 0 ? 0.2 : 0.55),
        z: Math.sin(a + offset * 1.4) * (0.88 - (strand % 4) * 0.07),
      }, time, radius));
    }
    ctx.strokeStyle = tone(0.09 + strand * 0.01, strand % 3 === 0 ? "amber" : "orange");
    ctx.lineWidth = strand % 2 === 0 ? 1.35 : 0.8;
    ctx.beginPath();
    for (const [index, point] of points.entries()) {
      if (index === 0) ctx.moveTo(point.x, point.y);
      else ctx.lineTo(point.x, point.y);
    }
    ctx.stroke();
  }
}

function drawSignals(ctx, projected, time) {
  for (const path of scene.paths) {
    const progress = (time * 0.00018 + path.phase) % 1;
    const segment = Math.floor(progress * (path.nodes.length - 1));
    const local = progress * (path.nodes.length - 1) - segment;
    const a = projected[path.nodes[segment]];
    const b = projected[path.nodes[Math.min(segment + 1, path.nodes.length - 1)]];
    if (!a || !b) continue;
    const x = a.x + (b.x - a.x) * local;
    const y = a.y + (b.y - a.y) * local;
    const pulse = ctx.createRadialGradient(x, y, 0, x, y, 24);
    pulse.addColorStop(0, tone(0.92, "white"));
    pulse.addColorStop(0.25, tone(0.56, "amber"));
    pulse.addColorStop(1, tone(0, "deep"));
    ctx.fillStyle = pulse;
    ctx.beginPath();
    ctx.arc(x, y, 24, 0, Math.PI * 2);
    ctx.fill();
  }
}

function draw(time) {
  if (!canvas) return;
  const rect = canvas.getBoundingClientRect();
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const width = Math.max(1, Math.floor(rect.width * dpr));
  const height = Math.max(1, Math.floor(rect.height * dpr));
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }

  pointer.x += (pointer.tx - pointer.x) * 0.08;
  pointer.y += (pointer.ty - pointer.y) * 0.08;

  const ctx = canvas.getContext("2d");
  const radius = Math.min(width, height) * 0.39;
  ctx.clearRect(0, 0, width, height);
  ctx.save();
  ctx.translate(width / 2, height / 2);

  const backgroundGlow = ctx.createRadialGradient(0, 0, radius * 0.05, 0, 0, radius * 1.22);
  backgroundGlow.addColorStop(0, "rgba(255, 214, 130, 0.16)");
  backgroundGlow.addColorStop(0.62, "rgba(255, 143, 45, 0.06)");
  backgroundGlow.addColorStop(1, "rgba(255, 93, 31, 0)");
  ctx.fillStyle = backgroundGlow;
  ctx.beginPath();
  ctx.arc(0, 0, radius * 1.22, 0, Math.PI * 2);
  ctx.fill();

  ctx.save();
  ctx.strokeStyle = tone(0.3, "amber");
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  ctx.arc(0, 0, radius * 0.99, 0, Math.PI * 2);
  ctx.stroke();
  ctx.strokeStyle = tone(0.13, "orange");
  ctx.lineWidth = 1;
  for (let ring = 0; ring < 3; ring++) {
    ctx.save();
    ctx.rotate(time * (0.00012 + ring * 0.00004) + ring * 0.8);
    ctx.scale(1, 0.34 + ring * 0.18);
    ctx.beginPath();
    ctx.arc(0, 0, radius * (0.74 + ring * 0.1), 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();
  }
  ctx.restore();

  drawNeuralShell(ctx, time, radius);

  const projected = scene.nodes.map((node) => {
    const wave = Math.sin(time * 0.0014 + node.phase) * 0.025;
    return project({ x: node.x + wave, y: node.y, z: node.z - wave }, time, radius * 0.96);
  });

  const sortedLinks = [...scene.links].sort((a, b) => {
    const az = (projected[a.from].z + projected[a.to].z) / 2;
    const bz = (projected[b.from].z + projected[b.to].z) / 2;
    return az - bz;
  });

  for (const link of sortedLinks) {
    const a = projected[link.from];
    const b = projected[link.to];
    const depth = (a.z + b.z + 2.2) / 4.4;
    const alpha = Math.max(0.035, Math.min(0.22, depth * (0.22 - link.length * 0.18)));
    ctx.strokeStyle = tone(alpha, depth > 0.55 ? "amber" : "orange");
    ctx.lineWidth = Math.max(0.45, (0.75 + depth) * Math.max(a.depth, b.depth) * 0.52);
    ctx.beginPath();
    const bend = Math.sin((link.from + link.to) * 0.17 + time * 0.001) * 12;
    ctx.moveTo(a.x, a.y);
    ctx.quadraticCurveTo((a.x + b.x) / 2 + bend, (a.y + b.y) / 2 - bend * 0.6, b.x, b.y);
    ctx.stroke();
  }

  drawSignals(ctx, projected, time);

  for (const [index, point] of projected.entries()) {
    const node = scene.nodes[index];
    const blink = 0.55 + Math.sin(time * 0.002 + node.phase) * 0.35;
    const depth = Math.max(0.22, Math.min(1, (point.z + 1.15) / 2.3));
    const edgeBoost = node.shell ? 0.85 : 1.25;
    const size = (1.15 + node.weight * 0.62) * point.depth * edgeBoost;
    ctx.fillStyle = tone((0.18 + depth * 0.62) * blink, depth > 0.66 ? "white" : "amber");
    ctx.beginPath();
    ctx.arc(point.x, point.y, size, 0, Math.PI * 2);
    ctx.fill();
  }

  const core = project({
    x: Math.sin(time * 0.0011) * 0.08,
    y: Math.cos(time * 0.00135) * 0.08,
    z: Math.sin(time * 0.0016) * 0.15,
  }, time, radius);
  const coreGlow = ctx.createRadialGradient(core.x, core.y, 0, core.x, core.y, radius * 0.22);
  coreGlow.addColorStop(0, "rgba(255, 252, 215, 0.98)");
  coreGlow.addColorStop(0.18, "rgba(255, 195, 91, 0.86)");
  coreGlow.addColorStop(0.54, "rgba(255, 111, 31, 0.28)");
  coreGlow.addColorStop(1, "rgba(255, 93, 31, 0)");
  ctx.fillStyle = coreGlow;
  ctx.beginPath();
  ctx.arc(core.x, core.y, radius * 0.22, 0, Math.PI * 2);
  ctx.fill();

  ctx.restore();
  requestAnimationFrame(draw);
}

window.addEventListener("pointermove", (event) => {
  pointer.tx = (event.clientX / window.innerWidth - 0.5) * 2;
  pointer.ty = (event.clientY / window.innerHeight - 0.5) * 2;
});

document.querySelectorAll("[data-copy]").forEach((button) => {
  button.addEventListener("click", () => copyText(button.dataset.copy || ""));
});

checkLocal?.addEventListener("click", checkLocalLumen);
openLocal?.addEventListener("click", (event) => {
  if (openLocal.getAttribute("aria-disabled") === "true") {
    event.preventDefault();
    showToast("Start Lumen locally first.");
  }
});

checkLocalLumen();
requestAnimationFrame(draw);
