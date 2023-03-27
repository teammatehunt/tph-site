import { useContext } from 'react';
import Head from 'next/head';
import Link from 'components/link';

import HuntInfoContext from 'components/context';
import PublicAccessLink from 'components/public_access';
import Section from 'components/section';

export default function Custom404() {
  const { userInfo } = useContext(HuntInfoContext);
  return (
    <>
      <Head>
        <title>404 - Page Not Found</title>
      </Head>

      <Section
        center
        className="flex flex-col items-center justify-center h-[90vh]"
      >
        <h1 className="mb-4">404 - Page Not Found</h1>
        <div className="flex items-center gap-4">
          {!userInfo?.teamInfo && (
            <>
              <PublicAccessLink />
              <Link href="/login">
                <a>Login</a>
              </Link>
            </>
          )}
          <Link href="/">
            <a>Back to Home</a>
          </Link>
        </div>
      </Section>
    </>
  );
}
