import React, {
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import Modal from 'react-modal';
import css from 'styled-jsx/css';
import cx from 'classnames';

import HuntInfoContext, { Story } from 'components/context';
import LinkIfStatic from 'components/link';
import { useLocalStorage } from 'utils/storage';
import { useEventWebSocket } from 'utils/fetch';

export const notifsKey = 'notifications';

const useLocalStorageCreator = ({ props }) =>
  useLocalStorage<string[]>({ ...props });

export const addSeenNotifs = (
  notifs: ReturnType<typeof useLocalStorageCreator>,
  seenNotifs: Story[]
) => {
  const _notifs = notifs.get();
  const _notifsSet = new Set(_notifs);
  const _seenNotifs = [
    ..._notifs,
    ...seenNotifs
      .map(({ slug }) => slug)
      .filter((slug) => !_notifsSet.has(slug)),
  ];
  notifs.set(_seenNotifs);
};

export const getUrl = (story: Story) => story.url;

export const getCurrentStorycards = (storyUnlocks, notif = true) => {
  const _notifs: Story[] = [];
  for (const unlock of storyUnlocks) {
    if (getUrl(unlock) && (!notif || (unlock.modal && unlock.deep > 0))) {
      _notifs.push(unlock);
    }
  }
  return _notifs;
};

/**
 * Component for rendering story cards that appear when certain milestones are
 * met in the hunt. Story cards can have text or images.
 * Include this in any page that wants them to appear.
 *
 * Notifications that are "seen" are saved in localStorage, so they don't
 * appear the next time a user opens the page.
 */
const StoryNotifications = ({ onlyFinished = false }) => {
  const { huntInfo, userInfo } = useContext(HuntInfoContext);
  const [allCurrentNotifs, setAllCurrentNotifs] = useState<Story[]>(
    huntInfo.storyUnlocks
  );
  const [hasFinished, setHasFinished] = useState<boolean>(
    userInfo?.teamInfo?.stage === 'finished'
  );

  const submissionHandler = useCallback((response) => {
    if (response?.data?.hasFinished) {
      // storycard pop-up after 5 seconds
      setTimeout(() => {
        if (response?.data?.storycards) {
          setAllCurrentNotifs(response.data.storycards);
        }
        setHasFinished(true);
      }, 5000);
    }
  }, []);
  useEventWebSocket({
    onJson: submissionHandler,
    key: 'submission',
  });

  let noNotifs = false;
  if (!huntInfo || !userInfo?.teamInfo) {
    // story notifications post-hunt are weird for logged out teams and lead to
    // unpredictable behavior when swapping to logged in teams.
    noNotifs = true;
  }
  if (onlyFinished && !hasFinished) {
    noNotifs = true;
  }

  // Only show notifications for story cards deep > 0 and without puzzles.
  const currentNotifs = useMemo(
    () => getCurrentStorycards(allCurrentNotifs),
    [allCurrentNotifs]
  );

  const notifs = useLocalStorage<string[]>(notifsKey, []);
  const [previousNotifs, setPreviousNotifs] = useState<string[]>();
  useEffect(() => {
    setPreviousNotifs(notifs.get());
  }, []);

  // Show up to two latest story cards that have not been seen already.
  const unseenNotifs = useMemo(() => {
    if (previousNotifs === undefined) return undefined;
    const previousNotifsSet = new Set(previousNotifs);
    return currentNotifs.filter((story) => !previousNotifsSet.has(story.slug));
  }, [currentNotifs, previousNotifs]);

  const newNotifications = useMemo(() => {
    const _newNotifications: Story[] = [];
    if (unseenNotifs?.length) {
      const lastUnseenNotif = unseenNotifs[unseenNotifs.length - 1];
      _newNotifications.push(lastUnseenNotif);
    }
    return _newNotifications;
  }, [unseenNotifs, hasFinished]);

  const [notificationModalOpen, setNotificationModalOpen] =
    useState<boolean>(false);
  useEffect(() => {
    if (!noNotifs) {
      if (newNotifications.length) {
        setNotificationModalOpen(true);
        addSeenNotifs(notifs, currentNotifs);
      }
    }
  }, [noNotifs, newNotifications, currentNotifs]);

  const { className, styles: modalStyles } = css.resolve`
    .modal {
      max-height: 90vh;
      overflow-x: none;
      overflow-y: auto;
      min-height: 50vh;
      min-width: 600px;
    }

    @media (max-width: 600px) {
      .modal {
        max-height: 100%;
        min-width: 100%;
      }
    }
  `;

  if (noNotifs || !currentNotifs) {
    return <></>;
  }

  return (
    <>
      {newNotifications.length > 0 && (
        <Modal
          style={{
            overlay: {
              backgroundColor: 'var(--dark-translucent)',
              zIndex: 1000, // Show over navbar
            },
          }}
          className={cx('modal abs-center', className)}
          isOpen={notificationModalOpen}
          onRequestClose={() => void setNotificationModalOpen(false)}
        >
          <input
            type="button"
            className="x-button"
            onClick={() => void setNotificationModalOpen(false)}
            value="✖"
            aria-label="Close"
          />

          {newNotifications.map((story) => {
            const storycard = (
              <img
                className="centerimg"
                key={story.slug}
                alt={story.text}
                src={getUrl(story)}
              />
            );

            return hasFinished ? (
              <LinkIfStatic href="/victory">{storycard}</LinkIfStatic>
            ) : story.puzzleSlug ? (
              <LinkIfStatic href={`/puzzles/${story.puzzleSlug}`}>
                {storycard}
              </LinkIfStatic>
            ) : (
              <>{storycard}</>
            );
          })}

          <style jsx>{`
            img {
              width: 600px;
              max-width: 90%;
            }

            input.x-button {
              background: rgba(0, 0, 0, 0.2);
              border: none;
              border-radius: 50%;
              color: var(--white);
              padding: 20px;
              position: sticky;
              float: right;
              top: 0;
              z-index: 100; /* Always show higher than content */
            }

            input.x-button:hover {
              background-color: rgba(0, 0, 0, 0.4);
            }

            :global(.dark) input.x-button {
              background: rgba(255, 255, 255, 0.2);
            }

            :global(.dark) input.x-button:hover {
              background-color: rgba(255, 255, 255, 0.4);
            }
          `}</style>
        </Modal>
      )}
      {modalStyles}
    </>
  );
};

export default StoryNotifications;
