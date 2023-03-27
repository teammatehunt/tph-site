import React, { Fragment, FunctionComponent } from 'react';
import cx from 'classnames';

import { PuzzleData } from 'components/puzzle_image';
import { RoundData } from 'components/puzzles_map';
import { LinkIfStatic } from 'components/link';

interface Props {
  roundSlug: string;
  roundData: RoundData;
  puzzles: PuzzleData[][];
}

const PuzzleTitle = ({ puzzleData }) => (
  <LinkIfStatic href={puzzleData.url || `/puzzles/${puzzleData.slug}`}>
    {puzzleData.name}
  </LinkIfStatic>
);

const NestedTitle = ({ puzzleData, ne }) => {
  // Based on Galactic's nesting implementation, which is N nested divs that each have a
  // left-border + padding. This makes long titles overrun correctly.
  // This needs to be driven by a variable which we do with recursion.
  // Is this a good idea? Uhhhhhh, IDK, ask me later, how else do you do a variable number
  // of nested divs.
  if (ne !== undefined && ne > 0) {
    return (
      <div className="border-dashed border-l-2 pl-5">
        <NestedTitle puzzleData={puzzleData} ne={ne - 1} />
      </div>
    );
  } else {
    return <PuzzleTitle puzzleData={puzzleData} />;
  }
};

const PuzzleTable: FunctionComponent<Props> = ({
  roundSlug,
  roundData,
  puzzles,
}) => {
  const isCols = puzzles.length > 1;
  const maxPuzzles = Math.max(...puzzles.map((round) => round.length));

  const roundName = roundData?.name ?? '??????';

  return (
    <div className="w-full">
      <div className="flex items-center w-full">
        <div className="hr w-full" />
        <h3
          className={cx({
            // For super long round names on mobile
            'prefer-nowrap': roundName.length < 30,
          })}
        >
          {roundData?.url ? (
            <a href={roundData.url}>{roundName}</a>
          ) : (
            // Not all rounds have a url
            roundName
          )}
        </h3>
        <div className="hr w-full" />
      </div>
      <div className="round-puzzles">
        {puzzles.map((round, i) => (
          <React.Fragment key={i}>
            {i ? (
              <hr key={`${roundSlug}-hr-${i}`} className="separator" />
            ) : null}
            {round.map((puzzleData, j) => (
              <div
                key={`${puzzleData.slug}-${roundSlug}-${j}`}
                className={cx(
                  'puzzle flex items-center grid grid-cols-3 gap-4'
                )}
              >
                <div
                  key={`${puzzleData.slug}-${roundSlug}-inner-${j}`}
                  className={cx('name primary col-span-2', {
                    'font-smallcaps font-bold': puzzleData.isMeta,
                  })}
                >
                  {puzzleData.ne !== undefined ? (
                    <NestedTitle
                      key={`${puzzleData.slug}-${roundSlug}-title0`}
                      puzzleData={puzzleData}
                      ne={puzzleData.ne}
                    />
                  ) : (
                    <PuzzleTitle
                      key={`${puzzleData.slug}-${roundSlug}-title1`}
                      puzzleData={puzzleData}
                    />
                  )}
                </div>
                <pre
                  className={cx('font-mono secondary', {
                    underline: puzzleData.answer === '',
                  })}
                >
                  {puzzleData.answer != undefined &&
                    (puzzleData.answer || <>&nbsp;</>)}
                </pre>
              </div>
            ))}
          </React.Fragment>
        ))}
      </div>
      <style jsx>{`
        .name :global(a) {
          color: inherit;
          text-decoration: inherit;
        }

        .name :global(a:hover) {
          text-decoration: underline;
        }

        .hr {
          border-top-style: solid;
          border-top-width: 1px;
          border-top-color: var(--secondary);
        }

        hr.separator {
          border-color: var(--secondary);
          width: 50%;
        }

        h3 {
          margin-inline: 1ex;
          font-style: italic;
          font-weight: 500;
        }
        h3.prefer-nowrap {
          white-space: nowrap;
        }

        .round-puzzles {
          width: 100%;
        }

        @media (min-width: 801px) {
          .separator {
            display: none;
          }

          h3 {
            /* No need to wrap on larger devices. */
            white-space: nowrap;
          }
        }
      `}</style>
    </div>
  );
};

export default PuzzleTable;
