import React, { FC, useContext, useEffect, useState } from 'react';
import Router from 'next/router';

import HuntInfoContext from 'components/context';
import { TimeConfig, displayTimeLeft, displayTimeLeftBig } from 'utils/timer';

interface Props {
  seconds: number;
  textOnCountdownFinish?: string;
  countdownFinishCallback: () => void;
  showHours?: boolean;
  compact?: boolean;
  bigNumbers?: boolean;
  render?: (tick: number, fps: number, options: TimeConfig) => JSX.Element;
}

export const Countdown: FC<Props> = ({
  seconds,
  textOnCountdownFinish,
  countdownFinishCallback,
  showHours = false,
  compact = false,
  bigNumbers = false,
  render,
}) => {
  const datetime = new Date().getTime() + 1000 * seconds;
  const getTimeDiff = () => {
    return datetime - new Date().getTime();
  };

  const [timeLeft, setTimeLeft] = useState(getTimeDiff());
  useEffect(() => {
    let interval: number | null = null;

    if (typeof window !== 'undefined') {
      const refresh = () => {
        const time = getTimeDiff();
        setTimeLeft(time);
        if (time > 0) {
          window.setTimeout(refresh, 1000);
        } else {
          countdownFinishCallback();
        }
      };
      interval = window.setTimeout(refresh, 1000);
    }

    return () => {
      if (interval) {
        window.clearInterval(interval);
      }
    };
  }, []);

  const display = bigNumbers ? displayTimeLeftBig : displayTimeLeft;

  return timeLeft <= 0 && textOnCountdownFinish ? (
    <span>{textOnCountdownFinish}</span>
  ) : (
    (render ?? display)(timeLeft, 1000, {
      showDays: showHours,
      showHours,
      compact,
      verbose: true,
      warningAt: 0,
    })
  );
};

const HuntCountdown: FC<{}> = () => {
  const { huntInfo } = useContext(HuntInfoContext);
  return (
    <>
      <div
        className="container flex-center-vert"
        aria-label="The hunt begins in..."
      >
        {/* FIXME */}
        <Countdown
          seconds={huntInfo.secondsToStartTime}
          textOnCountdownFinish="🎪 Setting up the carnival..."
          countdownFinishCallback={Router.reload}
          showHours
          bigNumbers
        />
      </div>

      <style jsx>{`
        span {
          background: var(--background);
          padding: 0 12px;
        }

        .container {
          aspect-ratio: 860 / 164;
          background-size: 100%;
          background-repeat: no-repeat;
          margin: 20px auto;
          max-width: 680px;
          width: 90vw;
          height: calc(min(680px, 90vw) * 164 / 860); /* Safari workaround */
        }

        @media (max-width: 800px) {
          font-size: 18px;
        }
      `}</style>
    </>
  );
};
export default HuntCountdown;
