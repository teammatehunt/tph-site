import React, { useContext } from 'react';
import Head from 'next/head';
import Link from 'components/link';
import { useRouter } from 'utils/router';
import cx from 'classnames';
import dynamic from 'next/dynamic';

import Custom404 from 'pages/404';
import { clientFetch } from 'utils/fetch';
import { Countdown } from 'components/countdown';
import HuntInfoContext from 'components/context';
import PublicAccessLink from 'components/public_access';
import RoundMap from 'components/round_map';
import { RoundData } from 'components/puzzles_map';
import Section from 'components/section';
import { serverFetch } from 'utils/fetch';

import heroImg from 'assets/museum/hero.png';

interface RoundProps {
  bg?: string;
  rounds?: RoundData[];
  ratio?: number; // Aspect ratio for bg image
}

// FIXME: Update landing page with your own design

interface TicketProps {
  className?: string;
}
const Ticket: React.FC<TicketProps> = ({ className, children }) => (
  <div className={cx('wrapper w-full', className)}>
    <img
      className="hero-img w-full"
      src={heroImg}
      alt="Ticket titled Museum of Interesting Things. Hours of operation: Jan 13, 2023, 1pm ET - Jan 15, 2023, 6pm. Presented by: Your friends at teammate, MIT Curators"
    />
    <div className="bg-white p-8">{children}</div>

    <style jsx>{`
      .wrapper {
        box-shadow: 0 6px 10px #ccc;
      }
    `}</style>
  </div>
);

const HuntCountdown = () => {
  const { huntInfo, userInfo } = useContext(HuntInfoContext);
  const router = useRouter();

  return (
    <>
      <Section className="w-[80vw] h-[80vh] flex items-center">
        <div className="relative">
          <Ticket className="absolute inset-0" />
          <Ticket className="-rotate-3">
            <div className="flex flex-col items-center justify-center gap-y-4">
              <h3 className="primary">The museum opens in...</h3>
              <Countdown
                seconds={huntInfo.secondsToStartTime}
                countdownFinishCallback={() => {
                  userInfo?.teamInfo && router.reload();
                }}
                showHours
                heading={true}
              />
            </div>
          </Ticket>
        </div>
      </Section>

      <style global jsx>{`
        .countdown {
          display: flex;
          gap: 20px;
        }
        .countdown-unit {
          display: flex;
          flex-direction: column;
          font-size: 3rem;
          line-height: 3rem;
          justify-content: center;
          align-items: center;
        }

        .countdown-unit span:first-child {
          color: var(--primary);
        }
        .countdown-unit span:last-child {
          font-size: 2rem;
          line-height: 2rem;
        }
      `}</style>
    </>
  );
};

const HuntOver = () => {
  return (
    <>
      <Section className="w-[80vw] h-[80vh] flex items-center">
        <div className="relative">
          <Ticket className="absolute inset-0" />
          <Ticket className="-rotate-3">
            <div className="flex flex-col items-center justify-center gap-y-4 text-black">
              <h3 className="primary">The 2023 MIT Mystery Hunt is over.</h3>
              <p>
                Browse the museum as <PublicAccessLink />
                {!process.env.isStatic && (
                  <>
                    , or <Link href="/login">login here</Link>
                  </>
                )}
                .
              </p>
            </div>
          </Ticket>
        </div>
        <style jsx>{`
          div h3 {
            color: #28766e !important; /* Actions (button background) */
          }
          :global(a) {
            color: #28766e !important; /* Actions (button background) */
          }
          :global(body a):hover {
            color: #28766e !important; /* Actions (button background) */
          }
        `}</style>
      </Section>
    </>
  );
};

const LandingPage: React.FC<RoundProps> = ({ rounds, ...props }) => {
  const { huntInfo, userInfo } = useContext(HuntInfoContext);
  const huntEnded = true;

  if (!rounds) {
    return <Custom404 />;
  }

  return (
    <>
      <Head>
        <title>FIXME HUNT</title>
      </Head>

      {
        // Hunt ended
        huntEnded && !userInfo?.teamInfo ? (
          <HuntOver />
        ) : // If the hunt has not yet started
        huntInfo.secondsToStartTime > 0 && !userInfo?.superuser ? (
          <HuntCountdown />
        ) : (
          <RoundMap rounds={rounds} {...props} />
        )
      }
    </>
  );
};

export default LandingPage;

export const getServerSideProps = async (context) => {
  const props = await serverFetch<RoundProps>(context, '/rounds');
  return { props };
};
