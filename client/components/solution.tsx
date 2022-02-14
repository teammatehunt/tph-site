import React, { FunctionComponent, ReactFragment, useContext } from 'react';
import Head from 'next/head';
import cx from 'classnames';

import PuzzleTitle from 'components/puzzle_title';
import InfoIcon from 'components/info_icon';
import LinkIfStatic from 'components/link';
import Section from 'components/section';

interface PuzzleData {
  title: string;
  slug: string;
  answer: string;
  maxWidth?: boolean;
  authors?: ReactFragment;
  url?: string;
  round?: string;
  smallTitle?: boolean;
}

/**
 * Wrapper component for all solutions, providing some common formatting.
 */
const Solution: FunctionComponent<PuzzleData> = ({
  title,
  slug,
  answer,
  authors,
  round,
  maxWidth = true,
  url = undefined,
  smallTitle = false,
  children,
}) => {
  return (
    <>
      <Head>
        <meta name="robots" content="noindex" />
        <title>{title} - Solution</title>
      </Head>

      <div className="title flex-center-vert">
        <PuzzleTitle title={title} small={smallTitle} />
      </div>
      <Section className={cx({ maxWidth })}>
        <div className="center">
          {authors && <h3>{authors}</h3>}
          <h3>
            Answer: <span className="spoiler monospace">{answer}</span>
          </h3>
          <div className="link">
            <LinkIfStatic href={`/stats/${slug}`}>View Stats</LinkIfStatic>
            <LinkIfStatic href={url || `/puzzles/${slug}`}>
              Back to Puzzle
            </LinkIfStatic>
          </div>
        </div>

        {children}
      </Section>

      <style jsx>{`
        :global(section.maxWidth) {
          max-width: 900px;
        }

        .title {
          flex-direction: column;
        }

        .link {
          display: flex;
          flex-direction: column;
          margin: 20px 0 40px;
        }
      `}</style>
    </>
  );
};

/** Common styling for an intermediate clue phrase */
export const Clue: FunctionComponent<{}> = ({ children }) => (
  <span className="monospace">{children}</span>
);

/** Common styling for the answer, in monospace. */
export const Answerize: FunctionComponent<{}> = ({ children }) => (
  <strong className="monospace">
    {children}

    <style jsx>{`
      .monospace {
        font-size: 16px;
      }
    `}</style>
  </strong>
);

export default Solution;
