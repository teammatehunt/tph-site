import React, { useEffect, useState } from 'react';

interface Dimensions {
  width: number;
  height: number;
}

/** Hook that returns the current screen size. */
const useScreenSize = () => {
  const computeScreenSize = (): Dimensions => {
    if (typeof window === 'undefined') {
      // Return an arbitrary value for server-side
      return { width: 640, height: 480 };
    }
    return {
      width: window.innerWidth,
      height: window.innerHeight,
    };
  };

  const [size, setSize] = useState<Dimensions>(computeScreenSize());
  const resize = () => setSize(computeScreenSize());

  useEffect(() => {
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, []);

  return size;
};

export default useScreenSize;
