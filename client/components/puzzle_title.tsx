import React, { FC, ReactNode, useMemo } from 'react';
import cx from 'classnames';

const SPLIT_LENGTH = 20;

/** Programmatically finds the best place to split into two lines. */
const computeSplit = (title: string): [string, string | undefined] => {
  // TODO: handle server errors for puzzleData so this cast isn't necessary
  title = String(title);
  if (title.length < SPLIT_LENGTH) {
    return [title, undefined];
  }

  // If the title is one long word, we have to keep it as one line.
  const words = title.split(' ');
  if (words.length === 1) {
    return [title, undefined];
  }

  // Iterate through each word until we find the first one that's > half the length.
  let acc = words[0].length;
  for (let i = 1; i < words.length; i++) {
    acc += words[i].length + 1; // Include space in accumulator
    if (acc > title.length / 2) {
      return [words.slice(0, i).join(' '), words.slice(i).join(' ')];
    }
  }

  // Should never reach this, just here to make Typescript happy
  return [title, undefined];
};

interface Props {
  title: ReactNode;
  small?: boolean;
  bannerImg?: string;
  bannerAlt?: string;
}

const PuzzleTitle: FC<Props> = ({ title, small, bannerImg, bannerAlt }) => {
  return (
    <>
      <h1 className={cx('font-title text-center w-full', { small })}>
        {title}
      </h1>

      {bannerImg && <img className="banner" src={bannerImg} alt={bannerAlt} />}

      <style jsx>{`
        h1 {
          max-width: 700px;
          color: var(--white);
          text-shadow: 0px 0px 12px black;
          margin: 1rem 0 2rem;
          filter: drop-shadow(2px 2px 0 rgba(0, 0, 0, 0.25));
        }

        h1.small {
          font-size: min(80px, 6vh) !important;
          margin-bottom: 1rem;
        }

        .banner {
          margin-bottom: 40px;
          width: 160px;
          max-width: 20%;
        }

        .banner {
          margin-top: -80px;
        }

        @media (max-width: 600px) {
          .banner {
            margin-top: -40px;
          }
        }

        @media print {
          h1 {
            color: black;
            font-size: 40px !important;
            text-shadow: none;
            filter: none !important;
            margin: 0;
          }
        }
      `}</style>
    </>
  );
};

export default PuzzleTitle;
