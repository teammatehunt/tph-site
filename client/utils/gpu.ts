import { useEffect, useState } from 'react';
import { getGPUTier } from 'detect-gpu';

export const WEBGL_SUPPORTED = (() => {
  if (typeof window === 'undefined') {
    return false; // ignore in server-side rendering
  }
  if (!window.WebGLRenderingContext) {
    return false;
  }
  let gl;
  const canvas = document.createElement('canvas');
  try {
    gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
  } catch (x) {
    gl = null;
  }
  if (!gl) {
    return false;
  }
  // Our textures require 8000px wide, so mobile browsers with limit 4096 are not supported.
  return gl.getParameter(gl.MAX_TEXTURE_SIZE) >= 8000;
})();

/**
 * Returns a rating for the client's GPU based on fps where
 * -1 = unknown, 0 = no hardware acceleration, 1 = 15fps, 2 = 30fps, 3 = 60fps
 */
const useGPUTier = () => {
  const [tier, setTier] = useState(-1);

  async function computeGPUTier() {
    const gpuTier = await getGPUTier();
    setTier(gpuTier.tier);
  }

  useEffect(() => void computeGPUTier(), []);
  return tier;
};

export default useGPUTier;
