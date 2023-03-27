import React from 'react';

import Custom404 from 'pages/404';
import Puzzle, { getPuzzleProps } from 'components/puzzle';

const PlaceholderPuzzle = ({ puzzleData }) => {
  if (puzzleData?.error) {
    return <Custom404 />;
  }

  return (
    <Puzzle puzzleData={puzzleData}>
      <h4 className="center">
        <span className="secondary">Warning</span>: This puzzle has not been
        post-prodded.
      </h4>
      {puzzleData.puzzleUrl && (
        <p className="center">
          You can find a link to the puzzle{' '}
          <a href={puzzleData.puzzleUrl}>here</a>.
        </p>
      )}
    </Puzzle>
  );
};

export default PlaceholderPuzzle;

// This handles redirects internally
export const getServerSideProps = async (context) => {
  const { res, params } = context;
  const { slug } = params || {};
  return await getPuzzleProps(slug)(context);
};
