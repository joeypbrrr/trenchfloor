(() => {
  const host = document.getElementById("scene");
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  function fail(err) {
    host.innerHTML = "<p class='scene-fallback'>3D view could not start on this device. Live research continues below.</p>";
    console.error(err);
  }
  try {
    if (!window.THREE) throw new Error("Three.js unavailable");
    const T = THREE;
    const scene = new T.Scene();
    scene.background = new T.Color("#070504");
    scene.fog = new T.Fog("#070504", 16, 34);
    const renderer = new T.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
    renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.75));
    renderer.outputColorSpace = T.SRGBColorSpace;
    renderer.toneMapping = T.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.05;
    host.appendChild(renderer.domElement);

    // Fixed camera. Nothing in this file rotates, pans, or zooms it.
    const camera = new T.PerspectiveCamera(30, 1, 0.1, 80);
    function frameCamera() {
      camera.position.set(0, 3.35, 12.4);
      camera.lookAt(0, 1.7, 0.1);
    }
    frameCamera();

    scene.add(new T.HemisphereLight("#ffb27a", "#140c08", 0.28));
    scene.add(new T.AmbientLight("#ff7a00", 0.08));
    function glow(x, y, z, intensity, distance, color) {
      const light = new T.PointLight(color || "#ff7a00", intensity, distance, 2);
      light.position.set(x, y, z);
      scene.add(light);
      return light;
    }

    const wall = new T.MeshStandardMaterial({ color: "#100c0a", roughness: 0.92, metalness: 0.04 });
    const floorMat = new T.MeshStandardMaterial({ color: "#0c0908", roughness: 0.84, metalness: 0.08 });
    const deskMat = new T.MeshStandardMaterial({ color: "#1a1410", roughness: 0.55, metalness: 0.35 });
    const trim = new T.MeshStandardMaterial({ color: "#3a2418", roughness: 0.4, metalness: 0.6 });
    const black = new T.MeshStandardMaterial({ color: "#070605", roughness: 0.5, metalness: 0.2 });
    function neonMat(color, intensity) {
      return new T.MeshStandardMaterial({
        color: color,
        emissive: color,
        emissiveIntensity: intensity,
        roughness: 0.28,
        metalness: 0.05,
        toneMapped: false,
      });
    }
    const orange = neonMat("#ff7a00", 2.4);
    const amber = neonMat("#ffb15a", 1.8);
    function cloth(hex) {
      return new T.MeshStandardMaterial({ color: hex, roughness: 0.72, metalness: 0.08 });
    }
    function skin(hex) {
      return new T.MeshStandardMaterial({ color: hex, roughness: 0.62, metalness: 0.02 });
    }

    function box(w, h, d, material, x, y, z, parent) {
      const mesh = new T.Mesh(new T.BoxGeometry(w, h, d), material);
      mesh.position.set(x, y, z);
      (parent || scene).add(mesh);
      return mesh;
    }

    box(30, 0.2, 18, floorMat, 0, -0.1, 0);
    box(30, 6.2, 0.2, wall, 0, 3, -7.2);
    box(0.2, 6.2, 18, wall, -15, 3, 0);
    box(0.2, 6.2, 18, wall, 15, 3, 0);
    box(30, 0.2, 18, wall, 0, 6.2, 0);
    const grid = new T.GridHelper(30, 30, 0x4a2a12, 0x1c120c);
    grid.position.y = 0.01;
    scene.add(grid);

    const tubes = [];
    [[-2.2, 5.7], [2.6, 5.7]].forEach(([z, y]) => {
      const tube = box(16, 0.08, 0.08, orange, 0, y, z);
      tubes.push(tube);
      glow(0, y - 0.3, z, 8, 14);
    });
    [-12.5, 12.5].forEach((x) => {
      tubes.push(box(0.07, 3.4, 0.07, amber, x, 3.1, -6.9));
    });
    tubes.push(box(17, 0.05, 0.08, orange, 0, 0.04, 2.8));
    glow(0, 2.2, 1.5, 6, 16, "#ff8a1e");
    glow(-8, 2.4, -1, 4, 10);
    glow(8, 2.4, -1, 4, 10);

    const signCanvas = document.createElement("canvas");
    signCanvas.width = 1024;
    signCanvas.height = 220;
    const sg = signCanvas.getContext("2d");
    sg.clearRect(0, 0, 1024, 220);
    sg.textAlign = "center";
    sg.textBaseline = "middle";
    sg.font = "700 120px 'IBM Plex Mono', monospace";
    sg.shadowColor = "#ff7a00";
    sg.shadowBlur = 28;
    sg.fillStyle = "#ff9a3c";
    sg.fillText("TRENCHFLOOR", 512, 110);
    const signTex = new T.CanvasTexture(signCanvas);
    signTex.colorSpace = T.SRGBColorSpace;
    const sign = new T.Mesh(
      new T.PlaneGeometry(8.2, 1.7),
      new T.MeshBasicMaterial({ map: signTex, transparent: true, toneMapped: false })
    );
    sign.position.set(0, 4.35, -7.02);
    scene.add(sign);
    const signLight = glow(0, 4.2, -5.6, 7, 12);

    box(18.2, 0.14, 2.5, deskMat, 0, 1.02, 0.15);
    box(18.2, 0.9, 0.12, trim, 0, 0.5, 1.35);
    [-9, 9].forEach((x) => box(0.16, 1.02, 2.4, trim, x, 0.51, 0.15));

    const roles = [
      { role: "Risk Manager", initials: "RM", color: "#ff7a00", task: "Waiting for the chain" },
      { role: "Bubble Map Analyst", initials: "BA", color: "#ffb000", task: "Waiting for holders" },
      { role: "X/Twitter Scout", initials: "XS", color: "#ff5a1f", task: "No free X API yet" },
      { role: "Data Scout", initials: "DS", color: "#ff9a3c", task: "Waiting for pairs" },
      { role: "Backtester", initials: "BT", color: "#ffc266", task: "Ledger is paper only" },
      { role: "Strategist", initials: "ST", color: "#ff6a00", task: "Buy dips. Never top-tick." },
    ];
    const skins = ["#e0b394", "#c48a62", "#8d5a3c", "#f0c8a8", "#a87456", "#d7a888"];
    const stations = [];

    function wrap(ctx, text, x, y, max, line) {
      const words = String(text || "").split(/\s+/);
      let row = "";
      let drawn = 0;
      words.forEach((word) => {
        const next = row ? row + " " + word : word;
        if (ctx.measureText(next).width > max && row) {
          ctx.fillText(row, x, y + drawn * line);
          drawn += 1;
          row = word;
        } else row = next;
      });
      if (row && drawn < 3) ctx.fillText(row, x, y + drawn * line);
    }

    function paintScreen(station, agent) {
      const ctx = station.ctx;
      const color = "#" + (agent.color || "ff7a00");
      ctx.fillStyle = "#100804";
      ctx.fillRect(0, 0, 512, 320);
      ctx.fillStyle = color;
      ctx.fillRect(0, 0, 512, 8);
      ctx.globalAlpha = 0.16;
      for (let y = 28; y < 320; y += 8) ctx.fillRect(0, y, 512, 2);
      ctx.globalAlpha = 1;
      ctx.fillStyle = color;
      ctx.font = "700 42px monospace";
      ctx.textAlign = "left";
      ctx.fillText(agent.initials || "TF", 24, 68);
      ctx.font = "600 28px monospace";
      ctx.fillStyle = "#ffe1c4";
      ctx.fillText((agent.role || "").toUpperCase(), 110, 64);
      ctx.font = "700 22px monospace";
      ctx.fillStyle = agent.status === "error" ? "#ff6b4a" : color;
      ctx.fillText((agent.status || "IDLE").toUpperCase(), 24, 112);
      ctx.fillStyle = "#f4d2b4";
      ctx.font = "500 22px monospace";
      wrap(ctx, agent.latest_action || agent.task || "", 24, 156, 460, 30);
      station.tex.needsUpdate = true;
    }

    function makeTag(text, color) {
      const canvas = document.createElement("canvas");
      canvas.width = 512;
      canvas.height = 96;
      const ctx = canvas.getContext("2d");
      ctx.fillStyle = "#120c09ee";
      ctx.fillRect(8, 12, 496, 72);
      ctx.strokeStyle = color;
      ctx.lineWidth = 4;
      ctx.strokeRect(8, 12, 496, 72);
      ctx.fillStyle = color;
      ctx.font = "700 36px monospace";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(text, 256, 48);
      const tex = new T.CanvasTexture(canvas);
      tex.colorSpace = T.SRGBColorSpace;
      const sprite = new T.Sprite(new T.SpriteMaterial({ map: tex, transparent: true }));
      sprite.scale.set(2.15, 0.4, 1);
      return sprite;
    }

    roles.forEach((role, i) => {
      const x = -7.5 + i * 3;
      const group = new T.Group();
      scene.add(group);
      const shirt = cloth(role.color);
      const face = skin(skins[i]);
      // Chair and seated body, facing the monitor (toward +Z / the camera side).
      box(0.72, 0.1, 0.72, black, x, 0.58, -1.15);
      box(0.12, 0.58, 0.12, trim, x, 0.29, -1.15);
      box(0.7, 0.72, 0.12, black, x, 1.05, -1.48);
      const body = new T.Group();
      body.position.set(x, 0, -1.05);
      scene.add(body);
      box(0.62, 0.72, 0.38, shirt, 0, 1.22, 0, body);
      const head = new T.Mesh(new T.SphereGeometry(0.24, 16, 12), face);
      head.position.set(0, 2.08, 0.04);
      body.add(head);
      box(0.52, 0.1, 0.3, shirt, 0, 2.28, 0, body);
      box(0.09, 0.18, 0.24, orange, -0.22, 2.08, 0.02, body);
      box(0.09, 0.18, 0.24, orange, 0.22, 2.08, 0.02, body);
      const arms = [];
      [-1, 1].forEach((side) => {
        const arm = new T.Group();
        arm.position.set(side * 0.4, 1.48, 0.05);
        body.add(arm);
        box(0.14, 0.48, 0.14, shirt, 0, -0.2, 0.12, arm);
        box(0.12, 0.12, 0.12, face, 0, -0.46, 0.2, arm);
        arms.push(arm);
        arm.rotation.x = -1.05;
      });
      const tag = makeTag(role.role.toUpperCase(), role.color);
      tag.position.set(x, 2.72, -1.05);
      scene.add(tag);

      const screenCanvas = document.createElement("canvas");
      screenCanvas.width = 512;
      screenCanvas.height = 320;
      const tex = new T.CanvasTexture(screenCanvas);
      tex.colorSpace = T.SRGBColorSpace;
      const bezel = new T.Group();
      bezel.position.set(x, 1.48, 0.55);
      bezel.rotation.y = -0.42;
      scene.add(bezel);
      box(1.72, 1.12, 0.08, black, 0, 0, 0, bezel);
      const panel = new T.Mesh(new T.PlaneGeometry(1.56, 0.96), new T.MeshBasicMaterial({ map: tex, toneMapped: false }));
      panel.position.set(0, 0, 0.045);
      bezel.add(panel);
      box(0.1, 0.34, 0.08, trim, 0, -0.7, 0, bezel);
      box(0.46, 0.05, 0.28, trim, 0, -0.86, 0, bezel);
      box(1.5, 0.035, 0.04, neonMat(role.color, 2.1), 0, -0.58, 0.06, bezel);
      box(0.7, 0.04, 0.24, black, 0, -0.2, 0.55, bezel);
      const station = { ctx: screenCanvas.getContext("2d"), tex, arms, tag, role };
      paintScreen(station, { ...role, color: role.color.slice(1), status: "idle", latest_action: role.task });
      stations.push(station);
    });

    function resize() {
      const w = host.clientWidth || 800;
      const h = host.clientHeight || 540;
      renderer.setSize(w, h, false);
      camera.aspect = w / Math.max(h, 1);
      camera.updateProjectionMatrix();
      frameCamera();
    }
    new ResizeObserver(resize).observe(host);
    resize();

    function animate(now) {
      requestAnimationFrame(animate);
      const t = now / 1000;
      if (!reduce) {
        const flicker = 2.2 + Math.sin(t * 5.5) * 0.06 + (Math.random() < 0.012 ? -0.55 : 0);
        orange.emissiveIntensity = flicker;
        sign.material.opacity = 0.92 + Math.sin(t * 7) * 0.04;
        signLight.intensity = 6.2 + Math.sin(t * 5.5) * 0.35;
        stations.forEach((station, i) => {
          station.arms.forEach((arm, side) => {
            arm.rotation.x = -1.05 + Math.sin(t * 7 + i + side) * 0.06;
          });
        });
      }
      renderer.render(scene, camera);
    }
    requestAnimationFrame(animate);
    document.querySelector(".scene-loading")?.remove();

    window.setAgentData = (agents) => {
      (agents || []).forEach((agent, i) => {
        if (!stations[i]) return;
        paintScreen(stations[i], agent);
        const next = makeTag((agent.role || stations[i].role.role).toUpperCase(), "#" + (agent.color || "ff7a00"));
        next.position.copy(stations[i].tag.position);
        next.scale.copy(stations[i].tag.scale);
        scene.remove(stations[i].tag);
        scene.add(next);
        stations[i].tag = next;
      });
    };
  } catch (err) {
    fail(err);
  }
})();
