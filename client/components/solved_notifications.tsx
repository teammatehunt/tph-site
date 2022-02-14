import React, { FunctionComponent, useCallback, useState } from 'react';
import dynamic from 'next/dynamic';

import { useEventWebSocket } from 'utils/fetch';
import Confetti from 'components/confetti';
import Twemoji from 'components/twemoji';
import { getPuzzleSlug } from 'utils/fetch';

/** Used to show a message when a puzzle is solved, with websocket support. */
const SolvedNotifications: FunctionComponent = () => {
  const [confettiId, setConfettiId] = useState<number>(0);
  const [notif, setNotif] = useState<[string?, string?]>();
  const [name, notifDimension] = notif ?? [];

  const checkCorrect = useCallback((response) => {
    if (response?.data?.guess?.isCorrect) {
      setConfettiId((id) => id + 1);
      if (response?.data?.puzzle?.slug !== getPuzzleSlug()) {
        setNotif([
          response?.data?.puzzle?.name,
          response?.data?.puzzle?.dimension,
        ]);
        setTimeout(() => {
          setNotif((notif) => {
            const [name] = notif ?? [];
            if (name === response?.data?.puzzle?.name) {
              return [name, undefined];
            }
            return notif;
          });
        }, 7000);
      }
    }
  }, []);

  useEventWebSocket({
    onJson: checkCorrect,
    key: 'submission',
  });

  return (
    <>
      {!confettiId ? null : <Confetti key={confettiId} />}
      <div
        className={`notif ${notifDimension ? 'active' : ''} ${
          notifDimension ?? ''
        }`}
      >
        <div className="notif-bg" />
        <div className="notif-text">
          {!name ? null : (
            <Twemoji>
              <span className="puzzle">{name}</span> was solved!
            </Twemoji>
          )}
        </div>
      </div>
      <style jsx>{`
        .notif {
          position: fixed;
          box-sizing: border-box;
          margin: 20px 40px;
          right: 0;
          top: 48px;
          max-width: max(0, calc(100% - 40px));
          width: 350px;
          opacity: 0;
          pointer-events: none;
          user-select: none;
          filter: brightness(125%);
          z-index: 1000;
          color: var(--yellow);
          transition: opacity 0.5s ease-in 0s, color 0s linear 0.5s;
        }

        .notif.active {
          opacity: 0.9;
          transition: opacity 0.5s ease-out 1s, color 0s linear 0s;
        }

        .notif-bg {
          position: absolute;
          border-radius: 10px;
          width: 100%;
          height: 100%;
          filter: contrast(75%);
          z-index: -1;
          transition: background-color 0s linear 0.5s;
        }

        .notif.active > .notif-bg {
          transition: background-color 0s linear 0s;
        }

        .notif-text {
          padding: 20px;
          font-size: 18px;
        }

        .puzzle {
          font-weight: bold;
        }
      `}</style>

      {/* need to keep colors synced with styles.css and layout.tsx */}
      <style jsx>{`
        .i {
          color: #fffcdf;
        }
        .i > .notif-bg {
          filter: contrast(75%) brightness(80%);
          background-color: var(--red);
          box-shadow: 0 0 10px var(--red);
        }
        .m > .notif-bg {
          background-color: #0f1e42;
          box-shadow: 0 0 10px #0f1e42;
        }
        .e > .notif-bg {
          background-color: #0c2f36;
          box-shadow: 0 0 10px #0c2f36;
        }
        .z > .notif-bg {
          background-color: #3d1832;
          box-shadow: 0 0 10px #3d1832;
        }
      `}</style>
    </>
  );
};

export default SolvedNotifications;
