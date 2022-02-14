import React, { FC, useRef } from 'react';

import CopyToClipboard from 'components/copy';
import Puzzle, { PuzzleData, getPuzzleProps } from 'components/puzzle';

const SLUG = '[[INSERT SLUG]]';

const PuzzlePage: FC<{ puzzleData: PuzzleData }> = ({ puzzleData }) => {
  const ref = useRef<HTMLDivElement>(null);
  return (
    <Puzzle puzzleData={puzzleData}>
      <div ref={ref}>[[INSERT PUZZLE CONTENT]]</div>

      {/* TODO: By default this adds a copy-to-clipboard for the entire puzzle
       * content. You may wish to copy a smaller portion, just pass in "text",
       * or omit it entirely. */}
      <CopyToClipboard textRef={ref} />

      {/* TODO: uncomment if you wish to include your own styles.
      <style jsx>{`
        .example {
          color: var(--dark);
        }
      `}</style>
        */}
    </Puzzle>
  );
};

export default PuzzlePage;

export const getServerSideProps = getPuzzleProps(SLUG);
