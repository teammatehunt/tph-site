import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import cx from 'classnames';
import parse from 'html-react-parser';
import { useRouter } from 'utils/router';
import { ReadyState } from 'react-use-websocket';

import { clientFetch, useEventWebSocket } from 'utils/fetch';
import { TimerBarFrom } from 'utils/timer';
import FlavorText from 'components/flavor_text';
import InfoIcon from 'components/info_icon';
import { Story } from 'components/storycard';
import { useBrowserUuid } from 'utils/uuid';

interface Props {
  className?: string;
  slug: string;
  story: Story;
}

interface Option {
  text?: string;
  state: string;
}

interface DialogueChoicesProps {
  options: Option[];
  singlePlayer: boolean;
  votes?: number[];
  myVote?: number;
  onChoice: (nextState: string, i: number) => void;
}

interface Response {
  state: string;
  sprite?: string;
  text: string;
  image?: string;
  transitions: Option[];
}

interface StatusResponse {
  bg: string;
  complete: boolean; // whether session has completed
  alt: string; // label for AI alt text
  sprite: string; // default sprite
}

/** Renders a single dialogue node and options. */
const DialogueChoices: React.FC<DialogueChoicesProps> = ({
  options,
  singlePlayer,
  votes,
  myVote,
  onChoice,
}) => {
  const [winner, totalVotes] = useMemo(() => {
    if (!votes) {
      return [null, null];
    }
    let currentOption: number | null = null;
    let currentVote = -1;
    let totalVotes = 0;
    for (let i = 0; i < options.length; i++) {
      totalVotes += votes[i] ?? 0;
      if ((votes[i] ?? 0) > currentVote) {
        currentOption = i;
        currentVote = votes[i] ?? 0;
      }
    }
    return [currentOption, totalVotes];
  }, [options, votes]);

  return (
    <>
      <div className="flex flex-col items-center space-y-2">
        {options.map(
          ({ state: nextState, text: optionText }, i) =>
            optionText ? (
              <div key={i} className="flex space-x-4 w-full">
                <button
                  className={cx(
                    'option flex-grow flex justify-between items-center no-underline',
                    {
                      winner: !singlePlayer && i === winner,
                    }
                  )}
                  tabIndex={0}
                  onClick={() => onChoice(nextState, i)}
                >
                  {!singlePlayer && (
                    <>
                      <div
                        className="absolute bar transition-transform"
                        style={{
                          transformOrigin: 'left',
                          transform: `scaleX(${
                            (votes?.[i] ?? 0) / (totalVotes || 1)
                          })`,
                        }}
                      />
                      <div
                        className={cx('radio shrink-0', {
                          checked: myVote === i,
                        })}
                      />
                    </>
                  )}
                  <div className="mx-2">{optionText}</div>
                  {!singlePlayer && (
                    <div className="votes">{votes?.[i] ?? 0}</div>
                  )}
                </button>
              </div>
            ) : null // Don't show if there is no text
        )}
      </div>

      <style jsx>{`
        .option {
          border: 1px solid var(--white);
          color: white !important;
          border-radius: 4px;
          position: relative;
          padding: 4px 8px;
          text-align: left;
          width: 100%;
        }
        .option:hover {
          color: var(--primary) !important;
        }

        .option.winner {
          border-color: var(--primary);
        }
        .option.winner .votes {
          color: var(--primary);
        }

        .bar {
          background: rgba(255, 255, 255, 0.2);
          height: 100%;
          width: 100%;
          margin-left: -8px;
          pointer-events: none;
        }

        .radio {
          border: 1px solid white;
          border-radius: 50%;
          width: 20px;
          height: 20px;
        }
        .radio.checked {
          background: var(--primary);
        }
      `}</style>
    </>
  );
};

interface DialogueChat {
  text: string;
  isTeam: boolean;
}

/**
 * Determines whether to join a lobby or use single-player mode.
 */
