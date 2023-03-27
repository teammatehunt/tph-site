import React, { useEffect, useMemo, useRef, useState } from 'react';
import App, { AppContext, AppProps } from 'next/app';
import getConfig from 'next/config';
import Error from 'next/error';
import Head from 'next/head';
import { useRouter } from 'utils/router';
import cryptoAES from 'crypto-js/aes';
import cryptoHex from 'crypto-js/enc-hex';
import cryptoUtf8 from 'crypto-js/enc-utf8';
import Modal from 'react-modal';
import nextCookies from 'next-cookies';
import 'react-responsive-carousel/lib/styles/carousel.min.css';
import 'styles/globals.css';

import Error404 from 'pages/404';
import Layout from 'components/layout';
import HuntInfoContext, { EMPTY_HUNT_INFO, HuntInfo } from 'components/context';
import HuntNotifications from 'components/hunt_notifications';
import { initBuildManifestProxy } from 'utils/buildManifestProxy';
import { serverFetch, clientFetch, addDecryptionKeys } from 'utils/fetch';
import { dragPatch } from 'utils/dragpatch';
import * as ga from 'utils/google_analytics';
import { createWorker } from 'utils/worker';
import { useSessionUuid } from 'utils/uuid';

const {
  publicRuntimeConfig: { ASSET_PREFIX },
} = getConfig();

type Props = AppProps & {
  huntInfo: HuntInfo;
  cookies?: Record<string, string>;
};

// custom app documentation: https://nextjs.org/docs/advanced-features/custom-app

// Overriding MyApp.getInitialProps will make a page fail to statically
// generate, even if it has no server-side dependencies. This is fine during
// hunt, but any custom props should later be defined inside the body of MyApp
// instead.

export default function MyApp({
  Component,
  pageProps,
  huntInfo,
  cookies = {},
}: Props) {
  if (process.env.isStatic) {
    try {
      huntInfo = require('assets/json_responses/hunt_info.json');
    } catch {
      huntInfo = EMPTY_HUNT_INFO;
    }
  }

  // Set global on client to allow decrypting.
  // We want this to happen at the start of first render to ensure it's
  // available before other scripts can run.
  if (typeof window !== 'undefined') {
    (window as unknown as any).CryptoJS = {
      AES: cryptoAES,
      enc: { Hex: cryptoHex, Utf8: cryptoUtf8 },
    };
  }

  // Add decryption keys if available and remove from pageProps
  pageProps = addDecryptionKeys(pageProps);
  // Default to 200 if no statusCode is explicitly given
  const {
    puzzleData,
    act,
    roundSlug,
    theme = 'hunt',
    statusCode = 200,
    bare = false,
  } = pageProps;

  const router = useRouter();
  const uuid = useSessionUuid();

  // note huntInfo here is the { huntInfo, userInfo } object.
  const huntIsOver = new Date() > new Date(huntInfo.huntInfo.endTime);

  useEffect(() => {
    // Set app element for accessibility reasons.
    Modal.setAppElement('body');
    // Apply a monkeypatch to support drag events in Firefox
    dragPatch();
  }, []);

  useEffect(() => {
    initBuildManifestProxy();
  }, []);

  useEffect(() => {
    const handleRouteChange = (url) => ga.pageview(url);
    router.events.on('routeChangeComplete', handleRouteChange);
    return () => {
      router.events.off('routeChangeComplete', handleRouteChange);
    };
  }, [router.events]);
  const basePath = router.asPath.split('#')[0]; // grab the path before hash

  const createdWorker = useRef(false);
  if (process.env.useWorker && !createdWorker.current) {
    if (!bare) createWorker();
    createdWorker.current = true;
  }

  const huntAct = act ?? puzzleData?.round?.act ?? 1;
  const augmentedHuntInfo: HuntInfo = {
    ...huntInfo,
    uuid,
    // If on a round/puzzle page, override the theme with the round slug.
    round: {
      theme,
      slug: roundSlug ?? puzzleData?.round?.slug,
      act: huntAct,
    },
  };

  const origin = `https://${process.env.domainName}`;

  let content;
  if (bare) {
    content = (
      <HuntInfoContext.Provider value={augmentedHuntInfo}>
        <Component {...pageProps} />
      </HuntInfoContext.Provider>
    );
  } else {
    // Wrap all components in context so that hunt info is accessible anywhere.
    content = (
      <HuntInfoContext.Provider value={augmentedHuntInfo}>
        <Layout>
          {statusCode === 404 ? (
            <Error404 />
          ) : statusCode >= 500 ? (
            <Error statusCode={statusCode} />
          ) : (
            <>
              <HuntNotifications />
              <Component {...pageProps} />
            </>
          )}
        </Layout>
      </HuntInfoContext.Provider>
    );
  }

  return (
    <>
      <Head>
        <meta property="og:title" content="FIXME Hunt" />
        <meta property="og:site_name" content="FIXME Hunt" />
        <meta
          property="og:description"
          content="The FIXME Hunt hosted by team name"
        />
        <meta
          key="og-image"
          property="og:image"
          content={
            /* This image needs to point to an absolute url */
            new URL(`${ASSET_PREFIX ?? ''}/banner.png`, origin).href
          }
        />
        <meta property="og:url" content={origin} />
        <meta property="twitter:card" content="summary_large_image" />
        <meta
          property="twitter:image:alt"
          content="The FIXME Hunt hosted by team name"
        />

        <link
          key="favicon"
          rel="shortcut icon"
          href={`${ASSET_PREFIX ?? ''}/favicon.ico`}
          type="image/vnd.microsoft.icon"
        />
      </Head>

      {content}

      <style global jsx>{`
        body {
          background-color: ${bare ? 'transparent' : 'inherit'};
        }
      `}</style>
    </>
  );
}

MyApp.getInitialProps = async (appContext: AppContext) => {
  let huntInfo: HuntInfo;
  let domain: string = '';

  const { pageProps, ...appProps } = await App.getInitialProps(appContext);

  let { statusCode = 200 } = pageProps;

  if (pageProps?.bare || statusCode >= 500) {
    // Next.js tries to staticly generate a 500 page during production build.
    // (This is a bug that was recently fixed in Next.js for 404 but not 500.)
    // TODO: Determine implications and decide whether we need to bypass
    // another way or build a custom _error.tsx component with getInitialProps.
    huntInfo = EMPTY_HUNT_INFO;
  } else if (typeof window === 'undefined') {
    if (process.env.isStatic) {
      // TODO: figure out what to do with the domain in the static case
      try {
        huntInfo = require('assets/json_responses/hunt_info.json');
      } catch {
        huntInfo = EMPTY_HUNT_INFO;
      }
    } else {
      huntInfo = await serverFetch<HuntInfo>(appContext.ctx, '/hunt_info', {
        method: 'GET',
      });
    }
  } else {
    huntInfo = await clientFetch<HuntInfo>(
      appContext.ctx,
      '/hunt_info',
      {
        method: 'GET',
      },
      true
    );
  }

  // Pass the cookies to the app.
  const cookies = nextCookies(appContext.ctx);

  return {
    cookies,
    huntInfo,
    pageProps,
    ...appProps,
  };
};
