import Document, { Html, Head, Main, NextScript } from 'next/document';

import * as ga from 'utils/google_analytics';

export default function MyDocument() {
  return (
    <Html>
      <Head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Work+Sans:ital,wght@0,300;0,400;0,700;0,900&display=swap"
          rel="stylesheet"
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

      <body>
        <Main />
        <NextScript />

        {/* Need to dangerously set for easter egg to show up in comments */}
        <div
          id="teaser"
          dangerouslySetInnerHTML={{
            __html: `<!-- Midnight Madness -->`,
          }}
        />
      </body>
    </Html>
  );
}