const DialogueRouter: React.FC<Props> = ({ className, story, slug }) => {
  const router = useRouter();
  const [isLoading, setLoading] = useState(true);
  const [sessionEnded, setSessionEnded] = useState(false);
  const [users, setUsers] = useState(0);
  const [ready, setReady] = useState(0);
  const [userReady, setUserReady] = useState(false);
  const [teamStarted, setTeamStarted] = useState(false);

  const [alt, setAlt] = useState('');
  const [bg, setBg] = useState('');
  const [defaultSprite, setDefaultSprite] = useState('');

  const [dialogueHistory, setDialogueHistory] = useState<DialogueChat[]>([]);
  const [dialogue, setDialogue] = useState<Response | null>(null);
  const [votes, setVotes] = useState<number[]>([]);
  const [myVote, setMyVote] = useState<number | undefined>();
  const [timeLeft, setTimeLeft] = useState<number | null>(null);
  const nextTimer = useRef<{ state: string; timer: number } | null>(null);
  const chatRef = useRef<HTMLDivElement>(null);

  const onSessionEnded = (finishUrl?: string) => {
    // FIXME: return to story or map page
  };

  const onNewDialogue = (dialogue, selectedText, newTimeLeft = undefined) => {
    setDialogue((oldDialogue) => {
      // Clear vote and update timer if dialogue changed
      if (oldDialogue?.text !== dialogue.text) {
        setMyVote(undefined);
        if (newTimeLeft != null) {
          setTimeLeft(Math.max(newTimeLeft, 1));
        }
      }
      return dialogue;
    });
    setDialogueHistory((oldHistory) => {
      if (oldHistory[oldHistory.length - 1]?.text === dialogue.text) {
        return oldHistory;
      }
      return [
        ...oldHistory,
        ...((selectedText
          ? [{ text: selectedText, isTeam: true }]
          : []) as DialogueChat[]),
        {
          text: dialogue.text,
          isTeam: false,
        },
      ];
    });
  };

  const uuid = useBrowserUuid();
  const { readyState, sendJsonMessage } = useEventWebSocket({
    onJson: ({ data }) => {
      if (data.session?.is_complete) {
        setSessionEnded(true);
        onSessionEnded(data.dialogue?.finish_url);
      } else {
        setUsers(data.session?.users ?? 1);
        setReady(data.session?.ready ?? 0);
        if (data.dialogue) {
          setTeamStarted(true);
          setVotes(data.votes ?? []);
          onNewDialogue(
            data.dialogue,
            data.selectedText,
            data.session?.time_left ?? 1
          );
        }
      }
    },
    key: slug,
    options: { uuid, storySlug: slug, connect: !isLoading && !sessionEnded },
  });

  const checkStatus = async () => {
    const response = await clientFetch<StatusResponse>(
      router,
      `/dialogue/${slug}/status`,
      { method: 'GET' }
    );
    setSessionEnded(response.complete);
    setAlt(response.alt);
    setBg(response.bg);
    setDefaultSprite(response.sprite);
    setLoading(false);
  };
  useEffect(() => void checkStatus(), []);

  useEffect(() => {
    // Scroll to bottom of history
    chatRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [dialogueHistory]);

  // Sets timer to increment to the next state
  // Even though there is one timer per client, the server is idempotent
  const onTimeout = useCallback(() => {
    if (dialogue?.state) {
      sendJsonMessage({ type: 'next', current: dialogue.state });
    }
  }, [dialogue?.state]);

  const onReadyOrStart = () => {
    if (userReady) {
      sendJsonMessage({ type: 'start' });
    } else {
      setUserReady(true);
      sendJsonMessage({ type: 'ready' });
    }
  };

  const onVote = (nextState: string, i: number) => {
    setMyVote(i);
    sendJsonMessage({ type: 'vote', state: i });
  };

  const singlePlayer = sessionEnded && !teamStarted;
  // Single-player endpoint just uses REST requests
  const getDialogueSinglePlayer = async (state?: string, i: number = 0) => {
    const response = await clientFetch<Response>(
      router,
      state ? `/dialogue/${slug}?state=${state}` : `/dialogue/${slug}`,
      { method: 'GET' }
    );
    onNewDialogue(response, dialogue?.transitions[i]?.text);
    if (
      response.transitions.length === 1 &&
      response.transitions[0].state === 'EXIT'
    ) {
      setTimeout(() => {
        onSessionEnded();
      }, 2000);
    }
  };
  const onStartSinglePlayer = () => {
    setUserReady(true);
    getDialogueSinglePlayer();
  };

  if (sessionEnded && teamStarted) {
    // End of team session, show a blank monitor. A timeout will close the window.
    return <div className="bg-black" />;
  }

  return (
    <>
      {dialogueHistory.length > 0 ? (
        <div className="h-full flex relative overflow-hidden">
          {dialogue?.image ? (
            <img className="mx-auto" src={dialogue.image} alt={dialogue.text} />
          ) : (
            <>
              <img
                className="sprite pointer-events-none"
                src={dialogue?.sprite || defaultSprite}
                alt={alt}
              />
              <div className="dialogue-container flex w-full h-full pb-8 relative">
                <div className="chat h-full flex flex-col items-center">
                  {dialogueHistory.map(({ text, isTeam }, i) => (
                    <p key={text} className={cx('bubble', { team: isTeam })}>
                      {parse(text)}
                    </p>
                  ))}
                  <p ref={chatRef} className="bubble invisible h-2" />
                </div>
              </div>
            </>
          )}
        </div>
      ) : (
        <img className="story mx-auto" src={story.imageUrl} alt={story.text} />
      )}

      {!isLoading && (singlePlayer || readyState === ReadyState.OPEN) ? (
        <div className="message-box bg-blur dark space-y-4">
          {dialogue ? (
            <>
              <DialogueChoices
                key={dialogue.state}
                options={dialogue.transitions}
                singlePlayer={singlePlayer}
                votes={votes}
                myVote={myVote}
                onChoice={singlePlayer ? getDialogueSinglePlayer : onVote}
              />
              {timeLeft != null && (
                <TimerBarFrom
                  key={`timer-${dialogue.state}`}
                  timeLeft={timeLeft}
                  onTimeout={onTimeout}
                  className="border-white h-2"
                  barClassName="bg-[#88ffff]"
                />
              )}
            </>
          ) : singlePlayer ? (
            <>
              <InfoIcon color="#fff">
                This team interaction has ended. You can still play through the
                dialogue in single-player mode.
              </InfoIcon>
              <button
                onClick={onStartSinglePlayer}
                className="border px-2 py-1"
              >
                Start
              </button>
            </>
          ) : (
            <>
              <InfoIcon center color="#fff">
                <div>
                  This interaction is best experienced with your entire team.
                  Start when your team is ready.
                </div>
                <div>{users - 1} of your teammates are here.</div>
              </InfoIcon>
              <button onClick={onReadyOrStart} className="border px-2 py-1">
                {userReady ? 'Start Interaction' : 'Ready to Start'}
              </button>
            </>
          )}
        </div>
      ) : (
        <p>Loading...</p>
      )}

      <style jsx>{`
        img.story {
          width: min(70vw, 70vh);
        }
        img.sprite {
          position: absolute;
          z-index: 1;
          left: 0;
          top: 50%;
          transform: translate(-10%, -50%);
          width: max(120px, 30vw);
          max-width: 400px;
        }
        .chat {
          padding-left: min(25vw, 500px);
          z-index: 1;
        }
        .chat .bubble {
          align-self: start;
          background: #eaeaea;
          border: 1px solid black;
          border-radius: 8px;
          color: black;
          padding: 4px 8px;
          max-width: 90%;
          text-align: left;
          text-shadow: none;
        }
        .chat .bubble.team {
          background: #0f766e;
          color: white;
          align-self: end;
        }

        .message-box {
          position: absolute;
          border: 1px solid var(--white);
          bottom: 24px;
          left: 50%;
          transform: translateX(-50%);
          max-width: 900px;
          padding: 1.4vh 1vw;
          font-size: min(2vw, 16px);
          min-height: 88px;
          width: 100%;
          z-index: 10;
        }

        @media (max-width: 550px) {
          img.sprite {
            transform: translate(-15%, -50%);
          }
          .chat .bubble {
            max-width: 100%;
            font-size: 12px;
          }
        }
      `}</style>

      <style jsx>{`
        .dialogue-container {
          background-image: ${bg ? `url(${bg})` : 'none'};
          background-size: cover;
          height: 100%;
          overflow-y: auto;
        }
      `}</style>
    </>
  );
};

export default DialogueRouter;
