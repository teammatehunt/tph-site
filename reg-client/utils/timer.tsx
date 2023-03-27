import { FC, useEffect, useRef, useState } from 'react';
import cx from 'classnames';

import { Sprite } from 'utils/assets';

export const displayTime = (time: number, pad: number = 2) =>
  Math.max(time, 0).toString().padStart(pad, '0');

export const pluralize = (value: number, str: string) =>
  `${str}${value === 1 ? '' : 's'}`;

export interface TimeConfig {
  showHours?: boolean;
  showDays?: boolean;
  compact?: boolean;
  verbose?: boolean;
  warningAt?: number;
  heading?: boolean;
}

export const getTimeLeft = (
  tick: number,
  fps: number,
  { showHours = false, showDays = false } = {}
) => {
  // Round seconds left up. Otherwise it display "0 seconds" for the final second.
  const totalSeconds = Math.max(0, Math.ceil(tick / fps));
  const days = Math.floor(totalSeconds / 60 / 60 / 24) % 365;
  let hours = Math.floor(totalSeconds / 60 / 60) % 24;
  if (!showDays) {
    hours = 24 * days + hours;
  }
  let minutes = Math.floor(totalSeconds / 60) % 60;
  if (!showHours) {
    minutes = 60 * hours + minutes;
  }
  const seconds = totalSeconds % 60;

  return [days, hours, minutes, seconds, totalSeconds];
};

/**
 * Computes how much time is left for display in a timer.
 */
export const displayTimeLeft = (
  tick: number,
  fps: number,
  options: TimeConfig = {}
) => {
  const [days, hours, minutes, seconds, totalSeconds] = getTimeLeft(
    tick,
    fps,
    options
  );
  const {
    showHours = false,
    showDays = false,
    compact = false,
    verbose = false,
    warningAt = 10,
    heading = false,
  } = options;

  const padding = verbose ? 1 : 2;

  return (
    <span className="countdown" suppressHydrationWarning>
      {showDays && days >= 1 && (
        <span className="countdown-unit">
          <span>{days}</span>{' '}
          <span>
            {pluralize(days, 'day')}
            {!heading && ', '}
          </span>
        </span>
      )}
      {showHours && hours >= 1 && (
        <span className="countdown-unit">
          <span>{displayTime(hours, padding)}</span>
          <span>
            {verbose
              ? ` ${pluralize(hours, 'hour')}${heading ? '' : ', '}`
              : !heading
              ? ':'
              : ''}
          </span>
        </span>
      )}

      {(!compact || (totalSeconds >= 60 && totalSeconds < 60 * 60)) && (
        <span className="countdown-unit">
          <span>{displayTime(minutes, padding)}</span>
          <span>
            {verbose ? ' min' : null}
            {(!compact || totalSeconds < 60) &&
              !heading &&
              (verbose ? ', ' : ':')}
          </span>
        </span>
      )}

      {(!compact || totalSeconds < 60) && (
        <span className="countdown-unit">
          <span
            className={warningAt > 0 && totalSeconds <= warningAt ? 'red' : ''}
            suppressHydrationWarning
          >
            {displayTime(seconds, padding)}
          </span>
          <span>{verbose ? ' sec' : ''}</span>
        </span>
      )}
    </span>
  );
};

export const formattedDateTime = (
  time: string | null | undefined,
  {
    year = 'numeric',
    month = 'short',
    day = 'numeric',
    weekday = 'short',
    hour = 'numeric',
    minute = 'numeric',
    second = undefined,
    timeZoneName = 'short',
  }: Intl.DateTimeFormatOptions = {}
) => {
  if (!time) {
    return '';
  }
  const date = new Date(time);
  return date.toLocaleDateString(undefined, {
    year: year ?? undefined,
    month: month ?? undefined,
    day: day ?? undefined,
    weekday: weekday ?? undefined,
    hour: hour ?? undefined,
    minute: minute ?? undefined,
    second: second ?? undefined,
    timeZoneName: timeZoneName ?? undefined,
  });
};

export const sortTime = (time: string | null | undefined) => {
  if (!time) {
    return Number.MAX_VALUE;
  }
  // don't need to localize, as long as sort order is consistent.
  const date = new Date(time);
  return date.getTime();
};

export const formattedDate = (time: string) =>
  formattedDateTime(time, {
    hour: undefined,
    minute: undefined,
    timeZoneName: undefined,
  });

export const formattedTime = (
  time: string,
  {
    hour = 'numeric',
    minute = 'numeric',
    second = undefined,
    timeZoneName = 'short',
  }: Intl.DateTimeFormatOptions = {}
) => {
  const date = new Date(time);
  return date.toLocaleTimeString(undefined, {
    hour: hour ?? undefined,
    minute: minute ?? undefined,
    second: second ?? undefined,
    timeZoneName: timeZoneName ?? undefined,
  });
};

export const TICK_SOUND_EFFECTS: Sprite = {
  src: 'public/tick',
  sprite: {
    tick: [0, 1000],
    tickFast: [2000, 1000],
    tickFaster: [3000, 1000],
    tickFastest: [4000, 1000],
  },
};

export const CountdownFrom = ({ timeLeft, onTimeout }) => {
  const [timer, setTimer] = useState(timeLeft);
  const timerInterval = useRef<number | null>(null);
  // When the time changes, restart the timer
  useEffect(() => {
    setTimer(timeLeft);
    if (timerInterval.current) {
      window.clearInterval(timerInterval.current);
    }
    timerInterval.current = window.setInterval(
      () =>
        setTimer((timer) => {
          if (timer <= 0 && timerInterval.current) {
            onTimeout();
            window.clearInterval(timerInterval.current);
            timerInterval.current = null;
          }

          return Math.max(0, timer - 1);
        }),
      1000
    );
  }, [timeLeft, onTimeout]);

  return <>{timer}</>;
};

export const TimerBarFrom = ({
  timeLeft,
  onTimeout,
  className = '',
  barClassName = '',
}) => {
  const [timer, setTimer] = useState(timeLeft);
  const timerInterval = useRef<number | null>(null);
  // When the time changes, restart the timer
  useEffect(() => {
    setTimer(timeLeft);
    const removeCallback = () => {
      if (timerInterval.current) {
        window.clearInterval(timerInterval.current);
        timerInterval.current = null;
      }
    };
    timerInterval.current = window.setInterval(
      () =>
        setTimer((timer) => {
          if (timer <= 0) {
            onTimeout();
            removeCallback();
          }

          return Math.max(0, timer - 1);
        }),
      1000
    );
    return removeCallback;
  }, [timeLeft, onTimeout]);

  return (
    <div className={cx('border w-full', className)}>
      <div
        className={cx('w-full h-full bar', barClassName)}
        style={{
          animation: `timer ${timeLeft}s linear forwards`,
          transformOrigin: 'left',
        }}
      />
      <style jsx>{`
        .bar {
          transform: scaleX(0);
        }
        @keyframes timer {
          to {
            transform: scaleX(1);
          }
        }
      `}</style>
    </div>
  );
};
