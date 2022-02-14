import React, { useEffect, useMemo, useRef, useState } from 'react';
import App, { AppProps } from 'next/app';
import Error from 'next/error';
import Head from 'next/head';
import { useRouter } from 'next/router';
import Modal from 'react-modal';
import nextCookies from 'next-cookies';
import 'styles.css';
import 'react-responsive-carousel/lib/styles/carousel.min.css';
import useCookie from 'react-use-cookie';

import Error404 from 'pages/404';
import Layout from 'components/layout';
import HuntInfoContext, { EMPTY_HUNT_INFO, HuntInfo } from 'components/context';
import { serverFetch, clientFetch } from 'utils/fetch';
import * as ga from 'utils/google_analytics';
import SolvedNotifications from 'components/solved_notifications';
import { createWorker } from 'utils/worker';

// FIXME: replace font
import headerFont from 'assets/public/Sandorian-Normal.otf';

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

    /** FIXME: uncomment if need to use cookies.
    useEffect(() => {
      const cookies = nextCookies({});
    }, []);
    */
  }

  // Default to 200 if no statusCode is explicitly given
  const { statusCode = 200, puzzleData, bare = false } = pageProps;

  const router = useRouter();

  // note huntInfo here is the { huntInfo, userInfo } object.
  const huntIsOver = new Date() > new Date(huntInfo.huntInfo.endTime);

  useEffect(() => {
    // Set app element for accessibility reasons.
    Modal.setAppElement('body');
  }, []);

  useEffect(() => {
    const handleRouteChange = (url) => ga.pageview(url);
    router.events.on('routeChangeComplete', handleRouteChange);
    return () => {
      router.events.off('routeChangeComplete', handleRouteChange);
    };
  }, [router.events]);

  const isIntroSolution = !!(
    router.pathname.startsWith('/solutions/') && puzzleData?.isIntro
  );
  const isWrapup =
    router.pathname.startsWith('/wrapup') ||
    router.pathname.startsWith('/q-and-a');

  const createdWorker = useRef(false);
  if (process.env.useWorker && !createdWorker.current) {
    if (!bare) createWorker();
    createdWorker.current = true;
  }

  const origin = `https://${process.env.domainName}`;

  let content;
  if (bare) {
    content = <Component {...pageProps} />;
  } else {
    // Wrap all components in context so that hunt info is accessible anywhere.
    content = (
      <HuntInfoContext.Provider value={huntInfo}>
        <Layout>
          {statusCode === 404 ? (
            <Error404 />
          ) : statusCode >= 500 ? (
            <Error statusCode={statusCode} />
          ) : (
            <>
              <SolvedNotifications />
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
        {/* FIXME: update all meta tags appropriately. */}
        <meta property="og:title" content="FIXME Puzzlehunt" />
        <meta property="og:site_name" content="FIXME Puzzlehunt" />
        <meta
          property="og:description"
          content="An online puzzlehunt by FIXME"
        />
        <meta
          key="og-image"
          property="og:image"
          content={
            /* This image needs to point to an absolute url */ new URL(
              'banner.png',
              origin
            ).toString()
          }
        />
        <meta property="og:url" content={origin} />
        <meta property="twitter:card" content="summary_large_image" />
        <meta
          property="twitter:image:alt"
          content="An online puzzlehunt by FIXME"
        />

        <link rel="preconnect" href="https://fonts.gstatic.com" />
        <link
          href="https://fonts.googleapis.com/css2?family=DM+Mono&family=Vollkorn:ital,wght@0,400;0,700;1,400&family=Vollkorn+SC:wght@400;700&display=swap"
          rel="stylesheet"
        />
        <link rel="preload" href={headerFont} as="font" crossOrigin="" />
        <link
          key="favicon"
          rel="shortcut icon"
          href="/favicon.ico"
          type="image/vnd.microsoft.icon"
        />

        {/* Global Site Tag (gtag.js) - Google Analytics */}
        <script
          async
          src={`https://www.googletagmanager.com/gtag/js?id=${ga.GOOGLE_ANALYTICS_ID}`}
        />
        <script
          dangerouslySetInnerHTML={{
            __html: `
            window.dataLayer = window.dataLayer || [];
            function gtag(){dataLayer.push(arguments);};
            gtag('js', new Date());
            gtag('config', '${ga.GOOGLE_ANALYTICS_ID}', {
              page_path: window.location.pathname,
            });
            `.replace(/\s+/g, ' '),
          }}
        />
      </Head>

      {content}

      <style global jsx>{`
        ${!bare
          ? ''
          : `
           body {
             background-color: transparent;
           }
           `}

        @font-face {
          font-family: 'Sandorian';
          src: url(${headerFont});
          font-style: normal;
          font-weight: 400;
          font-display: swap;
        }
      `}</style>
    </>
  );
}

MyApp.getInitialProps = async (appContext) => {
  let huntInfo: HuntInfo;

  const appProps = await App.getInitialProps(appContext);

  const { statusCode = 200 } = appProps.pageProps;

  if (appProps.pageProps?.bare || statusCode >= 500) {
    // Next.js tries to staticly generate a 500 page during production build.
    // (This is a bug that was recently fixed in Next.js for 404 but not 500.)
    // TODO: Determine implications and decide whether we need to bypass
    // another way or build a custom _error.tsx component with getInitialProps.
    huntInfo = EMPTY_HUNT_INFO;
  } else if (typeof window === 'undefined') {
    if (process.env.isStatic) {
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

  return { cookies, huntInfo, ...appProps };
};
