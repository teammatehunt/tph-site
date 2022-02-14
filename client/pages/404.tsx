import Head from 'next/head';
import Link from 'next/link';

import Section from 'components/section';
import error404 from 'assets/public/404.png';

export default function Custom404() {
  return (
    <>
      <Head>
        <title>404 - Page Not Found</title>
      </Head>

      <Section center className="flex-center">
        Page Not Found
        <Link href="/">
          <a>Back to Puzzles</a>
        </Link>
      </Section>

      <style jsx>{`
        img {
          width: 450px;
          max-height: 80vh;
          max-width: 60vh;
          height: auto;
          margin-bottom: 12px;
        }

        p {
          font-size: 1.2rem;
        }

        :global(section) {
          display: flex;
          height: 90vh;
          flex-direction: column;
          justify-content: center;
        }

        @media (max-width: 800px) {
          img {
            width: 400px;
          }
        }
      `}</style>
    </>
  );
}
