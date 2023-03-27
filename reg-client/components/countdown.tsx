import React, { FC, useContext, useEffect, useState } from 'react';

import HuntInfoContext from 'components/context';
import { TimeConfig, displayTimeLeft } from 'utils/timer';

interface Props {
  seconds: number;
  textOnCountdownFinish?: React.ReactNode;
  countdownFinishCallback: () => void;
  showHours?: boolean;
  compact?: boolean;
  heading?: boolean;
  render?: (tick: number, fps: number, options: TimeConfig) => JSX.Element;
}

// Remaining time on the countdown when it should expire. Useful for testing.
const EXPIRES_AT_MILLISECONDS = 0;
// The countdown ticks every <this many> milliseconds.
const RESOLUTION_MILLISECONDS = 1000;

export const Countdown: FC<Props> = ({
  seconds,
  textOnCountdownFinish,
  countdownFinishCallback,
  showHours = false,
  compact = false,
  heading = false,
  render,
}) => {
  const datetime = new Date().getTime() + 1000 * seconds;
  const getTimeDiff = () => {
    return datetime - new Date().getTime();
  };

  const [timeLeftMilliseconds, setTimeLeftMilliseconds] = useState(
    getTimeDiff()
  );
  useEffect(() => {
    let interval: number | null = null;

    if (typeof window !== 'undefined') {
      const refresh = () => {
        const time = getTimeDiff();
        setTimeLeftMilliseconds(time);
        if (time > EXPIRES_AT_MILLISECONDS) {
          // If there is still time on the countdown, recalculate time remaining after one more tick
          window.setTimeout(refresh, RESOLUTION_MILLISECONDS);
        } else if (
          time >
          EXPIRES_AT_MILLISECONDS - 2 * RESOLUTION_MILLISECONDS
        ) {
          // Ensure the callback runs once for anyone with the page open at countdown expiration,
          // with a small buffer in case the setTimeout drifts slightly over 1 tick
          countdownFinishCallback();
          if (interval != null) {
            window.clearInterval(interval);
          }
        }
        // In all other cases, don't let the callback run on page load
      };
      interval = window.setTimeout(refresh, RESOLUTION_MILLISECONDS);
    }

    return () => {
      if (interval) {
        window.clearInterval(interval);
      }
    };
  }, []);

  return timeLeftMilliseconds <= EXPIRES_AT_MILLISECONDS &&
    textOnCountdownFinish ? (
    <>{textOnCountdownFinish}</>
  ) : (
    (render ?? displayTimeLeft)(timeLeftMilliseconds, RESOLUTION_MILLISECONDS, {
      showDays: showHours,
      showHours,
      compact,
      verbose: true,
      warningAt: 0,
      heading,
    })
  );
};
