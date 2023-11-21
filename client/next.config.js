const assert = require('assert');
const crypto = require('crypto');
const path = require('path');
const { sources, Compilation } = require('webpack');

const {
  CLIENT_STATIC_FILES_PATH,
} = require('next/dist/shared/lib/constants.js');

const IS_ARCHIVE = !!Number(process.env.ENABLE_POSTHUNT_SITE); // whether to use /20xx/... path scheme for posthunt
const USE_ENCRYPTION_PLUGIN = !IS_ARCHIVE;
const IS_STATIC = false; // whether to use jsons instead of a backend server
const USE_WORKER = IS_ARCHIVE; // whether to enable the web worker for fetch and websocket emulation
const FILENAME_HASH_LENGTH = 8; // for encrypted/
// FIXME: Update prefix
const STORAGE_PREFIX = '20xx-'; // for cookies and localStorage

const CLIENT = path.basename(process.cwd());

/**
 * List of public pages that are allowed to show up in the build manifest.
 * By default, we use regex to suppress pages from showing up in this generated
 * JSON file to avoid leaking spoilers - otherwise hidden puzzle pages will be
 * visible to the public upon inspecting the Network dev tools!
 * See https://stackoverflow.com/q/63510179 for more details.
 *
 * FIXME: add any public-facing pages so they will be statically optimized.
 */
const MANIFEST_ALLOWLIST = [
  '/',
  '/404',
  '/_error',
  '/about',
  '/events',
  '/events/free-answer',
  '/health_and_safety',
  '/login',
  '/logout',
  '/puzzles',
  '/register',
  '/register-team',
  '/register-individual',
  '/reset_password',
  '/sponsors',
  '/story',
  //'/wrapup',
  //'/q-and-a',
  '/hints/\\[slug\\]',
]
  .map((endpoint) => `("${endpoint}")`)
  .join('|');

// Match any string of the form ,"{url not in the allowlist}":["..."]
// These will be removed in the build manifest
const MANIFEST_REGEX = new RegExp(
  `,(?!${MANIFEST_ALLOWLIST})"/[^"]*":\\[([^"\\[\\]]+|"[^"]*")*\\]`,
  'g'
);

// Set sortedPages to the empty list
const SORTED_PAGES_REGEX = /(?<=\bsortedPages:\[).*?(?=\][,}])/;

/** Custom plugin that overwrites the build manifest to hide spoilers. */
class BuildManifestPlugin {
  constructor(options) {
    this.buildId = options.buildId;
    this.modern = options.modern;
  }

  apply(compiler) {
    compiler.hooks.emit.tapAsync(
      'TphBuildManifest',
      (compilation, callback) => {
        const clientManifestPath = `${CLIENT_STATIC_FILES_PATH}/${this.buildId}/_buildManifest.js`;
        if (clientManifestPath in compilation.assets) {
          compilation.updateAsset(
            clientManifestPath,
            (old) =>
              // Replace spoilers in the build manifest.
              new sources.RawSource(
                old
                  .source()
                  .replace(MANIFEST_REGEX, '')
                  .replace(SORTED_PAGES_REGEX, '')
              )
          );
        }
        callback();
      }
    );
  }
}

const hash = (s, format = undefined) => {
  return crypto.createHash('sha256').update(s).digest(format);
};

// must be known at build time -- keep in sync with python settings/base.py
// FIXME: Change this here and in python
const SECRET_KEY_POSTFIX = 'FIXME_replace_WITH_a_NEW_key_SYNCED_between_NEXTJS_and_PYTHON';
class EncryptionPlugin {
  constructor(options) {
    this.dev = options.dev;
  }

