import path from 'path';

/*
 * Load static paths from a json. Use with:
 *
 * export const getStaticPathsInStaticExport = generateGetStaticPaths(import.meta.url);
 */
export const generateGetStaticPaths = (importMetaUrl : string, isFactory?: boolean) => {
  if (!process.env.isStatic) {
    return async () => {
      throw new Error('generateGetStaticPaths was called when the site is not static');
    };
  } else {
    // import here for tree shaking
    const fs = require('fs');
    const prefix = 'file:///app/posthunt-client/pages/';
    if (!importMetaUrl.startsWith(prefix)) throw new Error(`${importMetaUrl} does not start with ${prefix}`);
    return async () => {
      const route = importMetaUrl.slice(prefix.length);
      const base = path.basename(route, '.tsx');
      const isCatchAll = base.includes('[...')
      const isOptionalCatchAll = base.startsWith('[[...')
      const commonRouteParts = path.dirname(route).split('/');

      // construct the directory path containing the jsons for this route
      // NB: the api url includes the basePath but import.meta.url does not
      const pathParts = 'assets/json_responses/2023'.split('/');
      // push the domain
      pathParts.push(commonRouteParts[0]);
      pathParts.push('api');
      if (isFactory) {
        // factory round urls have an extra factory in the api url
        pathParts.push('factory');
      }
      // push the rest of the route
      pathParts.push(...commonRouteParts.slice(1));

      const parent = pathParts.join('/');
      if (!fs.existsSync(parent)) {
        console.warn(`No static pages generated for ${parent} because there were no json files`);
        return {
          paths: [],
          fallback: false,
        };
      }
      const files = await fs.promises.readdir(parent);

      // assumes the param is `slug`
      const paths = files.filter(
        // ignore jsons with query parameters (these slugs occur once with the
        // query parameter forthe solution and once without)
        fname => !fname.includes('?')
      ).map(fname => {
        const fbase = path.basename(fname, '.json');
        return {
          params: {
            slug: isCatchAll ? [fbase] : fbase,
          },
        };
      });
      if (isOptionalCatchAll) {
        paths.push({
          params: {
            slug: [],
          },
        });
      }
      return {
        paths,
        fallback: false,
      };
    };
  }
};
