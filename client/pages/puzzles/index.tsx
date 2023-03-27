import React from 'react';

import Custom404 from 'pages/404';
import Section from 'components/section';
import Title from 'components/title';
import PuzzlesList, { getPuzzlesListProps } from 'components/puzzles_list';
import { RoundProps } from 'components/puzzles_map';
import PuzzleApiComment from 'components/puzzle_api_comment';

const PuzzlesPage = ({ puzzles, rounds }: RoundProps) => {
  if (!Object.keys(puzzles).length) {
    return <Custom404 />;
  }

  return (
    <>
      <PuzzleApiComment />
      <Section title="All Puzzles">
        <PuzzlesList puzzles={puzzles} rounds={rounds} />
      </Section>
    </>
  );
};

export default PuzzlesPage;
export const getServerSideProps = getPuzzlesListProps;
