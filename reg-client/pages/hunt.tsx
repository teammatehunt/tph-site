import React from 'react';
import { serverFetch } from 'utils/fetch';

// Should never directly be shown to users, but instead always redirect away
// (to homepage before hunt start, and to hunt site after hunt start)
const HuntRedirectPage = () => {
  return <></>;
};

export default HuntRedirectPage;

interface HuntData {
  huntSite: string;
}

export const getServerSideProps = async (context) => {
  // Use the same headers as in dev to avoid any delays due to stale responses
  // from: https://nextjs.org/docs/going-to-production#caching
  const props = await serverFetch<HuntData>(context, '/hunt_site', {
    'Cache-Control': 'no-cache, no-store, max-age=0, must-revalidate',
  });

  return {
    redirect: {
      permanent: false,
      destination: props.huntSite,
    },
  };
};
