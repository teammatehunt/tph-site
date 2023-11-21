import React, { useRef } from 'react';
import Head from 'next/head';

import Custom404 from 'pages/404';
import PuzzleMap, { getPuzzlesMapProps } from 'components/puzzles_map';
import PuzzleList from 'components/puzzles_list';
import { generateGetStaticPaths } from 'utils/static';

const Round = ({ puzzles, rounds, roundSlug }) => {
  if (!puzzles || !rounds?.[roundSlug]) {
    return <Custom404 />;
  }

  return (
    <>
      <Head>
        <title>{rounds[roundSlug].name}</title>
        {rounds[roundSlug].favicon && (
          <link
            key="favicon"
            rel="shortcut icon"
            href={rounds[roundSlug].favicon}
            type="image/vnd.microsoft.icon"
          />
        )}
      </Head>

      <PuzzleMap roundData={rounds[roundSlug]} puzzles={puzzles} />
      <PuzzleList puzzles={puzzles} rounds={rounds} />

      <style global jsx>{`
        .puzzles-map + .puzzle-list {
          background: white;
        }
      `}</style>
    </>
  );
};

export default Round;
export const getServerSideProps = async (context) => {
  const { res, params } = context;
  const { slug } = params || {};
  return await getPuzzlesMapProps(slug, true /* redirect */)(context);
};

// supposing round pages for mypuzzlehunt2.com do not exist at /round/{slug}
export const getStaticPathsInStaticExport = import.meta.url.includes(
  'mypuzzlehunt2.com'
)
  ? async () => ({
      paths: [],
      fallback: false,
    })
  : generateGetStaticPaths(import.meta.url);