  // detect and rename dynamic chunks under /app/client/encrypted/ to enc/ and
  // generates encryption keys
  apply(compiler) {
    compiler.hooks.compilation.tap('TphEncryption', (compilation) => {
      compilation.hooks.optimizeChunks.tap(
        'TphEncryptionPreprocess',
        (chunks) => {
          // NB: this only checks client not reg-client for chunks that should be encrypted
          const CLIENT_ROOT = '/app/client';
          const ENC_COMPONENT_PREFIX = path.join(CLIENT_ROOT, 'encrypted');
          for (const chunk of chunks) {
            let basename = null;
            for (const group of chunk._groups) {
              for (const origin of group.origins) {
                const context = origin.request.startsWith('./')
                  ? origin.module?.context
                  : CLIENT_ROOT;
                if (!context) continue;
                const request = path.join(context, origin.request);
                if (
                  request?.startsWith(ENC_COMPONENT_PREFIX) &&
                  // only use canonical path and ignore extra generated request paths
                  !['', 'index', 'index.tsx'].includes(request.split('/').pop())
                ) {
                  basename = path.parse(request).name;
                }
              }
            }
            if (basename) {
              const name = this.dev
                ? hash(basename, 'hex').substr(0, FILENAME_HASH_LENGTH)
                : basename;
              chunk.name = `enc/${name}`;
            }
          }
        }
      );

      // encrypt files with the keys generated earlier
      compilation.hooks.processAssets.tap(
        {
          name: 'TphEncryption',
          stage: Compilation.PROCESS_ASSETS_STAGE_OPTIMIZE_SIZE,
        },
        () => {
          // encrypt everything under chunks/enc/
          // things get placed here if they were imported from encrypted/
          // to get files here, use dynamic(() => import('encrypted/bucket/[name]'))
          const encPathDir = `${CLIENT_STATIC_FILES_PATH}/chunks/enc/`;
          for (const asset of compilation.getAssets()) {
            if (asset.name.startsWith(encPathDir)) {
              // asset.name is name.js in dev and name.hash.js in prod
              const basename = path.parse(asset.name).name;
              const name = this.dev
                ? basename
                : basename.split('.').slice(0, -1).join('.');
              // use halves of a sha256 as the aes128 key and iv
              const hashVal = hash(name + SECRET_KEY_POSTFIX);
              const k = hashVal.slice(0, 16);
              const iv = hashVal.slice(16, 32);
              const cipher = crypto.createCipheriv('aes128', k, iv);
              // NB: hex is more bytes than base64 when raw but fewer when compressed after
              let ciphertext = cipher.update(
                asset.source.buffer(),
                'utf8',
                'hex'
              );
              ciphertext += cipher.final('hex');

              // The generated source will look for a key to decrypt the
              // payload before executing.
              // NB: cannot use the WebCrypto API because webpack expects the
              // chunk to be loaded synchronously. CryptoJS used on client
              // because of much smaller size (due to modular imports) than
              // crypto or node-forge.
              const newSource = `
                  (function(){
                    key=(self.cryptKeys||{})[${JSON.stringify(name)}];
                    if(key){
                      fromHex=self.CryptoJS.enc.Hex.parse;
                      k=fromHex(key.slice(0,32));
                      iv=fromHex(key.slice(32,64));
                      c=fromHex(${JSON.stringify(ciphertext)});
                      p=self.CryptoJS.AES.decrypt({ciphertext:c},k,{iv}).toString(self.CryptoJS.enc.Utf8);
                      eval(p);
                    }
                  })();
                `
                .trim()
                .split('\n')
                .map((s) => s.trim())
                .join('\n');
              compilation.updateAsset(
                asset.name,
                new sources.RawSource(newSource)
              );
            }
          }
        }
      );
    });
  }
}

// FIXME: update base paths
const basePath =
  CLIENT === 'posthunt-client'
    ? '/20xx'
    : IS_ARCHIVE && CLIENT === 'reg-client'
    ? '/20xx/registration.mypuzzlehunt.com'
    : '';

