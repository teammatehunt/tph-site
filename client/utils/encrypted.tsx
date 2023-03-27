import React, { useRef, useState } from 'react';
import cryptoHex from 'crypto-js/enc-hex';
import dynamic from 'next/dynamic';
import sha256 from 'crypto-js/sha256';

import { useCache, cacheOptions } from 'utils/hooks';
import getErrorComponent from 'components/error';

// Wraps Next.js dynamic imports with encryption.
//
// const Component = useDynamicEncrypted<Props>('path/to/module');
// const Component = useDynamicEncrypted<Props>(`path/to/module/${slug}`);
//
// NB: The path should be everything after encrypted/.

interface Options extends cacheOptions<boolean> {
  onError?: (error: Error) => any;
}

export const useDynamic = <T,>(
  importer: () => Promise<React.ComponentType<T>>,
  deps: any[],
  options: Options = { enabled: true }
): React.ComponentType<T> => {
  const { onError, enabled = true } = options;
  const Component = useCache(
    () =>
      dynamic<T>(importer().catch(onError ?? getErrorComponent), {
        loading: () => <>Loading...</>,
      }),
    deps,
    { enabled }
  ) as React.ComponentType<T>; // ignore typing for null case
  return Component;
};

const hashedPath = (path: string): string => {
  if (
    !process.env.useEncryptionPlugin ||
    process.env.NODE_ENV === 'development'
  ) {
    return path;
  } else {
    // hash basename
    return sha256(path.split('/').pop())
      .toString(cryptoHex)
      .substr(0, process.env.FILENAME_HASH_LENGTH);
  }
};

const dynamicEncrypted = <T,>(mod: string, onError): any => {
  const hashedMod = hashedPath(mod);
  // evaluate hashedBucket now but put hashedSlug in the closure
  const importer = () =>
    import(`encrypted/${hashedMod}`).catch(onError ?? getErrorComponent);
  return dynamic<T>(importer, {
    loading: () => <>Loading...</>,
  });
};

const useDynamicEncrypted = <T,>(
  mod: string,
  options: Options = { enabled: true }
): React.ComponentType<T> => {
  const { onError, enabled = true } = options;
  const Component = useCache(() => dynamicEncrypted(mod, onError), [mod], {
    enabled,
  }) as React.ComponentType<T>; // ignore typing for null case
  return Component;
};
export default useDynamicEncrypted;
