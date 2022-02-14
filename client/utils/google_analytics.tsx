export const GOOGLE_ANALYTICS_ID = 'FIXME';

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
