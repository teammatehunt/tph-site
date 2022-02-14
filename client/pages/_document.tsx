import Document, { Html, Head, Main, NextScript } from 'next/document';

import flush from 'styled-jsx/server';

import { GOOGLE_ANALYTICS_ID } from 'utils/google_analytics';

export default class MyDocument extends Document {}

// Inject jsx styles in server-side rendering
MyDocument.getInitialProps = async (ctx) => {
  const initialProps = await Document.getInitialProps(ctx);
  return {
    ...initialProps,
    styles: (
      <>
        {initialProps.styles}
        {flush()}
      </>
    ),
  };
};
