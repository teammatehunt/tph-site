import React, { FC, useContext, useMemo } from 'react';
import dynamic from 'next/dynamic';

import Custom404 from 'pages/404';
import { PuzzleData } from 'components/puzzle_image';
import PuzzleTable from 'components/puzzle_table';
import { serverFetch } from 'utils/fetch';

export interface Props {
  // Map from round name to list of puzzles.
  puzzles: Record<string, PuzzleData[]>;
}

const StoryNotifications = dynamic(
  () => import('components/story_notifications'),
  { ssr: false }
);

const PuzzlesList: FC<Props> = ({ puzzles }) => {
  return (
    <div>
      <StoryNotifications />
      {Object.entries(puzzles).map(([round, puzzles_in_round]) => (
        <PuzzleTable name={round} puzzles={[puzzles_in_round]} />
      ))}
    </div>
  );
};

export default PuzzlesList;
export const getPuzzlesListProps = async (context) => {
  let props: Props;
  if (process.env.isStatic) {
    try {
      props = require('assets/json_responses/puzzles.json');
    } catch {
      props = {} as Props;
    }
  } else {
    props = await serverFetch<Props>(context, '/puzzles');
  }
  return {
    props,
  };
};
