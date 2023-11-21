import React, {
  FC,
  RefObject,
  useContext,
  useMemo,
  useEffect,
  useRef,
  useState,
  useCallback,
} from 'react';
import parse from 'html-react-parser';
import { Router } from 'next/router';
import { useRouter } from 'utils/router';
import Head from 'next/head';
import Link from 'components/link';
import cx from 'classnames';
import dynamic from 'next/dynamic';
import useCookie from 'react-use-cookie';

import Accordion from 'components/accordion';
import CopyToClipboard, { CopyConfig } from 'components/copy';
import GuessBox, { Guess } from 'components/puzzle/guess_box';
import HuntInfoContext, { Errata } from 'components/context';
import InteractionForm, { Interaction } from 'components/interaction_form';
import PuzzleTitle from 'components/puzzle_title';
import Section from 'components/section';
import { Story } from 'components/storycard';
import { Countdown } from 'components/countdown';
import { DjangoFormErrors } from 'types';
import {
  clientFetch,
  CryptKeys,
  serverFetch,
  useEventWebSocket,
} from 'utils/fetch';
import Table from 'components/table';
import { formattedDateTime } from 'utils/timer';
import { LinkIfStatic } from 'components/link';
import { UnsupportedMessage } from 'components/unsupported';
import { useSessionUuid } from 'utils/uuid';
import WorkerLoadingIcon from 'components/worker_loading_icon';

const POSTHUNT_NEEDS_WORKER_PUZZLES: string[] = [];

const answerize = (s: string) => {
  return s ? s.toUpperCase().replace(/[^A-Z]/g, '') : '';
};

export interface RoundData {
  act: number;
  slug: string;
  name: string;
  url: string;
  wordmark?: string;
  header?: string;
  background?: string;
  favicon?: string;
  private?: any; // Custom puzzle-specific data.
}

export interface RateLimitData {
  shouldLimit: boolean;
  secondsToWait: number;
}

export interface CannedHint {
  keywords: string;
  content: string;
}

export interface PuzzleData {
  statusCode?: number;
  name: string;
  slug: string;
  url: string;
  isSolved?: boolean;
  guesses?: Guess[];
  solutionLinkVisible?: boolean;
  adminLinkVisible?: boolean;
  adminUrl?: string;
  rateLimit?: RateLimitData;
  canViewHints?: boolean;
  canAskForHints?: boolean;
  hintReason?: string;
  hintsUrl?: string;
  errata?: Errata[];
  cannedB64Encoded?: string;
  answerB64Encoded?: string;
  partialMessagesB64Encoded?: [string, string][];
  puzzleUrl?: string; // External url for testsolving only.
  round?: RoundData;
  storycard?: Story;
  interaction?: Interaction;
  private?: any; // Custom puzzle-specific data.
}

interface AnswerForm {
  answer?: string;
}

interface SolveResponse {
  form_errors?: DjangoFormErrors<AnswerForm>;
  guesses?: Guess[];
  ratelimit_data?: RateLimitData;
  interaction?: Interaction;
  private?: any; // Custom puzzle-specific data.
}

export interface PuzzleProps {
  titleHtml?: React.ReactFragment;
  nameOverride?: string;
  puzzleData: PuzzleData;
  copyData?: { ref: RefObject<HTMLElement>; config?: CopyConfig };
  showTitle?: boolean;
  smallTitle?: boolean;
  showSubmission?: boolean | string;
  maxWidth?: boolean;
  maxWidthPx?: number;
  dark?: boolean;
  bgUrl?: string;
  Input?: FC<React.HTMLProps<HTMLInputElement>>;
  localChecker?: string;
}

export interface PuzzleDataProps {
  puzzleData: PuzzleData;
}

interface LinkData {
  href: string;
  text: string;
  shallow?: boolean;
}

function getCountdown(secondsToWait, onFinish) {
  return (
    <Countdown
      seconds={secondsToWait}
      countdownFinishCallback={onFinish}
      showHours
    />
  );
}

export const RoundHeader: FC<{ round: RoundData }> = ({ round }) => (
  <div className="round-header flex items-center justify-center print:hidden">
    {round.header && (
      <img
        className="absolute w-full inset-x-0 top-0 pointer-events-none"
        src={round.header}
        alt={round.name}
      />
    )}
    <a className="md:w-1/3 w-2/3 z-[1]" href={round.url}>
      <img className="w-full" src={round.wordmark} alt="Back to round" />
    </a>
  </div>
);