module.exports = {
  // makes JS minification faster: https://nextjs.org/docs/upgrading
  swcMinify: true,
  images: {
    // using built-in image support messes with pathing
    disableStaticImages: true,
  },
  // https://github.com/vercel/next.js/issues/24781
  // Font optimization is broken on Next 12.1 with getServerSideProps
  optimizeFonts: false,
  optimization: {
    // ensure that hashes change even when emitted files change only from
    // plugin changes
    realContentHash: true,
  },
  // This gets set at build time for the client but runtime for the server. The
  // value of assetPrefix on the initial server-rendered page load persists on
  // client navigation.
  // We only define the CDN variables on deploy.
  assetPrefix: IS_ARCHIVE ? '' : process.env.CDN_ORIGIN,
  // Set the basePath to the path prefix for puzzles.mit.edu archival.
  // posthunt-client contains the combined hunt domain subpaths and reg-client
  // is used for registration.mypuzzlehunt.com
  basePath: basePath,

  webpack: (config, { buildId, dev, isServer, webpack }) => {
    // Replaces the static path with contenthash in production only.
    const fileLoaderHashName = (resourcePath, resourceQuery) => {
      const staticPath = 'static';
      if (process.env.NODE_ENV === 'development') {
        return `${staticPath}/[path][name].[ext]`;
      } else {
        return `${staticPath}/[path][contenthash].[ext]`;
      }
    };
    const hashName = (resourcePath, resourceQuery) => {
      const staticPath = 'static';
      if (process.env.NODE_ENV === 'development') {
        return `${staticPath}/[path][name][ext][query]`;
      } else {
        return `${staticPath}/[path][contenthash][ext][query]`;
      }
    };

    if (
      USE_ENCRYPTION_PLUGIN &&
      !IS_STATIC &&
      process.env.NODE_ENV !== 'development'
    ) {
      // Map imports starting with 'encrypted/'
      // This is mainly used for where a solution file wants to import from its
      // encrypted puzzle module. This is necessary because all the encrypted
      // filenames get renamed for staging/prod.
      //
      // // @ts-ignore
      // import { grid } from 'encrypted/path/to/puzzle';
      //
      // Note that typescript will not be able to resolve the module name, so
      // it must be ignored.
      config.plugins.push(
        new webpack.NormalModuleReplacementPlugin(
          /^encrypted\//,
          (resource) => {
            // hash the basename
            const name = hash(resource.request.split('/').pop(), 'hex').substr(
              0,
              FILENAME_HASH_LENGTH
            );
            resource.request = `encrypted/${name}`;
          }
        )
      );
    }

    // Allow requiring images directly from 'assets/{slug}/{image}.png'
    config.resolve.alias.assets = path.resolve('./assets');

    // Allow imports from symlinked files
    config.resolve.symlinks = false;

    // Override next.js contenthash to not conflict with hashes in puzzle slugs.
    // chunks/name.contenthash.js is important for encrypted files below.
    if (!isServer) {
      const oldFilename = config.output.filename;
      config.output.filename = oldFilename.replace(
        /\[name\]-\[contenthash\]/,
        '[name].[contenthash]'
      );
    }

    const assetGenerator = {
      filename: hashName,
    };

    // Fix Next.js bug with asset/inline https://github.com/vercel/next.js/discussions/36981
    // and override with our hashName function
    config.module.generator['asset/resource'] = assetGenerator;
    config.module.generator['asset/source'] = assetGenerator;
    delete config.module.generator['asset'];

    // Adds ReactComponent named import to svgs
    // import svgUrl, { ReactComponent as SvgComponent } from 'path/to/file.svg';
    // will set svgUrl to the url of the svg and SvgComponent as an inlineable component.
    config.module.rules.push({
      test: /\.svg$/,
      resourceQuery: '',
      use: [
        {
          loader: '@svgr/webpack',
          options: {
            prettier: false,
            svgo: false,
            svgoConfig: {
              plugins: [{ removeViewBox: false }],
            },
            titleProp: true,
            ref: true,
          },
        },
        {
          loader: 'file-loader',
          options: {
            name: fileLoaderHashName,
          },
        },
      ],
      issuer: {
        and: [/\.(ts|tsx|js|jsx|md|mdx)$/],
      },
    });

    const assetExts = {};

    // file types to import by url
    assetExts.resource = [
      // images
      'gif',
      'ico',
      'jpeg',
      'jpg',
      'png',
      'webp',

      // sound
      'mp3',
      'm4a',
      'wav',

      'pdf',
      'zip',
      'wasm',

      // fonts
      'otf',
      'ttf',

      //other
      'tzx',
      'bas',
    ];

    // file types to import by file contents
    assetExts.source = [
      // text files
      'txt',
      'lvl',
      'sol',

      // python for pyodide
      'py',
    ];

    // file types to import by data url
    assetExts.inline = [];

    const testRegex = (exts) => new RegExp(`\.(${exts.join('|')})$`);

    for (const type of ['resource', 'source', 'inline']) {
      if (assetExts[type].length > 0) {
        config.module.rules.push({
          test: testRegex(assetExts[type]),
          type: `asset/${type}`,
        });
      }
    }

    // YAML files
    config.module.rules.push({
      test: /\.ya?ml$/,
      type: 'json',
      loader: 'yaml-loader',
    });

    // Override asset module type when given explicitly
    config.module.rules.push({
      resourceQuery: /inline/, // import img from 'path/to/asset.png?inline'
      type: 'asset/inline',
    });
    config.module.rules.push({
      resourceQuery: /source/, // import img from 'path/to/asset.png?source'
      type: 'asset/source',
    });
    config.module.rules.push({
      resourceQuery: /resource/, // import img from 'path/to/asset.png?resource'
      type: 'asset/resource',
    });

    if (!IS_STATIC && !USE_WORKER) {
      // Override with our custom build manifest plugin while hunt is active.
      config.plugins.push(
        new BuildManifestPlugin({
          buildId,
          modern: config.experimental ? config.experimental.modern : false,
        })
      );
    }
    if (USE_ENCRYPTION_PLUGIN && !IS_STATIC && !isServer) {
      config.plugins.push(new EncryptionPlugin({ dev }));
    }

    // Provide plugins for jQuery. Unfortunately the page_flip and shine_image
    // implementations use this; ideally we would tear it out entirely.
    config.plugins.push(
      new webpack.ProvidePlugin({
        $: 'jquery',
        jQuery: 'jquery',
      })
    );

    return config;
  },

  // Build-time env variables, will be statically compiled into code to allow
  // for dead-code elimination.
  env: {
    // Whether or not to include static site features like in-browser
    // answer-checker, etc. Intended for post-hunt deployment.
    isArchive: IS_ARCHIVE,
    isStatic: IS_STATIC,
    useWorker: USE_WORKER,
    useEncryptionPlugin: USE_ENCRYPTION_PLUGIN,
    basePath: basePath,
    storagePrefix: STORAGE_PREFIX,
    // The name of hints.
    // FIXME
    hintsName: 'hints',
    // The domain name of the site to deploy.
    domainName: 'mypuzzlehunt.com',
    FILENAME_HASH_LENGTH,
  },
  // Runtime env variables
  publicRuntimeConfig: {
    GOOGLE_ANALYTICS_ID: process.env.GOOGLE_ANALYTICS_ID,
  },
};
