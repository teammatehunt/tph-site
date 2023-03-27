/**
 * Some sample animations used for the Puzzle Factory in MH 2023.
 */

// Animation Helpers

// int 1 - 10 representing 10 levels of speed (not linear)
// should start at 7, shutdown is special (not just 0), and then 1 - 10 speeds up over time

const cycle = (time: number, duration: number) => {
  return (time % duration) / duration;
};

const pauseCycle = (time: number, duration: number, interval: number) => {
  var mod = time % interval;

  return mod < duration ? mod / duration : 1;
};

const lerp = (prop: number, a: number, b: number) => {
  return a + prop * (b - a);
};

const speedup = (prop: number, a: number, b: number) => {
  return a + prop * prop * (b - a);
};

const slowdown = (prop: number, a: number, b: number) => {
  var newProp = 1 - (1 - prop) * (1 - prop);
  return a + prop * (b - a);
};

const slightSpeedup = (prop: number, a: number, b: number) => {
  var cutoff = 0.3;
  var tempProp = lerp(prop, cutoff, 1);
  var newProp = (tempProp * tempProp - cutoff * cutoff) / (1 - cutoff * cutoff);
  return lerp(newProp, a, b);
};

const sinWave = (prop: number, a: number, b: number) => {
  var mid = (a + b) / 2.0;
  var amp = (b - a) / 2.0;
  return mid + Math.sin(prop * 2 * Math.PI) * amp;
};

const clamp01 = (num) => {
  if (num < 0) return 0;
  if (0 <= num && num <= 1) return num;
  return 1;
};

const ellipsePoint = (elX, elY, r1, r2, theta) => {
  var adjTheta = ((theta + 720) % 360) * (Math.PI / 180);
  var tan = Math.tan(adjTheta);
  var xTemp = (r1 * r2) / Math.sqrt(r2 * r2 + r1 * r1 * tan * tan);
  if (adjTheta > Math.PI / 2 && adjTheta < (3 * Math.PI) / 2) {
    xTemp = xTemp * -1;
  }
  var yTemp = Math.sqrt(1 - (xTemp / r1) * (xTemp / r1)) * r2;
  if (adjTheta < Math.PI) {
    yTemp = yTemp * -1;
  }
  return {
    x: xTemp + elX,
    y: yTemp + elY,
  };
};

const xSlide =
  (startPos, endPos, offsetPos, duration) =>
  (time: number, { x }) => {
    var diff = endPos - startPos;
    var lerpOffset = lerp(cycle(time, duration), 0, diff);
    var minPos = Math.min(startPos, endPos);
    return {
      x: ((lerpOffset + offsetPos + Math.abs(diff)) % Math.abs(diff)) + minPos,
    };
  };

const ySlide =
  (startPos, endPos, offsetPos, duration) =>
  (time: number, { y }) => {
    var diff = endPos - startPos;
    var lerpOffset = lerp(cycle(time, duration), 0, diff);
    var minPos = Math.min(startPos, endPos);
    return {
      y: ((lerpOffset + offsetPos + Math.abs(diff)) % Math.abs(diff)) + minPos,
    };
  };

// Hard-coded animations

const flicker = (time, { alpha }) => {
  var len = 24;
  var alphas = [
    0, 0.4, 0.4, 0.9, 0.6, 0.6, 0.8, 1, 0.5, 0.5, 0.5, 0.2, 0.9, 1, 0.9, 0.4,
    0.4, 0.1, 0.5, 0.6, 0, 0.5, 0.4,
  ];

  var cycleTime = 200;
  var progress = cycle(time, cycleTime) * len;

  var thisIndex = Math.floor(progress);
  var nextIndex = (thisIndex + 1) % len;
  var prop = progress - thisIndex;

  return {
    alpha: lerp(prop, alphas[thisIndex], alphas[nextIndex]),
  };
};

const wave =
  (amplitude, period) =>
  (time, { rotation }) => {
    return {
      rotation: sinWave(cycle(time, period), -1 * amplitude, amplitude),
    };
  };

const ANIMATIONS = {
  rotate: (time, { rotation }) => {
    var newTime = time;
    var rotateTime = lerp(7 / 10, 400, 100);
    return {
      rotation: 2 * Math.PI * cycle(newTime, 200),
    };
  },
  spinFast: (time, { rotation }) => {
    var newTime = time;
    var spinTime = lerp(7 / 10, 30, 10);
    return {
      rotation: 2 * Math.PI * cycle(newTime, spinTime),
    };
  },
  wave: wave(0.55, 80),
  flicker: flicker,
};

export default ANIMATIONS;
