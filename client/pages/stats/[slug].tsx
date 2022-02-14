// @ts-nocheck
// To make tables sorttable, we need to attach custom properties and call
// external functions, both of which make TypeScript unhappy.
import React, { useContext, useState, useEffect, useRef } from 'react';
import Head from 'next/head';
import Link from 'next/link';

import Section from 'components/section';
import Title from 'components/title';
import LinkIfStatic from 'components/link';
import { FullTable } from 'components/table';
import Page404 from 'pages/404';

import { serverFetch } from 'utils/fetch';
import { formattedDateTime, displayTimeLeft, sortTime } from 'utils/timer';

interface SolverData {
  team: string;
  slug: string;
  is_current: boolean;
  unlock_time: string;
  solve_time: string;
  wrong_duration?: number;
  open_duration?: number;
  total_guesses: number;
}

interface StatsData {
  solvers?: SolverData[];
  solves: number;
  guesses: number;
  answers_tried: {
    wrong_answer: string;
    count: number;
  }[];
  wrong: string;
  puzzle_name: string;
  puzzle_answer: string;
}

const Stats = ({ statsData, slug }) => {
  // invalid slugs make it to this function instead of getting redirected to
  // 404 page, eventually causing a server error. I am so done with debugging
  // Caddy redirects so screw it just copy-paste the 404 code.
  if (!statsData.solvers) {
    return <Page404 />;
  }

  useEffect(() => {
    const func = async () => {
      // directly call the makeSortable function once it's all rendered.
      const tables = document.getElementsByClassName('sorttable');
      while (!window.sorttable)
        await new Promise((resolve) => setTimeout(resolve, 100));
      for (let i = 0; i < tables.length; i++) {
        window.sorttable.makeSortable(tables[i]);
      }
    };
    func();
  }, []);

  return (
    <Section>
      <Title title={`Stats: ${statsData.puzzle_name}`} />
      <Head>
        <meta name="robots" content="noindex" />
        <script src="/sorttable.js"></script>
      </Head>
      <div className="center link">
        <LinkIfStatic href={`/puzzles/${slug}`}>Back to Puzzle</LinkIfStatic>
      </div>
      <h3>
        Total solves: <strong>{statsData.solves}</strong>
      </h3>
      <h3>
        Total guesses: <strong>{statsData.guesses}</strong>
      </h3>
      <FullTable className="sorttable">
        <thead>
          <tr className="full">
            <th style={{ width: '34%' }}>Team</th>
            <th style={{ width: '12%' }}>Wrong guesses</th>
            <th style={{ width: '12%' }}>Unlock time</th>
            <th style={{ width: '15%' }}>Time to solve</th>
            <th style={{ width: '12%' }}>Solve time</th>
            <th style={{ width: '15%' }}>
              Time to solve after{' '}
              <span className="answer monospace">{statsData.wrong}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {statsData.solvers.map(
            (
              {
                team,
                slug,
                total_guesses,
                unlock_time,
                open_duration,
                solve_time,
                wrong_duration,
              },
              i
            ) => (
              <tr key={`solver-row-${i}`}>
                <td>
                  <Link href="/team/[slug]" as={`/team/${slug}`}>
                    <a>{team}</a>
                  </Link>
                </td>
                <td>{total_guesses}</td>
                <td sorttable_customkey={sortTime(unlock_time)}>
                  {formattedDateTime(unlock_time, {
                    year: null,
                    weekday: null,
                  })}
                </td>
                <td sorttable_customkey={open_duration}>
                  {open_duration &&
                    displayTimeLeft(open_duration, 1, {
                      showHours: true,
                      showDays: false,
                      verbose: true,
                      warningAt: 0,
                    })}
                </td>
                <td sorttable_customkey={sortTime(solve_time)}>
                  {formattedDateTime(solve_time, {
                    year: null,
                    weekday: null,
                  })}
                </td>
                <td sorttable_customkey={wrong_duration}>
                  {wrong_duration &&
                    displayTimeLeft(wrong_duration, 1, {
                      showHours: true,
                      showDays: false,
                      verbose: true,
                      warningAt: 0,
                    })}
                </td>
              </tr>
            )
          )}
        </tbody>
      </FullTable>
      <br />
      <br />
      <FullTable className="sorttable">
        <thead>
          <tr>
            <th style={{ width: '80%' }}>Answer</th>
            <th style={{ width: '20%' }}>Submission count</th>
          </tr>
        </thead>
        <tbody>
          <tr className="answer">
            <td className="monospace">
              <strong>{statsData.puzzle_answer}</strong>
            </td>
            <td>{statsData.solves}</td>
          </tr>
          {statsData.answers_tried.map((answer, i) => (
            <tr key={`answer-${i}`} className="answer">
              <td className="monospace">{answer.wrong_answer}</td>
              <td>{answer.count}</td>
            </tr>
          ))}
        </tbody>
      </FullTable>
      <style jsx>{`
        .full {
          width: 100%;
        }
        .link {
          margin: 20px 0 40px;
        }
        th {
          font-size: 24px;
          padding-bottom: 4px;
          padding-right: 4px;
          word-wrap: anywhere;
        }
        td {
          padding-top: 4px;
          padding-bottom: 4px;
          padding-right: 4px;
          word-wrap: anywhere;
        }
        th,
        tr {
          border-bottom: 1px dashed black;
        }
        .answer {
          font-size: 18px;
        }
      `}</style>
    </Section>
  );
};

export default Stats;

export const getServerSideProps = async (context) => {
  const { params } = context;
  const { slug } = params || {};
  let props: any;
  if (process.env.isStatic) {
    props = require(`assets/json_responses/stats/${slug}.json`);
  } else {
    props = {
      statsData: await serverFetch<StatsData>(context, `/stats/${slug}`),
      slug,
    };
  }

  return {
    props,
  };
};

/*
export const getStaticPaths = async () => {
  return require('assets/json_responses/puzzle_paths.json');
};
*/
