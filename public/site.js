const canvas = document.getElementById("orb");
const pointer = { x: 0, y: 0, tx: 0, ty: 0 };

function rgba(alpha) {
  return `rgba(255, 143, 45, ${alpha})`;
}

function rotate(point, time) {
  const ay = time * 0.00055 + pointer.x * 1.2;
  const ax = Math.sin(time * 0.00035) * 0.36 + pointer.y * 0.72;
  const az = Math.cos(time * 0.00028) * 0.2;
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
  const depth = 2.55 / (2.55 - p.z);
  return {
    x: p.x * radius * depth,
    y: p.y * radius * depth,
    z: p.z,
    depth,
  };
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
  const radius = Math.min(width, height) * 0.34;
  ctx.clearRect(0, 0, width, height);
  ctx.save();
  ctx.translate(width / 2, height / 2);

  const glow = ctx.createRadialGradient(0, 0, radius * 0.1, 0, 0, radius * 1.28);
  glow.addColorStop(0, "rgba(255, 214, 130, 0.18)");
  glow.addColorStop(0.55, "rgba(255, 143, 45, 0.06)");
  glow.addColorStop(1, "rgba(255, 93, 31, 0)");
  ctx.fillStyle = glow;
  ctx.beginPath();
  ctx.arc(0, 0, radius * 1.28, 0, Math.PI * 2);
  ctx.fill();

  for (let ring = 0; ring < 4; ring++) {
    const points = [];
    const scale = 0.42 + ring * 0.16;
    for (let i = 0; i <= 120; i++) {
      const a = (i / 120) * Math.PI * 2;
      const point = {
        x: Math.cos(a) * scale,
        y: Math.sin(a) * scale * (0.62 + Math.sin(a * 3 + time * 0.001) * 0.05),
        z: Math.sin(a + ring * 0.8) * scale * 0.44,
      };
      points.push(project(point, time + ring * 160, radius));
    }
    ctx.strokeStyle = rgba(0.24 - ring * 0.035);
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    for (const [index, point] of points.entries()) {
      if (index === 0) ctx.moveTo(point.x, point.y);
      else ctx.lineTo(point.x, point.y);
    }
    ctx.stroke();
  }

  for (let i = 0; i < 88; i++) {
    const a = i * 2.399963;
    const z = 1 - (2 * i + 1) / 88;
    const r = Math.sqrt(1 - z * z);
    const point = project({ x: Math.cos(a) * r, y: Math.sin(a) * r, z }, time, radius);
    ctx.fillStyle = rgba(Math.max(0.16, Math.min(0.9, (point.z + 1.1) / 2.2)));
    ctx.beginPath();
    ctx.arc(point.x, point.y, 2.2 * point.depth, 0, Math.PI * 2);
    ctx.fill();
  }

  for (let i = 0; i < 36; i++) {
    const a = i * 0.74 + time * 0.0006;
    const d = radius * (0.3 + (i % 7) * 0.08);
    const x = Math.cos(a) * d;
    const y = Math.sin(a * 1.18) * d * 0.72;
    ctx.strokeStyle = rgba(0.14 + (i % 5) * 0.04);
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(x, y);
    ctx.stroke();
  }

  const core = project({
    x: Math.sin(time * 0.0011) * 0.14 + 0.06,
    y: Math.cos(time * 0.00135) * 0.1,
    z: Math.sin(time * 0.0016) * 0.18,
  }, time, radius);
  const coreGlow = ctx.createRadialGradient(core.x, core.y, 0, core.x, core.y, radius * 0.28);
  coreGlow.addColorStop(0, "rgba(255, 252, 215, 0.96)");
  coreGlow.addColorStop(0.28, "rgba(255, 195, 91, 0.68)");
  coreGlow.addColorStop(1, "rgba(255, 93, 31, 0)");
  ctx.fillStyle = coreGlow;
  ctx.beginPath();
  ctx.arc(core.x, core.y, radius * 0.28, 0, Math.PI * 2);
  ctx.fill();

  ctx.restore();
  requestAnimationFrame(draw);
}

window.addEventListener("pointermove", (event) => {
  pointer.tx = (event.clientX / window.innerWidth - 0.5) * 2;
  pointer.ty = (event.clientY / window.innerHeight - 0.5) * 2;
});

requestAnimationFrame(draw);
