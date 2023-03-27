import React, { FC, HTMLProps } from 'react';
import parse from 'html-react-parser';
import cx from 'classnames';
import { Transition } from '@headlessui/react';

import { formattedDateTime } from 'utils/timer';

export interface Guess {
  timestamp: string;
  guess: string;
  response: string;
  isCorrect?: boolean;
}

interface Props {
  guesses: Guess[];
}

const GuessBox: FC<Props & HTMLProps<HTMLDivElement>> = ({
  guesses,
  className,
}) => {
  return (
    <Transition
      className={cx(className, 'overflow-auto rounded-md drop-shadow-md')}
      show={guesses.length > 0}
      leave="fading"
      leaveFrom="opacity-100"
      leaveTo="opacity-0"
    >
      <table>
        <thead>
          <tr>
            <th className="text-center">Guesses</th>
            <th className="text-center">Response</th>
            <th className="text-center">Time</th>
          </tr>
        </thead>
        <tbody>
          {guesses.map(({ timestamp, guess, response, isCorrect }, i) => (
            <tr key={i} className={cx({ correct: isCorrect })}>
              <td
                className={cx('guess flex justify-center', {
                  small: guess.length >= 16,
                })}
              >
                <pre className="font-mono inline-block">{guess}</pre>
              </td>
              <td className="text-center">{parse(response)}</td>
              <td className="text-center" suppressHydrationWarning>
                {formattedDateTime(timestamp, {
                  month: 'numeric',
                  year: '2-digit',
                  second: 'numeric',
                })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <style jsx>{`
        :global(.fading) {
          background: rgba(255, 91, 91, 0.5);
          transition: opacity linear 0.5s;
        }

        table {
          margin: 8px 0;
          max-height: 240px;
          width: 100%;
        }

        .guess {
          font-size: 20px;
          white-space: normal;
          word-wrap: break-word;
          word-break: break-word;
          text-overflow: clip;
        }

        .guess.small {
          font-size: 16px;
        }

        td {
          padding: 4px 8px;
        }

        .correct {
          font-weight: bold;
          color: var(--primary);
        }
      `}</style>
    </Transition>
  );
};

export default GuessBox;
