/*
 * File containing generic hooks.
 */
import {useRef} from 'react';

export interface cacheOptions<B extends boolean> {
  enabled: B | boolean;
}

/* This is like useMemo but guarantees only called once semantics.
 * Additionally, this will only call the creator if enabled is true.
 */
export const useCache = <T,B extends boolean>(
  creator : () => T,
  deps: any[],
  options: cacheOptions<B> = {enabled: true},
) : T | (B extends true ? never : null) => {
  const ref = useRef({
    init: false,
    // this gets replaced by creator() on the first run while enabled
    // ignore typing for null case (only when enabled is false)
    data: null as any as T,
    deps: [] as any[],
  });
  const changed = deps.length !== ref.current.deps.length || deps.some((dep, i) => dep !== ref.current.deps[i])
  if (options.enabled && (!ref.current.init || changed)) {
    ref.current.init = true;
    ref.current.data = creator();
    ref.current.deps = deps;
  }
  return ref.current.data;
};
