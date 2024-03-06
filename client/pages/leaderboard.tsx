import React, { useContext, useEffect, useRef, useState } from 'react';
import Link from 'next/link';

import Section from 'components/section';
import Title from 'components/title';
import { serverFetch } from 'utils/fetch';
import { formattedDateTime } from 'utils/timer';

interface Props {
  teams: Team[];
}

interface Team {
  team_name: string;
  slug: string;
  is_current: boolean;
  total_solves: number;
  last_solve_time?: string;
  metameta_solve_time?: string;
}

const isInViewport = (el: HTMLElement | null) => {
  if (typeof window === undefined || !el) {
    return false;
  }

  const rect = el.getBoundingClientRect();
  return (
    rect.top >= 0 &&
    rect.left >= 0 &&
    rect.right <= (window.innerWidth || document.documentElement.clientWidth) &&
    rect.bottom <= (window.innerHeight || document.documentElement.clientHeight)
  );
};

const Tent = ({ win, children }) => (
  <>
    {win && '🎪🎪 '}
    {children}
    {win && ' 🎪🎪'}
  </>
);

const Leaderboard = ({ teams }) => {
  const currentTeamRef = useRef<HTMLTableRowElement>(null);
  const [showScrollPointer, setShowScrollPointer] = useState<boolean>(false);

  useEffect(() => {
    if (currentTeamRef.current) {
      setShowScrollPointer(!isInViewport(currentTeamRef.current));
    }
  }, []);

  const scrollToCurrentPlace = () => {
    currentTeamRef.current!.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <>
      <Title title="Guests" subline="Come One, Come All!" />
      <Section>
        <div className="section">
          {showScrollPointer && (
            <div className="center">
              <button onClick={scrollToCurrentPlace}>Jump to team</button>
            </div>
          )}

          <table className="center">
            <thead>
              <tr>
                <th className="small-caps">Rank</th>
                <th className="small-caps">Team</th>
                <th className="small-caps">Solves</th>
                <th className="small-caps">Last Solve Time</th>
              </tr>
            </thead>
            <tbody>
              {teams.map((team: Team, i) => (
                <tr
                  key={team.team_name}
                  className={team.is_current ? 'current' : undefined}
                  ref={team.is_current ? currentTeamRef : null}
                >
                  <td className="text-bold">
                    {team.is_current && <div className="finger">&#9758;</div>}
                    {i + 1}
                  </td>
                  <td>
                    <Tent win={!!team.metameta_solve_time}>
                      <Link href="/team/[slug]" as={`/team/${team.slug}`}>
                        {team.team_name}
                      </Link>
                    </Tent>
                  </td>
                  <td>{team.total_solves}</td>
                  <td className="solve-time">
                    {formattedDateTime(team.metameta_solve_time, {
                      month: 'numeric',
                      year: '2-digit',
                      second: 'numeric',
                    }) ||
                      formattedDateTime(team.last_solve_time, {
                        month: 'numeric',
                        year: '2-digit',
                        second: 'numeric',
                      }) ||
                      '--'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <style jsx>{`
        .section {
          position: relative;
        }

        table {
          width: 100%;
        }

        th {
          border-bottom: 1px solid var(--secondary);
          color: var(--primary);
          padding-bottom: 8px;
          font-size: 20px;
          font-weight: 800;
        }

        tr {
          border-bottom: 1px solid var(--black);
        }

        td {
          padding: 8px 20px;
          font-size: 16px;
          word-break: break-all;
        }

        thead th:nth-child(1) {
          width: 10%;
          min-width: 3ch;
        }

        thead th:nth-child(3) {
          width: 10%;
        }

        thead th:nth-child(4) {
          width: 20%;
        }

        thead th:nth-child(5) {
          width: 10%;
        }

        .current {
          background: var(--background-dark);
        }

        .current td:first-child,
        .current a {
          color: var(--secondary);
        }

        .finger {
          margin: 6px calc(10% - 48px) 0 -40px;
          float: left;
        }

        .solve-time {
          word-break: keep-all;
        }

        @media (max-width: 550px) {
          thead th:nth-child(3),
          thead th:nth-child(4),
          thead th:nth-child(5) {
            width: 72px;
          }

          td {
            padding: 4px;
          }
        }
      `}</style>
    </>
  );
};

export default Leaderboard;

export const getServerSideProps = async (context) => {
  let props: Props;
  if (process.env.isStatic) {
    props = require('assets/json_responses/leaderboard.json');
  } else {
    props = await serverFetch<Props>(context, '/teams', {
      method: 'GET',
    });
  }
  return {
    props,
  };
};
