import React, { useContext } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import dynamic from 'next/dynamic';

import HuntCountdown from 'components/countdown';
import HuntInfoContext from 'components/context';
import PuzzlesMap, {
  getPuzzlesMapProps,
  Props as PuzzlesMapProps,
} from 'components/puzzles_map';
import ShadowImage from 'components/shadow_image';
import Section from 'components/section';
import { formattedDateTime } from 'utils/timer';
import logo from 'assets/public/logo.png';

const LandingSection = ({ huntInfo }) => {
  return (
    <Section center>
      <p>
        <em>Coming to Town</em>
      </p>
      <p>
        {/* Suppress hydration because local time will not match server time. */}
        <strong className="small-caps" suppressHydrationWarning>
          {formattedDateTime(huntInfo.startTime)}
        </strong>{' '}
        –{' '}
        <strong className="small-caps" suppressHydrationWarning>
          {formattedDateTime(huntInfo.endTime)}
        </strong>
      </p>
    </Section>
  );
};

const PreHunt = () => {
  const { huntInfo, userInfo } = useContext(HuntInfoContext);

  return (
    <>
      <div className="hero">
        <img src={logo} alt="FIXME Puzzle Hunt presented by a team" />
      </div>

      {!userInfo?.teamInfo ? (
        <LandingSection huntInfo={huntInfo} />
      ) : (
        // Otherwise, show the countdown
        <Section center>
          <HuntCountdown />
        </Section>
      )}

      <style jsx>{`
        .hero {
          text-align: center;
        }

        .hero img {
          max-width: 800px;
          max-height: 400px;
        }

        .col {
          margin: 20px auto;
          padding: 20px;
          max-width: 580px;
          min-width: 240px;
        }

        @media (max-width: 600px) {
          .hero img {
            width: calc(100vw - 16px);
            height: calc(60vw - 8px);
          }
        }
      `}</style>
    </>
  );
};

const LandingPage: React.FC<PuzzlesMapProps> = (props) => {
  const { huntInfo, userInfo } = useContext(HuntInfoContext);

  return (
    <>
      <Head>
        <title>Hunt Title FIXME</title>
      </Head>

      {
        // If the hunt has not yet started...
        huntInfo.secondsToStartTime > 0 ? (
          <PreHunt />
        ) : (
          <PuzzlesMap {...props} />
        )
      }
    </>
  );
};

export default LandingPage;
export const getServerSideProps = getPuzzlesMapProps;
