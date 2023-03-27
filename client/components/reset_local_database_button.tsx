import React, { FC, useCallback, useContext, useState } from 'react';
import cx from 'classnames';
import { XCircleIcon } from '@heroicons/react/outline';

import { clientFetch } from 'utils/fetch';
import { useRouter } from 'utils/router';
import { useWorker } from 'utils/worker';

import HuntInfoContext from 'components/context';
import InfoIcon from 'components/info_icon';
import Modal from 'components/modal';
import WebsocketNotice from 'components/websocket_notice';

/**
 * Buttons for resetting the pyodide database. Used only when the webworker is
 * enabled (eg for the static site).
 */
const ResetLocalDatabaseButton: FC = () => {
  const router = useRouter();
  const { ready, readyPromise } = useWorker();
  const { huntInfo } = useContext(HuntInfoContext);
  const [modalOpen, setModalOpen] = useState(false);

  const reset = useCallback(() => {
    const func = async () => {
      await readyPromise;
      clientFetch(router, '/reset_local_database', { method: 'POST' });
      setModalOpen(false);
    };
    func();
  }, [router, readyPromise]);

  if (!process.env.useWorker) {
    return null;
  }

  return (
    <>
      <button
        onClick={() => void setModalOpen(true)}
        className="font-bold ui-button mx-2"
      >
        Reset Progress
      </button>

      <Modal
        XButton={XCircleIcon}
        onRequestClose={() => void setModalOpen(false)}
        isOpen={modalOpen}
        className="story-modal"
        contentLabel="Reset Hunt progress"
        shouldCloseOnEsc
      >
        <div className="p-8 pt-16">
          <WebsocketNotice readyState={ready} />
          <InfoIcon>
            This will reset all Hunt progress, including local progress on all
            interactive puzzles. Continue?
          </InfoIcon>

          <div className="mt-4 flex flex-wrap justify-center gap-2">
            <button
              className="font-bold border story-button"
              disabled={!ready}
              onClick={reset}
            >
              Reset all progress
            </button>
          </div>
        </div>
      </Modal>
      <style jsx>{`
        button {
          color: var(--link);
        }

        :global(.story-button) {
          border-color: var(--link) !important;
          padding: 4px;
        }

        :global(.story-modal .x-button) {
          color: var(--link) !important;
          top: 0 !important;
          right: 0 !important;
        }

        button:not(:disabled):hover {
          text-decoration: underline;
          text-underline-offset: 4px;
        }
      `}</style>
    </>
  );
};
export default ResetLocalDatabaseButton;
