import { useEffect, useRef } from 'react';

/**
 * Sets up a callback to run every animation frame.
 * Must provide a tick ref which will be passed into the callback.
 */
export const useAnimationFrame = (
  callback: (tick: number) => void,
  tickRef: React.MutableRefObject<number>,
  deps: React.DependencyList
) => {
  // Use useRef for mutable variables that we want to persist
  // without triggering a re-render on their change
  const requestRef = useRef<number | undefined>();
  const previousTimeRef = useRef<number | undefined>();

  const animate = (time) => {
    if (previousTimeRef.current !== undefined) {
      const deltaTime = time - previousTimeRef.current;
      tickRef.current += deltaTime / 100;
      callback(tickRef.current);
    }
    previousTimeRef.current = time;
    requestRef.current = requestAnimationFrame(animate);
  };

  useEffect(() => {
    requestRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(requestRef.current!);
  }, [deps]);
};
