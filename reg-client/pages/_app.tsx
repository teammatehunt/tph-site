import React, { useEffect } from 'react';
import App, { AppProps } from 'next/app';
import Error from 'next/error';
import Head from 'next/head';
import { useRouter } from 'next/router';
import Modal from 'react-modal';
import 'styles/globals.css';

import Error404 from 'pages/404';
import HuntInfoContext, { EMPTY_HUNT_INFO, HuntInfo } from 'components/context';
import { serverFetch, clientFetch } from 'utils/fetch';
import * as ga from 'utils/google_analytics';

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
  // Default to 200 if no statusCode is explicitly given
  const { statusCode = 200, puzzleData, bare = false } = pageProps;

  const router = useRouter();

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

  const origin = process.env.isStatic
    ? `https://puzzles.mit.edu/20xx/${process.env.domainName}`
    : `https://${process.env.domainName}`;

  let content;
  if (bare) {
    content = <Component {...pageProps} />;
  } else {
    // Wrap all components in context so that hunt info is accessible anywhere.
    content = (
      <HuntInfoContext.Provider value={huntInfo}>
        {statusCode === 404 ? (
          <Error404 />
        ) : statusCode >= 500 ? (
          <Error statusCode={statusCode} />
        ) : (
          <>
            <Component {...pageProps} />
          </>
        )}
      </HuntInfoContext.Provider>
    );
  }

  return (
    <>
      <Head>
        <meta property="og:title" content="FIXME HUNT" />
        <meta property="og:site_name" content="FIXME HUNT" />
        <meta
          property="og:description"
          content="Welcome to the Museum of Interesting Things! Register now for our grand opening on January 13th."
        />
        <meta
          key="og-image"
          property="og:image"
          content={
            /* This image needs to point to an absolute url */
            `${origin}/banner.png`
          }
        />
        <meta property="og:url" content={origin} />
        <meta property="twitter:card" content="summary_large_image" />
        <meta
          property="twitter:image:alt"
          content="Welcome to the Museum of Interesting Things! Register now for our grand opening on January 13th."
        />

        <link
          key="favicon"
          rel="shortcut icon"
          href={`${router.basePath}/favicon.ico`}
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
    huntInfo = await serverFetch<HuntInfo>(appContext.ctx, '/hunt_info', {
      method: 'GET',
    });
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

  return { huntInfo, ...appProps };
};
