import React, { FC, useMemo } from 'react';

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
  title: string;
  small?: boolean;
  bannerImg?: string;
  bannerAlt?: string;
}

const PuzzleTitle: FC<Props> = ({ title, small, bannerImg, bannerAlt }) => {
  return (
    <>
      <div className={`puzzle-title ${small ? 'small' : ''}`}>{title}</div>

      {bannerImg && <img className="banner" src={bannerImg} alt={bannerAlt} />}

      <style jsx>{`
        div.puzzle-title {
          max-width: 700px;
          width: 100%;
          text-align: center;
          font-family: var(--title-font);
          font-size: ${small ? '56' : '70'}px;
          color: var(--primary);
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
      `}</style>
    </>
  );
};

export default PuzzleTitle;
