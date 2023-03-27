import React, { FC, useContext, useMemo } from 'react';

import Custom404 from 'pages/404';
import { PuzzleData } from 'components/puzzle_image';
import { RoundData, RoundProps } from 'components/puzzles_map';
import PuzzleTable from 'components/puzzle_table';
import Section from 'components/section';
import { serverFetch } from 'utils/fetch';

const PuzzlesList: FC<RoundProps> = ({ puzzles, rounds }) => {
  return (
    <Section className="puzzle-list rounded-md max-w-[1000px]">
      {Object.entries(puzzles).map(([roundSlug, puzzlesInRound]) => (
        <PuzzleTable
          key={roundSlug}
          roundSlug={roundSlug}
          roundData={rounds[roundSlug]}
          puzzles={[puzzlesInRound]}
        />
      ))}

      <style global jsx>{`
        section + .puzzle-list {
          margin-top: 60px;
        }
      `}</style>
    </Section>
  );
};

export default PuzzlesList;
export const getPuzzlesListProps = async (context) => {
  let props: RoundProps;
  if (process.env.isStatic) {
    try {
      props = require('assets/json_responses/puzzles.json');
    } catch {
      props = {} as RoundProps;
    }
  } else {
    props = await serverFetch<RoundProps>(context, '/puzzles');
  }
  return {
    props,
  };
};
