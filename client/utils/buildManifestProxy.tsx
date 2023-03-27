/*
 * This proxies the build manifest to always contain the current route, which
 * is needed for same-route navigation.
 *
 * The Next.js build manifest is populated in
 * https://github.com/vercel/next.js/blob/v12.1.0/packages/next/build/webpack/plugins/build-manifest-plugin.ts.
 *
 * The build manifest gets used for converting paths to routes (eg for dynamic
 * routes) and for determining paths of assets to fetch.
 */

import Router from 'next/router';

let hasRun = false;
export const initBuildManifestProxy = () => {
  // we only need to run this once
  if (hasRun) return;
  hasRun = true;

  const applyProxy = () => {
    const manifestHandler = {
      // ensure the current route is a key
      has(target, key) {
        if (Router.route && key === Router.route) {
          return true;
        }
        return Reflect.has(target, key);
      },
      ownKeys(target) {
        const keys = Reflect.ownKeys(target);
        if (Router.route && !keys.includes(Router.route)) {
          return [...keys, Router.route];
        }
        return keys;
      },
      getOwnPropertyDescriptor(target, prop) {
        const val = Reflect.getOwnPropertyDescriptor(target, prop);
        if (Router.route) {
          if (val === undefined && prop === Router.route) {
            return {
              configurable: true,
              enumerable: true,
            };
          }
        }
        return val;
      },

      // include route in manifest when queried
      get(target, key) {
        const val = Reflect.get(target, key);
        if (Router.route) {
          // returns empty list of dependencies for the current route since it
          // must have been already loaded (and it's not easy to find the
          // correct dependencies to inject)
          if (key === Router.route && val === undefined) {
            return [];
          }
          // add the current route to the list of pages
          if (key === 'sortedPages' && !val.includes(Router.route)) {
            return [...val, Router.route];
          }
        }
        return val;
      },
    };

    const manifest = self.__BUILD_MANIFEST!;
    self.__BUILD_MANIFEST = new Proxy(manifest, manifestHandler);
  };

  // run immediately if build manifest is loaded or add to the next.js callback
  // chain for when it loads
  if (self.__BUILD_MANIFEST) {
    applyProxy();
  } else {
    const cb = self.__BUILD_MANIFEST_CB;
    self.__BUILD_MANIFEST_CB = () => {
      cb && cb();
      applyProxy();
    };
  }
};
