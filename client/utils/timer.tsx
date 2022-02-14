import { FC } from 'react';

import { Sprite } from 'utils/assets';

const displayTime = (time: number, pad: number = 2) =>
  Math.max(time, 0).toString().padStart(pad, '0');

export const pluralize = (value: number, str: string) =>
  `${str}${value === 1 ? '' : 's'}`;

export const BigNumber: FC<{}> = ({ children }) => (
  <span className="number" suppressHydrationWarning>
    {children}

    <style jsx>{`
      color: var(--secondary);
      font-size: min(8vw, 4em);
      margin-right: 4px;
      vertical-align: middle;
    `}</style>
  </span>
);

export interface TimeConfig {
  showHours?: boolean;
  showDays?: boolean;
  compact?: boolean;
  verbose?: boolean;
  warningAt?: number;
}

export const getTimeLeft = (
  tick: number,
  fps: number,
  { showHours = false, showDays = false } = {}
) => {
  // Round seconds left up. Otherwise it display "0 seconds" for the final second.
  const totalSeconds = Math.ceil(tick / fps);
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
  } = options;

  const padding = verbose ? 1 : 2;

  return (
    <span suppressHydrationWarning>
      {showDays && days >= 1 && `${days} ${pluralize(days, 'day')}, `}
      {showHours && hours >= 1 && (
        <>
          {displayTime(hours, padding)}
          {verbose ? ` ${pluralize(hours, 'hour')}, ` : ':'}
        </>
      )}

      {(!compact || (totalSeconds >= 60 && totalSeconds < 60 * 60)) && (
        <>
          {displayTime(minutes, padding)}
          {verbose ? ' min' : null}
        </>
      )}

      {(!compact || totalSeconds < 60) && (
        <>
          {!compact && (verbose ? ', ' : ':')}
          <span
            className={warningAt > 0 && totalSeconds <= warningAt ? 'red' : ''}
            suppressHydrationWarning
          >
            {displayTime(seconds, padding)}
            {verbose ? ' sec' : ''}
          </span>
        </>
      )}
    </span>
  );
};

/**
 * Computes how much time is left for display in a timer.
 */
export const displayTimeLeftBig = (
  tick: number,
  fps: number,
  options: TimeConfig = {}
) => {
  const [days, hours, minutes, seconds] = getTimeLeft(tick, fps, options);
  const { showHours = false, showDays = false } = options;

  return (
    <div className="center">
      {showDays && (
        <span suppressHydrationWarning>
          <BigNumber>{days}</BigNumber> {pluralize(days, 'day')}
        </span>
      )}
      {showHours && (
        <span>
          <BigNumber>{displayTime(hours, 2)}</BigNumber>
          {pluralize(hours, 'hour')}
        </span>
      )}

      <span suppressHydrationWarning>
        <BigNumber>{displayTime(minutes, 2)}</BigNumber>
        {' min'}
      </span>

      <span suppressHydrationWarning>
        <BigNumber>{displayTime(seconds, 2)}</BigNumber>
        {' sec'}
      </span>

      <style jsx>{`
        div {
          color: var(--primary);
          font-size: 12px;
          display: grid;
          grid-template-columns: 1fr 1fr 1fr 1fr;
          grid-gap: 0 12px;
          padding: 0 20px;
          text-transform: uppercase;
          white-space: nowrap;
          width: 100%;
        }

        @media (max-width: 550px) {
          div {
            font-size: 12px;
          }
        }
      `}</style>
    </div>
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
