const path = require('path');
const { RawSource } = require('webpack-sources');

const {
  CLIENT_STATIC_FILES_PATH,
} = require('next/dist/next-server/lib/constants.js');

const IS_STATIC = false;
const USE_WORKER = false;

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
  '/donate',
  '/faq',
  '/leaderboard',
  '/login',
  '/logout',
  '/puzzles',
  '/register',
  '/reset_password',
  '/rules',
  '/story',
  '/have-you-tried',
  '/wrapup',
  '/q-and-a',
  '/team/\\[slug\\]',
  '/hints/\\[slug\\]',
]
  .map((endpoint) => `(\\"\\${endpoint}\\")`)
  .join('|');

// Match any string of the form ,"{url not in the allowlist}":[]
const MANIFEST_REGEX = new RegExp(
  `,(?!${MANIFEST_ALLOWLIST})\\"[^\\[\\]]+?\\":\\[.*?\\]`,
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
              new RawSource(
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

const imageTypes = ['jpg', 'jpeg', 'png', 'svg', 'webp', 'gif', 'ico'];

module.exports = {
  webpack: (config, { buildId, dev, isServer, webpack }) => {
    // Replaces the static path with contenthash in production only.
    const hashName = (resourcePath, resourceQuery) => {
      const staticPath = isServer ? '/_next/static' : 'static';
      if (process.env.NODE_ENV === 'development') {
        return `${staticPath}/[path][name].[ext]`;
      } else {
        return `${staticPath}/[path][contenthash].[ext]`;
      }
    };

    // Allow requiring images directly from 'assets/{slug}/{image}.png'
    config.resolve.alias.assets = path.join(__dirname, 'assets');

    // Override next.js contenthash to not conflict with hashes in puzzle slugs.
    if (!isServer) {
      config.output.filename = config.output.filename.replace(
        /\[name\]-\[chunkhash\]/,
        '[chunkhash]/[name]'
      );
    }

    config.module.rules.push({
      test: new RegExp(`\.(${imageTypes.join('|')})$`),
      loader: 'file-loader',
      options: {
        name: hashName,
      },
    });

    // Load WebAssembly
    config.module.rules.push({
      test: /\.wasm$/,
      type: 'javascript/auto',
      loader: 'file-loader',
      options: {
        name: hashName,
      },
    });

    // Load sound, font, pdf, zip files.
    config.module.rules.push({
      test: /\.(mp3|otf|ttf|pdf|zip)$/i,
      loader: 'file-loader',
      options: {
        name: hashName,
      },
    });

    // Text files
    config.module.rules.push({
      test: /\.(txt|lvl|sol)$/,
      exclude: /node_modules/,
      loader: 'raw-loader',
    });

    // Python files
    config.module.rules.push({
      test: /\.py$/,
      exclude: /node_modules/,
      loader: 'raw-loader',
    });

    // YAML files
    config.module.rules.push({
      test: /\.ya?ml$/,
      type: 'json',
      loader: 'yaml-loader',
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

    // Provide plugins for jQuery. Unfortunately the copy-to-clipboard
    // implementation uses this; ideally we would tear it out entirely.
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
    isStatic: IS_STATIC,
    useWorker: USE_WORKER,
    // FIXME
    // The name of hints.
    hintsName: 'hints',
    // The domain name of the site to deploy.
    domainName: 'mypuzzlehunt.com',
  },
};
