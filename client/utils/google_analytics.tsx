import getConfig from 'next/config';

const nextConfig = getConfig();
export const GOOGLE_ANALYTICS_ID = process.env.isStatic
  ? process.env.GOOGLE_ANALYTICS_ID
  : nextConfig.publicRuntimeConfig.GOOGLE_ANALYTICS_ID;

// log the pageview with their URL
export const pageview = (url) => {
  window.gtag('config', GOOGLE_ANALYTICS_ID, {
    page_path: url,
  });
};

// log specific events happening.
export const event = ({ action, params }) => {
  window.gtag('event', action, params);
};
