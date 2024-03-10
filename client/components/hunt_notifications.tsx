import React, {
  FC,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react';
import { Transition } from '@headlessui/react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import cx from 'classnames';
import { Howl } from 'howler';

import HuntInfoContext from 'components/context';
import Twemoji from 'components/twemoji';
import { getPuzzleSlug } from 'utils/fetch';
import { useEventWebSocket } from 'utils/fetch';

interface NotificationType {
  round: string;
  url: string;
  visible: boolean;
  message: string;
  title?: string;
  icon?: string;
}

/** Used to show solve or unlock notifications, with websocket support. */
const HuntNotifications: FC = () => {
  const { huntInfo, round } = useContext(HuntInfoContext);
  const notifTimers = useRef<(number | null)[]>([]);
  const timerPaused = useRef<boolean>(false);
  const audioStream = useRef<Howl[]>([]);
  const [notifs, setNotifs] = useState<NotificationType[]>([
    /* Uncomment to test */
    /*
    {
      round: 'intro',
      url: '/rounds/intro',
      visible: true,
      message: '🌌 A test puzzle was unlocked!',
    },
    {
      round: 'main',
      url: '/main',
      visible: true,
      message: '🌌 You unlocked some new story content!',
      title: 'Story update',
      icon: 'http://placekitten.com/400/250',
    },
     */
  ]);
  const hideNotification = (i: number) => () => {
    if (timerPaused.current) {
      // Just restart the timer
      notifTimers.current[i] = window.setTimeout(hideNotification(i), 10000);
      return;
    }
    setNotifs((notifs) => {
      const newNotifs = [...notifs];
      newNotifs[i] = { ...notifs[i], visible: false };
      return newNotifs;
    });
    notifTimers.current[i] = null;
  };
  const addNotification = useCallback((puzzle, data) => {
    let i;
    setNotifs((notifs) => {
      i = notifs.length;
      return [
        ...notifs,
        {
          round: puzzle.round,
          url: puzzle.url,
          visible: true,
          ...data,
        },
      ];
    });
    // Set a timeout to hide this notification
    notifTimers.current[i] = window.setTimeout(
      hideNotification(i),
      // Messages with titles are more important, show for 20s.
      data.title ? 20000 : 10000
    );
    if (!!data.sound && !document.hidden) {
      const stream = new Howl({
        src: data.sound,
        html5: true,
      });
      stream.play();
      audioStream.current.push(stream);
    }
  }, []);

  const pauseTimers = (pause: boolean) => {
    timerPaused.current = pause;
  };

  const checkUnlock = useCallback(
    ({ data }) => {
      const puzzle = data?.puzzle;
      if (!data || !puzzle) {
        return;
      }
      if (data.message) {
        addNotification(puzzle, {
          message: data.message,
          icon: data.icon,
          title: data.title,
        });
      }
    },
    [addNotification]
  );

  const checkCorrect = useCallback(
    ({ data }) => {
      const puzzle = data?.puzzle;
      if (!data || !data.guess?.isCorrect || !puzzle) {
        return;
      }
      if (data.message) {
        addNotification(puzzle, {
          message: data.message,
          icon: data.icon,
          title: data.title,
          sound: data.sound,
        });
      }
    },
    [addNotification]
  );

  const checkHint = useCallback(
    ({ data }) => {
      const puzzle = data?.puzzle;
      if (!data || !puzzle) {
        return;
      }
      addNotification(puzzle, {
        message: data.message,
        icon: data.icon,
        title: data.title,
      });
    },
    [addNotification]
  );

  // Clear timers on unmount
  useEffect(
    () => () => {
      notifTimers.current.forEach((timerId) => {
        if (timerId) clearTimeout(timerId);
      });
    },
    []
  );

  useEventWebSocket({ onJson: checkCorrect, key: 'submission' });
  useEventWebSocket({ onJson: checkUnlock, key: 'unlock' });
  useEventWebSocket({ onJson: checkHint, key: 'hint' });

  return (
    <>
      {notifs.length > 0 ? (
        <div
          className="notifs flex flex-col items-end space-y-2"
          onPointerEnter={() => pauseTimers(true)}
          onPointerLeave={() => pauseTimers(false)}
        >
          {notifs.map((notif, i) => (
            <a key={notif.url} className="w-full no-underline" href={notif.url}>
              <Notification
                visible={notif.visible}
                title={notif.title}
                icon={notif.icon}
              >
                <Twemoji options={{ className: 'emoji inline-block' }}>
                  {notif.message}
                </Twemoji>
              </Notification>
            </a>
          ))}
        </div>
      ) : null}

      <style jsx>{`
        .notifs {
          position: fixed;
          right: 24px;
          top: 48px;
          width: 360px;
          z-index: 1001; /* Show over modal */
        }

        :global(.ReactModal__Body--open) .notifs {
          /* Bump it down when a modal is open to leave room for X button */
          top: 92px;
        }
      `}</style>
    </>
  );
};

interface NotificationProps {
  visible?: boolean;
  title?: string;
  icon?: string;
}

const Notification: FC<NotificationProps> = ({
  visible = false,
  title = false,
  icon,
  children,
}) => {
  const [show, setShow] = useState(visible);
  return (
    <Transition
      appear
      show={show && visible}
      className="notif relative"
      enterFrom="opacity-0"
      enterTo="opacity-100"
      leaveFrom="opacity-100 max-h-64"
      leaveTo="opacity-0 max-h-0"
      aria-live="polite"
      role="alert"
    >
      <button
        className="absolute top-0 right-0 p-2"
        aria-label="Close"
        onClick={(e) => {
          setShow(false);
          e.preventDefault();
        }}
      >
        <XMarkIcon className="w-4 h-4" />
      </button>
      <div className="notif-bg" />
      <div className="p-4 flex flex-col">
        {icon && <img src={icon} alt="" />}
        {title && (
          <h5 className="mt-2 text-sm font-bold font-smallcaps">{title}</h5>
        )}
        <div className={cx('description', { primary: !title })}>{children}</div>
        {title && <span className="text-sm primary">View now &gt;</span>}
      </div>

      <style jsx>{`
        :global(.notif) {
          border: 1px solid rgba(255, 255, 255, 0.2);
          border-radius: 12px;
          box-shadow: 0px 4px 4px rgba(0, 0, 0, 0.125);
          box-sizing: border-box;
          overflow: hidden;
          transition: opacity 0.5s ease-in 0s, color 0s linear 0.5s,
            max-height 0.5s;
        }
        :global(.notif):hover {
          filter: brightness(1.1);
        }

        .notif-bg {
          background-color: var(--white);
          opacity: 0.85;
          position: absolute;
          top: 0;
          width: 100%;
          height: 100%;
          z-index: -1;
          transition: background-color 0s linear 0.5s;
        }
        .notif-bg.dark {
          background-color: rgba(0, 0, 0, 0.8) !important;
          backdrop-filter: blur(8px);
          border: 1px solid rgba(0, 0, 0, 0.1);
          border-radius: 0;
        }

        img {
          max-height: 250px;
        }

        :global(a) .description {
          color: var(--text);
        }
      `}</style>
    </Transition>
  );
};

export default HuntNotifications;
