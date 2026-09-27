/**
 * Decorative Monsoon Particle Flow Engine for Synoptiq.
 * Renders client-side decorative streamlines over the Arabian Sea,
 * Indian subcontinent, and Bay of Bengal on an HTML5 Canvas.
 * NOTE: This is a purely decorative visual display effect; it is NOT decoded
 * GEFS 850 hPa wind fields, forecast data, or meteorological observations.
 * 100% offline, client-side, zero external libraries.
 */

export function createParticleLayer(map) {
  let isRunning = true;
  let animationId = null;
  const numParticles = 450;
  const particles = [];

  // Canvas element
  const canvas = document.createElement("canvas");
  canvas.className = "leaflet-particle-canvas";
  canvas.style.position = "absolute";
  canvas.style.top = "0";
  canvas.style.left = "0";
  canvas.style.pointerEvents = "none";
  canvas.style.zIndex = "450"; // Above basemap, below interactive polygons

  const pane = map.getPanes().overlayPane;
  pane.appendChild(canvas);
  const ctx = canvas.getContext("2d");

  function resize() {
    const size = map.getSize();
    const pixelRatio = window.devicePixelRatio || 1;
    canvas.width = size.x * pixelRatio;
    canvas.height = size.y * pixelRatio;
    canvas.style.width = `${size.x}px`;
    canvas.style.height = `${size.y}px`;
    ctx.scale(pixelRatio, pixelRatio);
    reposition();
  }

  function reposition() {
    const topLeft = map.containerPointToLayerPoint([0, 0]);
    L.DomUtil.setPosition(canvas, topLeft);
  }

  /**
   * Synoptic Monsoon Vector Field (JJAS 850 hPa Climatology):
   * - Arabian Sea: Strong SW flow (u > 0, v > 0)
   * - Peninsular India: Westerly flow across Western Ghats (u > 0, v ~ 0)
   * - Bay of Bengal: SW turning Southerly / S-SE (u > 0, v > 0)
   * - Indo-Gangetic Plains: Easterly / SE monsoon trough flow (u < 0, v >= 0)
   */
  function getVelocity(lat, lon) {
    let u = 0;
    let v = 0;

    if (lat < 8.0 || lat > 37.0 || lon < 65.0 || lon > 98.0) {
      return { u: 0, v: 0, speed: 0 };
    }

    if (lat >= 8.0 && lat < 22.0 && lon < 74.0) {
      // Arabian Sea Low-Level Jet (Somali Jet branch)
      u = 1.6 + 0.4 * Math.sin(lat * 0.3);
      v = 1.0 + 0.3 * Math.cos(lon * 0.2);
    } else if (lat >= 10.0 && lat < 22.0 && lon >= 74.0 && lon < 83.0) {
      // Peninsular cross-equatorial westerlies
      u = 1.8;
      v = 0.2 * Math.sin(lon * 0.4);
    } else if (lat >= 10.0 && lat < 24.0 && lon >= 83.0 && lon < 95.0) {
      // Bay of Bengal cyclonic curvature
      u = 0.8 + 0.4 * Math.sin(lat * 0.2);
      v = 1.4 - 0.4 * Math.cos(lon * 0.1);
    } else if (lat >= 22.0 && lat < 30.0 && lon >= 74.0 && lon < 88.0) {
      // Monsoon Trough (deflected easterlies along the Himalayas)
      u = -1.2;
      v = 0.3;
    } else if (lat >= 24.0 && lon >= 88.0) {
      // Northeast / Assam funneling
      u = -0.4;
      v = 1.1;
    } else {
      // Background general flow
      u = 0.7;
      v = 0.5;
    }

    const speed = Math.sqrt(u * u + v * v);
    return { u, v, speed };
  }

  function resetParticle(p) {
    // Spawn across the India & Indian Ocean bounding box
    p.lat = 7.0 + Math.random() * 29.0;
    p.lon = 66.0 + Math.random() * 32.0;
    p.age = 0;
    p.maxAge = 40 + Math.floor(Math.random() * 70);
    p.history = [];
  }

  // Initialize particles
  for (let i = 0; i < numParticles; i++) {
    const p = {};
    resetParticle(p);
    p.age = Math.floor(Math.random() * p.maxAge); // Stagger initial ages
    particles.push(p);
  }

  function drawFrame() {
    if (!isRunning) return;

    const size = map.getSize();

    // Clear canvas every frame to keep canvas transparent and never occlude map layers
    ctx.clearRect(0, 0, size.x, size.y);

    const step = 0.08; // Coordinate delta step

    for (let i = 0; i < particles.length; i++) {
      const p = particles[i];
      p.age++;

      if (p.age > p.maxAge) {
        resetParticle(p);
        continue;
      }

      const vel = getVelocity(p.lat, p.lon);
      if (vel.speed === 0) {
        resetParticle(p);
        continue;
      }

      // Advance particle in geographic space
      p.lat += vel.v * step;
      p.lon += vel.u * step;

      // Project to screen space
      const pt = map.latLngToContainerPoint([p.lat, p.lon]);

      if (pt.x < 0 || pt.x > size.x || pt.y < 0 || pt.y > size.y) {
        resetParticle(p);
        continue;
      }

      p.history.push({ x: pt.x, y: pt.y });
      if (p.history.length > 5) {
        p.history.shift();
      }

      if (p.history.length >= 2) {
        const lifeProgress = p.age / p.maxAge;
        const baseAlpha = Math.sin(lifeProgress * Math.PI) * 0.85;

        for (let j = 1; j < p.history.length; j++) {
          const ptA = p.history[j - 1];
          const ptB = p.history[j];
          const segDist = Math.hypot(ptB.x - ptA.x, ptB.y - ptA.y);

          // Ignore large jumps from screen wrap-around or resets
          if (segDist < 35) {
            const segAlpha = (j / p.history.length) * baseAlpha;
            ctx.beginPath();
            ctx.moveTo(ptA.x, ptA.y);
            ctx.lineTo(ptB.x, ptB.y);
            ctx.strokeStyle = vel.speed > 1.8 ? `rgba(240, 249, 255, ${segAlpha})` : `rgba(56, 189, 248, ${segAlpha})`;
            ctx.lineWidth = vel.speed > 1.8 ? 1.75 : 1.25;
            ctx.stroke();
          }
        }
      }
    }

    animationId = requestAnimationFrame(drawFrame);
  }

  // Event handlers
  map.on("resize", resize);
  map.on("viewreset", () => {
    reposition();
    particles.forEach(resetParticle);
  });
  map.on("move", reposition);
  map.on("zoomstart", () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    particles.forEach(resetParticle);
  });

  resize();
  animationId = requestAnimationFrame(drawFrame);

  return {
    toggle(enabled) {
      if (enabled === undefined) {
        isRunning = !isRunning;
      } else {
        isRunning = Boolean(enabled);
      }

      if (isRunning) {
        canvas.style.display = "block";
        resize();
        animationId = requestAnimationFrame(drawFrame);
      } else {
        canvas.style.display = "none";
        if (animationId) {
          cancelAnimationFrame(animationId);
          animationId = null;
        }
      }
      return isRunning;
    },
    destroy() {
      isRunning = false;
      if (animationId) cancelAnimationFrame(animationId);
      map.off("resize", resize);
      map.off("viewreset", reposition);
      map.off("move", reposition);
      if (canvas.parentNode) {
        canvas.parentNode.removeChild(canvas);
      }
    },
  };
}
