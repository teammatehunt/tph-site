import React, { FC, useCallback } from 'react';

import HuntInfoContext from 'components/context';
import { clientFetch } from 'utils/fetch';
import { useRouter } from 'next/router';
import { useWorker } from 'utils/worker';

const ResetLocalDatabaseButton: FC = () => {
  const router = useRouter();
  const { ready, readyPromise } = useWorker();
  const reset = useCallback(() => {
    const func = async () => {
      await readyPromise;
      if (
        window.confirm(
          'This will reset local progress on all puzzles. Continue?'
        )
      ) {
        clientFetch(router, '/reset_local_database', { method: 'POST' });
      }
    };
    func();
  }, []);

  if (!process.env.useWorker) {
    return null;
  }

  return (
    <>
      <button className={ready ? '' : 'invisible'} onClick={reset}>
        Reset progress?
      </button>
      <style jsx>{`
        .invisible {
          visibility: hidden;
        }

        button {
          background: none;
          border: none;
          color: var(--primary);
          z-index: 50;
          font-style: italic;
          font-size: 16px;
        }

        button:disabled,
        button:hover {
          text-decoration: underline;
          text-underline-offset: 4px;
        }
      `}</style>
    </>
  );
};

export default ResetLocalDatabaseButton;
