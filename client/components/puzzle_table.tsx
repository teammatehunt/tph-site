import React, { Fragment, FunctionComponent } from 'react';
import { PuzzleData } from 'components/puzzle_image';
import LinkIfStatic from 'components/link';

interface Props {
  name?: string;
  puzzles: PuzzleData[][];
  final?: boolean;
}

const PuzzleTable: FunctionComponent<Props> = ({ name, puzzles, final }) => {
  const isCols = puzzles.length > 1;
  const maxPuzzles = Math.max(...puzzles.map((round) => round.length));

  return (
    <div className="round">
      {!name ? null : (
        <div className="header">
          <div className="hr" />
          <h3>{name}</h3>
          <div className="hr" />
        </div>
      )}
      <div className={`round-puzzles ${isCols ? 'dense' : ''}`}>
        {puzzles.map((round, i) => (
          <React.Fragment key={i}>
            {i ? <hr key={i} className="separator" /> : null}
            {round.map((puzzleData, j) => (
              <div
                key={puzzleData.slug}
                className={`puzzle ${
                  isCols ? `col-${i}` : final ? 'final' : 'nocol'
                } ${puzzleData.isMeta ? 'meta' : ''}`}
              >
                <div className="name">
                  <LinkIfStatic
                    href={puzzleData.url || `/puzzles/${puzzleData.slug}`}
                  >
                    {puzzleData.name}
                  </LinkIfStatic>
                </div>
                <div className="answer">{puzzleData.answer}</div>
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

        .round {
          width: 100%;
        }

        .header {
          display: flex;
          width: 100%;
          align-items: center;
        }

        .hr {
          width: 100%;
          border-top-style: solid;
          border-top-width: 1px;
          border-top-color: var(--secondary);
        }

        hr.separator {
          border-color: var(--secondary);
          width: 50%;
        }

        h3 {
          white-space: nowrap;
          margin-inline: 1ex;
          font-style: italic;
          font-weight: 500;
        }

        .round-puzzles {
          display: grid;
          width: 100%;
          grid-template-columns: 1fr;
          column-gap: 8ch;
          row-gap: 0.5em;
        }

        .round-puzzles.dense {
          grid-auto-flow: dense;
        }

        .puzzle {
          display: flex;
          column-gap: 2ch;
          align-items: center;
        }

        .puzzle > * {
          flex: 1;
        }

        .meta {
          flex-direction: column;
          text-align: center;
          margin: 24px 0;
        }

        .name {
          color: var(--primary);
        }

        .meta > .name {
          font-family: var(--sc-font);
          font-size: 24px;
          font-weight: bold;
          color: var(--secondary);
        }

        .answer {
          font-family: monospace;
        }

        @media (min-width: 801px) {
          .round-puzzles {
            grid-template-columns: 1fr 1fr;
          }

          .separator {
            display: none;
          }

          .col-0 {
            grid-column: 1;
          }

          .col-1 {
            grid-column: 2;
          }

          .nocol.meta {
            grid-column: 1;
          }

          .nocol.meta + .nocol.meta {
            grid-column: auto;
          }

          .final.meta {
            grid-column: span 2;
          }

          .col-0.meta,
          .col-1.meta {
            grid-row: ${maxPuzzles};
          }
        }
      `}</style>
    </div>
  );
};

export default PuzzleTable;
