import { NextRouter, useRouter as useNextRouter } from 'next/router';
import { useMemo } from 'react';
import { getBasePath } from 'utils/fetch';

// Prepend the rest of the prefix that is not part of process.env.basePath. In
// posthunt, this is /mypuzzlehunt.com for the hunt site(s) but the empty
// string for the registration site.
export const prependSecondaryBasePath = (router, path) => {
  let secondaryBasePath = router.basePath;
  if (secondaryBasePath.startsWith(process.env.basePath!)) {
    secondaryBasePath = secondaryBasePath.slice(process.env.basePath!.length);
  }
  // ensure no trailing slash for the root of the secondaryBasePath
  if (secondaryBasePath && path === '/') return secondaryBasePath;
  return secondaryBasePath + path;
}

export const sanitizePath = (router, path) => {
  let sanitized;
  if (path.startsWith(router.nextRouter.basePath)) {
    // path is the complete path
    sanitized = path.slice(router.nextRouter.basePath.length);
  } else {
    // path is relative to the site domain
    sanitized = prependSecondaryBasePath(router, path);
  }
  return sanitized;
};

// handler for router proxy
const routerHandler = {
  get(target, key) {
    const val = Reflect.get(target, key);
    if (key === "push") {
      return new Proxy(val, {
        // handler for push
        apply(push, thisArg, [url, as, ...rest]) {
          const proxyUrl = sanitizePath(thisArg, url);
          const proxyAs = as === undefined ? undefined : sanitizePath(thisArg, as);
          return Reflect.apply(push, thisArg, [proxyUrl, proxyAs, ...rest]);
        },
      });
    } else if (key === "basePath") {
      return getBasePath(target);
    } else if (key === "pathname" || key === "asPath") {
      const origPath = target.basePath + val;
      const newBasePath = getBasePath(target);
      if (origPath.startsWith(newBasePath)) {
        return origPath.slice(newBasePath.length);
      }
    } else if (key === "nextRouter") {
      // provide access to unproxied object
      return target;
    }
    return val;
  },
};

export interface Router extends NextRouter {
  nextRouter: NextRouter;
}

// Hook that proxies the router to include secondary base path as part of the base path
export const useRouter = () => {
  const router = useNextRouter();
  const proxyRouter = useMemo(() => new Proxy(router, routerHandler), [router]);
  return proxyRouter;
};
