import React, { FunctionComponent, useCallback, useContext } from 'react';

import HuntInfoContext from 'components/context';

interface Props {
  showSolved: boolean;
  setShowSolved: (showSolved: boolean) => void;
}

const ShowSolvedSwap: FunctionComponent<Props> = ({
  showSolved,
  setShowSolved,
}) => {
  const { userInfo, huntInfo } = useContext(HuntInfoContext);
  const loggedIn = !!userInfo?.teamInfo;
  const huntIsOver = huntInfo && new Date() > new Date(huntInfo.endTime);

  const swap = useCallback(
    (newShowSolved) => () => {
      setShowSolved(newShowSolved);
    },
    [setShowSolved]
  );

  // Don't render this server-side because localStorage doesn't exist.
  if (typeof window === 'undefined' || !huntIsOver || loggedIn) {
    return null;
  }

  return (
    <>
      <div className="flex items-center">
        <i>Show all as</i>:
        <button
          className="font-smallcaps"
          disabled={!showSolved}
          onClick={swap(false)}
        >
          Unsolved
        </button>
        <button
          className="font-smallcaps"
          disabled={showSolved}
          onClick={swap(true)}
        >
          Solved
        </button>
      </div>
      <style jsx>{`
        button {
          background: none;
          border: none;
          color: var(--primary);
          margin-left: 16px;
          z-index: 50;
          font-weight: bold;
        }

        button:disabled,
        button:hover {
          text-decoration: underline;
          text-underline-offset: 4px;
        }

        div {
          color: var(--primary);
          font-size: 16px;
          margin-bottom: 16px;
        }
      `}</style>
    </>
  );
};

export default ShowSolvedSwap;
