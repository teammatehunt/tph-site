import Document, { Html, Head, Main, NextScript } from 'next/document';

import * as ga from 'utils/google_analytics';

// FIXME: Update fonts
const GOOGLE_FONTS =
  'https://fonts.googleapis.com/css2?family=DM+Mono&family=Quicksand:ital,wght@0,400;0,500;0,700;1,400&display=swap';

export default function MyDocument() {
  return (
    <Html>
      <Head>
        <link rel="preconnect" href="https://fonts.gstatic.com" />
        <link href={GOOGLE_FONTS} rel="stylesheet" />

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
      </body>
    </Html>
  );
}
