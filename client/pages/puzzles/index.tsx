import React, { FunctionComponent, useContext } from 'react';
import Head from 'next/head';
import dynamic from 'next/dynamic';

import Custom404 from 'pages/404';
import Section from 'components/section';
import PuzzlesList, {
  getPuzzlesListProps,
  Props as PuzzlesListProps,
} from 'components/puzzles_list';
import banner from 'assets/public/logo.png';

const PuzzlesPage = ({ puzzles }: PuzzlesListProps) => {
  return (
    <div>
      <Head>
        <title>List of Puzzles</title>
      </Head>

      <Section>
        {Object.keys(puzzles).length ? (
          <PuzzlesList puzzles={puzzles} />
        ) : (
          <Custom404 />
        )}
      </Section>
    </div>
  );
};

export default PuzzlesPage;
export const getServerSideProps = getPuzzlesListProps;