/**
 * Wrapper component for all puzzles with logic for submissions, as well as
 * displaying past guesses.
 */
const Puzzle: FC<PuzzleProps> = ({
  titleHtml,
  puzzleData,
  nameOverride,
  copyData = undefined,
  showTitle = true,
  smallTitle = false,
  showSubmission = true,
  maxWidth = true,
  maxWidthPx = 900,
  Input = 'input',
  dark = false,
  bgUrl = undefined,
  localChecker = undefined,
  children,
}) => {
  const router = useRouter();
  const { userInfo, huntInfo } = useContext(HuntInfoContext);

  const copyButtonRef = useRef<HTMLButtonElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const uuid = useSessionUuid();
  const darkMode = dark;

  const [error, setError] = useState<any>('');
  const [guesses, setGuesses] = useState<Guess[]>(puzzleData.guesses ?? []);
  const [guessesVisible, setGuessesVisible] = useState<boolean>(true);
  const [isSolved, setSolved] = useState<boolean>(puzzleData.isSolved ?? false);

  const [isSubmitting, setSubmitting] = useState<boolean>(false);
  const [isInputDisabled, setInputDisabled] = useState<boolean>(false);

  const [secondsToWait, setSecondsToWait] = useState<number>(
    puzzleData.rateLimit?.secondsToWait ?? 0
  );
  const [isRateLimited, setRateLimited] = useState<boolean | undefined>(
    puzzleData.rateLimit?.shouldLimit
  );
  const [rateLimitError, setRateLimitError] = useState<any>('');
  const [errata, setErrata] = useState<Errata[]>(puzzleData.errata ?? []);
  const [cannedHints, setCannedHints] = useState<CannedHint[]>(
    puzzleData.cannedB64Encoded
      ? JSON.parse(atob(puzzleData.cannedB64Encoded))
      : []
  );
  const [storycard, setStorycard] = useState<Story | undefined>(
    puzzleData.storycard
  );
  const [interaction, setInteraction] = useState<Interaction | undefined>(
    puzzleData.interaction
  );

  const slug = puzzleData.slug;
  const huntIsOver = huntInfo && new Date() > new Date(huntInfo.endTime);
  const loggedIn = !!userInfo?.teamInfo;
  const reallyShowSubmission =
    showSubmission === 'public' ? userInfo?.public : showSubmission;

  /* Websocket handler which syncs guesses, rate limits, etc. with the rest of
  /* the team. */
  const websocketHandler = useCallback((message = {}) => {
    if (message.data?.puzzle?.slug === puzzleData.slug) {
      const storycard = message.data?.storycard;
      if (storycard) {
        setStorycard(storycard);
        if (storycard.url) {
          // Navigate to url directly on solve
          // Hack: wait a second so they see the solve animation
          setTimeout(() => router.push(storycard.url), 1000);
        }
      }
      if (message.data?.guess) {
        setGuesses((guesses) => {
          // Make sure that we only update if the guess isn't already in the list.
          if (
            guesses.some((guess) => guess.guess === message.data.guess.guess)
          ) {
            return guesses;
          }

          // Otherwise, prepend to the list.
          return [message.data.guess, ...guesses];
        });
        if (message.data.guess.isCorrect) setSolved(true);
      }
      if (message.data?.rateLimit) {
        setSecondsToWait(message.data.rateLimit.secondsToWait);
        setRateLimited(message.data.rateLimit.shouldLimit);
      }
    }
  }, []);
  useEventWebSocket({
    onJson: websocketHandler,
    key: 'submission',
  });

  useEffect(() => {
    setGuesses(puzzleData.guesses ?? []);
    setSolved(puzzleData.isSolved ?? false);
  }, [puzzleData.guesses, puzzleData.isSolved]);

  useEffect(() => {
    if (secondsToWait > 0) {
      const timer = getCountdown(
        secondsToWait,
        () => void setSecondsToWait(0) // reset on finish
      );
      const error = (
        <>
          <span>Your next guess will be available in:</span>{' '}
          <strong>{timer}</strong>
        </>
      );
      setRateLimitError(error);
    } else {
      setRateLimitError('');
      setRateLimited(false);
    }
  }, [secondsToWait]);

  const hintsUrl = puzzleData?.hintsUrl;

  /* Shows the hint, solution, and stats links if unlocked. */
  const getTopRightLinks = useMemo((): LinkData[] => {
    const topRightLinks: LinkData[] = [];
    if (hintsUrl) {
      topRightLinks.push({
        href: hintsUrl,
        text: 'Request a hint',
      });
    }
    if (puzzleData?.solutionLinkVisible) {
      topRightLinks.push({
        href: `/solutions/${slug}`,
        text: 'View solution',
      });
      topRightLinks.push({
        href: `/stats/${slug}`,
        text: 'View stats',
      });
    }
    if (storycard && storycard.url) {
      topRightLinks.push({
        href: storycard.url,
        text: 'View story',
      });
    }
    return topRightLinks;
  }, [guesses, puzzleData?.solutionLinkVisible, storycard, hintsUrl]);

  /* In static mode (or post-hunt) this is used to check answers against a
   * base64 encoded answer. */
  const onSubmitLocalChecker = (e) => {
    e.preventDefault();
    const data = new FormData(e.target);
    e.target.reset(); // Clear the form input
    const guess: string = answerize(data.get('answer') as string);
    if (!guess) {
      setError(
        'All puzzle answers will have at least one letter A through Z \
               (case does not matter).'
      );
      return;
    }
    for (const oldGuess of guesses) {
      if (guess === oldGuess.guess) {
        setError(`You\u2019ve already tried calling in the answer \
                 \u201c${guess}\u201d for this puzzle.`);
        return;
      }
    }
    setError(''); // clear previous errors
    if (isRateLimited) {
      setRateLimitError(
        "You've submitted too many guesses. Please wait before trying again."
      );
    } else {
      // TextEncoder needed for non-ASCII
      const guessB64Encoded = btoa(
        String.fromCharCode(...new TextEncoder().encode(guess))
      );
      const isCorrect = guessB64Encoded === puzzleData.answerB64Encoded;
      let newGuesses = [...guesses];
      let response = isCorrect ? 'Correct!' : 'Incorrect';
      if (puzzleData.partialMessagesB64Encoded) {
        for (let [
          partialGuessB64Encoded,
          partialResponseB64Encoded,
        ] of puzzleData?.partialMessagesB64Encoded) {
          if (guessB64Encoded === partialGuessB64Encoded)
            response = atob(partialResponseB64Encoded);
        }
      }
      newGuesses.unshift({
        timestamp: new Date().toString(),
        guess: guess,
        response: response,
        isCorrect: isCorrect,
      });
      setGuesses(newGuesses);
      if (isCorrect) {
        setSolved(true);
      }
    }
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    const data = new FormData(e.target);
    data.append('uuid', uuid);
    e.target.reset(); // Clear the form input

    setSubmitting(true);
    const response = await clientFetch<SolveResponse>(
      router,
      `/solve/${slug}`,
      {
        method: 'POST',
        body: data,
      }
    );
    setSubmitting(false);
    // Always set guesses left and isRateLimited.
    const rateLimitedBefore = isRateLimited;
    if (response.ratelimit_data) {
      setRateLimited(response.ratelimit_data.shouldLimit);
    }
    if (response.guesses) {
      // A successful guess happened.
      const newGuesses = response.guesses;
      setGuesses(newGuesses);
      if (!isSolved && newGuesses[0]?.isCorrect) {
        setSolved(true);
      }
    }
    if (response.ratelimit_data?.shouldLimit) {
      // We were already rate limited and tried to make a guess.
      // Do not update the error message, even if an error is defined, because
      // doing so overwrites the countdown.
    } else if (response.form_errors) {
      // We were not rate limited but our answer submit was bad for some reason.
      setError(response.form_errors.answer || response.form_errors.__all__!);
    } else {
      // wipe errors from previous guess
      setError('');
      setRateLimitError('');
    }
    if (response.ratelimit_data?.shouldLimit) {
      setSecondsToWait(response.ratelimit_data.secondsToWait);
    }
    if (response.interaction) {
      setInteraction(interaction);
    }
  };

  const displayedErrata = useMemo(
    () => (
      <div className="errata">
        {errata.map((err, i) => (
          <p className="error" key={`errata-${i}`}>
            <b>Erratum</b> on{' '}
            {formattedDateTime(err.time, {
              month: 'numeric',
              year: '2-digit',
              second: undefined,
            })}
            :{' '}
            {err.text.startsWith('Hint') ? (
              <>
                Hint: <span className="spoiler">{parse(err.text)}</span>
              </>
            ) : (
              parse(err.text)
            )}
          </p>
        ))}

        <style jsx>{`
          .errata {
            margin: 0 auto;
          }
        `}</style>
      </div>
    ),
    [errata]
  );

  const displayedCannedHints = useMemo(
    () => (
      <Accordion heading="Show canned hints">
        <p>Hints reveal on hover.</p>
        <Table>
          <thead>
            <tr>
              <th>Keywords</th>
              <th>Hint</th>
            </tr>
          </thead>
          <tbody>
            {cannedHints.map((hint, i) => (
              <tr key={`canned-${i}`}>
                <td className="spoiler">{hint.keywords}</td>
                <td className="spoiler">{hint.content}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Accordion>
    ),
    [cannedHints]
  );

  const puzzleTitle = nameOverride ?? puzzleData.name;

  return (
    <div
      className={cx('puzzle container', {
        maxWidth,
        darkmode: darkMode,
      })}
    >
      <Head>
        {puzzleData.round?.favicon && (
          <link
            key="favicon"
            rel="shortcut icon"
            href={puzzleData.round.favicon}
            type="image/vnd.microsoft.icon"
          />
        )}
        {showTitle && <title>{puzzleTitle}</title>}
      </Head>
      <div className="top-right flex flex-wrap justify-end space-x-2 print:hidden">
        {getTopRightLinks.map(({ href, text, shallow = false }, i) => (
          <Link key={`topright-${i}`} href={href} shallow={shallow}>
            <a className="bg-navbar p-1.5 rounded-lg secondary">{text}</a>
          </Link>
        ))}
      </div>
      {puzzleData.round?.wordmark && <RoundHeader round={puzzleData.round} />}
      <div className="flex items-center justify-center">
        {titleHtml || <PuzzleTitle title={puzzleTitle} small={smallTitle} />}
      </div>
      {guessesVisible && (
        <div
          className={cx(
            'ui-wrapper mt-[0.6rem] mx-auto flex flex-col items-center justify-center'
          )}
        >
          {!isSolved && reallyShowSubmission && (
            <div className="guess-box flex flex-col justify-center text-center drop-shadow-md">
              <form
                onSubmit={
                  localChecker !== 'none' &&
                  (process.env.isArchive || (huntIsOver && !loggedIn))
                    ? onSubmitLocalChecker
                    : onSubmit
                }
              >
                <label className="flex items-center pb-2" htmlFor="answer">
                  <h4>
                    {userInfo?.public ? 'Check answer' : 'Submit a guess'}
                  </h4>
                </label>
                <div className="inputs flex relative justify-center w-full">
                  <Input
                    ref={inputRef}
                    className="font-mono grow shrink-0 basis-80 px-3 py-2"
                    name="answer"
                    id="answer"
                    disabled={isSubmitting}
                    type="text"
                  />
                  <input
                    className="ui-button font-smallcaps font-bold basis-24"
                    id="submit-button"
                    type="submit"
                    disabled={isSubmitting || isRateLimited}
                    value={isSubmitting ? 'Submitting' : 'Submit'}
                  />
                </div>
                {rateLimitError ? (
                  <p className="error">{rateLimitError}</p>
                ) : (
                  error && <p className="error">{error}</p>
                )}
              </form>
            </div>
          )}
          <GuessBox className="guess-box" guesses={guesses} />
        </div>
      )}
      <Section
        className={cx(
          'puzzle-container min-h-[50vh] max-h-full transition-height duration-1000 relative',
          {
            'bg-white after:bg-white after:drop-shadow-md rounded-md after:rounded-md':
              !darkMode,
            'bg-img': !!bgUrl,
          }
        )}
      >
        {cannedHints?.length > 0 && displayedCannedHints}
        {errata?.length > 0 && displayedErrata}
        {interaction && !isSolved && <InteractionForm {...interaction} />}
        {process.env.useWorker &&
          POSTHUNT_NEEDS_WORKER_PUZZLES.includes(slug) && <WorkerLoadingIcon />}
        {
          /* Pass guesses to child if render is a function. */
          typeof children === 'function' ? children(guesses) : children
        }
        {copyData && (
          <CopyToClipboard
            textRef={copyData.ref}
            selfRef={copyButtonRef}
            config={copyData.config}
          />
        )}
      </Section>
      <style jsx>{`
        :global(#__next) {
          background-image: ${puzzleData.round?.background
            ? `url(${puzzleData.round.background}) !important`
            : 'inherit'};
        }

        .puzzle.container {
          padding-bottom: 0;
        }

        .container.maxWidth,
        .container.maxWidth :global(section) {
          max-width: ${maxWidthPx}px;
        }

        :global(.puzzle-container.bg-img) {
          background-image: ${bgUrl ? `url(${bgUrl})` : 'inherit'};
          background-size: ${bgUrl ? 'cover' : 'inherit'};
          background-repeat: ${bgUrl ? 'repeat-y' : 'inherit'};
        }
      `}</style>
      <style jsx>{`
        /* Set drop-shadow on :after to avoid messing with position fixed */
        :global(.puzzle-container):after {
          content: ' ';
          position: absolute;
          left: 0;
          top: 0;
          height: 100%;
          width: 100%;
          z-index: -1;
        }

        :global(.darkmode .puzzle-container),
        :global(.darkmode .puzzle-container):after {
          border: none;
        }

        .container {
          margin: 0 auto;
        }

        .not-logged-in {
          border: 1px solid #000;
          padding: 8px 16px;
          margin-bottom: 16px;
        }

        :global(.darkmode) .not-logged-in {
          border: none;
        }

        .top-right {
          position: relative;
          z-index: 1;
          padding: 16px 0 8px;
          max-width: 80vw;
        }

        :global(.ui-wrapper) {
          max-width: 900px;
        }

        :global(.guess-box) {
          background: white;
          border-radius: 4px;
          margin-bottom: 50px;
          padding: 20px;
          width: 100%;
        }

        :global(.darkmode .guess-box) {
          background: transparent;
          border: 1px solid white;
        }

        input {
          font-size: 16px;
        }

        input[type='submit'] {
          font-size: 18px;
        }

        @media (max-width: 800px) {
          :global(.guess-box) {
            width: 95vw;
          }

          .top-right {
            max-width: 100vw;
          }

          h1 {
            font-size: 40px;
            line-height: 40px;
          }

          .inputs input {
            max-width: 80%;
          }
        }

        @media print {
          :global(.guess-box) {
            display: none;
          }

          .container {
            max-width: 100%;
          }

          .container.maxWidth :global(.puzzle-container),
          :global(.puzzle-container) {
            width: 100% !important;
            max-width: 100%;
          }

          :global(.puzzle-container):after {
            display: none;
          }
        }
      `}</style>
    </div>
  );
};

export default Puzzle;

interface PuzzleOptions {
  bare?: boolean;
  solution?: boolean;
}

interface PuzzleDataServerResponse extends PuzzleData {
  redirect?: string;
}
interface PuzzleDataResponseProps {
  puzzleData: PuzzleData;
  bare?: boolean;
  cryptKeys?: CryptKeys;
}

/* Returns a prop getter for a particular puzzle. */
export const getPuzzleProps =
  (slug: string, options: PuzzleOptions = {}) =>
  async (context) => {
    const { bare = false } = options;
    let puzzleData: PuzzleDataServerResponse;
    // Fetches data from the server.
    puzzleData = await serverFetch<PuzzleDataServerResponse>(
      context,
      `/puzzle/${slug}${options.solution ? '?s=1' : ''}`
    );

    // Check that the puzzle is accessible
    if (puzzleData.statusCode === 404) {
      return {
        props: {
          statusCode: puzzleData.statusCode,
          puzzleData: null,
        },
      };
    } else if (puzzleData.statusCode === 302) {
      let destination: string = puzzleData.redirect!;
      if (destination.startsWith(process.env.basePath!)) {
        destination = destination.slice(process.env.basePath!.length);
      }
      return {
        redirect: {
          destination,
          permanent: false,
        },
      };
    }

    const props: PuzzleDataResponseProps = {
      puzzleData,
      bare,
    };
    // If cryptKeys exist for the puzzle, move it to the root level.
    const cryptKeys = puzzleData.private?.cryptKeys;
    if (cryptKeys) {
      props.cryptKeys = cryptKeys;
      delete puzzleData.private.cryptKeys;
    }

    return { props };
  };

export const getClientPuzzleProps = async (router, slug: string) => {
  const puzzleData = await clientFetch<PuzzleData>(router, `/puzzle/${slug}`);
  return puzzleData;
};
