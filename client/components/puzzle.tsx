import React, {
  FunctionComponent,
  useContext,
  useMemo,
  useEffect,
  useState,
  useCallback,
} from 'react';
import parse from 'html-react-parser';
import { Router, useRouter } from 'next/router';
import Head from 'next/head';
import Link from 'next/link';
import cx from 'classnames';

import PuzzleTitle from 'components/puzzle_title';
import HuntInfoContext, { Errata } from 'components/context';
import InfoIcon from 'components/info_icon';
import Section from 'components/section';
import { Countdown } from 'components/countdown';
import { DjangoFormErrors } from 'types';
import { clientFetch, serverFetch, useEventWebSocket } from 'utils/fetch';
import { formattedDateTime } from 'utils/timer';
import StoryNotifications from 'components/story_notifications';
import LinkIfStatic from 'components/link';

const answerize = (s: string) => {
  return s ? s.toUpperCase().replace(/[^A-Z]/g, '') : '';
};

export interface Guess {
  timestamp: string;
  guess: string;
  response: string;
  isCorrect?: boolean;
}

export interface RateLimitData {
  guessCount: number;
  shouldLimit: boolean;
  secondsToWait?: number;
  guessesLeft: number;
  grantUnderReview: boolean;
}

export interface PuzzleData {
  name: string;
  slug: string;
  isSolved?: boolean;
  guesses?: Guess[];
  solutionLinkVisible?: boolean;
  adminLinkVisible?: boolean;
  adminUrl?: string;
  rateLimit?: RateLimitData;
  canViewHints?: boolean;
  canAskForHints?: boolean;
  errata?: Errata[];
  answerB64Encoded?: string;
  partialMessagesB64Encoded?: [string, string][];
  puzzleUrl?: string;
  round?: string;
  endcapUrl?: string;
  storyUrl?: string;
  endcapSlug?: string;
  private?: any; // Custom puzzle-specific data.
}

interface AnswerForm {
  answer?: string;
}

interface SolveResponse {
  form_errors?: DjangoFormErrors<AnswerForm>;
  guesses?: Guess[];
  ratelimit_data?: RateLimitData;
}

interface MoreGuessResponse {
  granted: boolean;
}

interface Props {
  titleHtml?: React.ReactFragment;
  nameOverride?: string;
  puzzleData: PuzzleData;
  showTitle?: boolean;
  smallTitle?: boolean;
  maxWidth?: boolean;
  maxWidthPx?: number;
}

interface LinkData {
  href: string;
  text: string;
}

function getCountdown(secondsToWait, setError, setSecondsToWait) {
  const countdownCallback = function () {
    // Cleanup errors tied to rate limit.
    setError('');
    setSecondsToWait(0);
  };
  return (
    <Countdown
      seconds={secondsToWait}
      textOnCountdownFinish=""
      countdownFinishCallback={countdownCallback}
      showHours
    />
  );
}

const getEndcapUrl = (puzzleData: PuzzleData) => puzzleData.endcapUrl;

/**
 * Wrapper component for all puzzles with logic for submissions, as well as
 * displaying past guesses.
 */
const Puzzle: FunctionComponent<Props> = ({
  titleHtml,
  puzzleData,
  nameOverride,
  showTitle = true,
  smallTitle = false,
  maxWidth = true,
  maxWidthPx = 900,
  children,
}) => {
  const router = useRouter();
  const { userInfo, huntInfo } = useContext(HuntInfoContext);
  const [error, setError] = useState<any>('');
  const [guesses, setGuesses] = useState<Guess[]>(puzzleData.guesses ?? []);
  const [isSolved, setSolved] = useState<boolean>(puzzleData.isSolved ?? false);

  const [isSubmitting, setSubmitting] = useState<boolean>(false);
  const [secondsToWait, setSecondsToWait] = useState<number>(
    puzzleData.rateLimit?.secondsToWait ?? 0
  );
  const [isRateLimited, setRateLimited] = useState<boolean | undefined>(
    puzzleData.rateLimit?.shouldLimit
  );
  // For static version, start this at 20 instead of using puzzleData.
  const [guessesLeft, setGuessesLeft] = useState<number>(
    process.env.isStatic ? 20 : puzzleData.rateLimit?.guessesLeft ?? 20
  );
  // Only used in static version.
  const [totalGuesses, setTotalGuesses] = useState<number>(20);
  const [moreGuessesPending, setMoreGuessesPending] = useState<
    boolean | undefined
  >(puzzleData.rateLimit?.grantUnderReview);
  const [errata, setErrata] = useState<Errata[]>(puzzleData.errata ?? []);

  const slug = puzzleData.slug;
  const huntIsOver = huntInfo && new Date() > new Date(huntInfo.endTime);
  const loggedIn = !!userInfo?.teamInfo;

  /* Websocket handler which syncs guesses, rate limits, etc. with the rest of
  /* the team. */
  const websocketHandler = useCallback((message) => {
    if (message?.data?.puzzle?.slug === puzzleData.slug) {
      if (message?.data?.guess) {
        setGuesses((guesses) => [message.data.guess, ...guesses]);
        if (message?.data?.guess?.isCorrect) setSolved(true);
      }
      if (message?.data?.rateLimit) {
        setSecondsToWait(message?.data?.rateLimit?.secondsToWait);
        setRateLimited(message?.data?.rateLimit?.shouldLimit);
        setGuessesLeft(message?.data?.rateLimit?.guessesLeft);
        setMoreGuessesPending(message?.data?.rateLimit?.grantUnderReview);
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
  }, [puzzleData]);

  useEffect(() => {
    if (secondsToWait > 0) {
      const timer = getCountdown(secondsToWait, setError, setSecondsToWait);
      const error = (
        <>
          <span>
            You've submitted too many guesses. Your next guess will be available
            in:
          </span>{' '}
          <strong>{timer}</strong>
        </>
      );
      setError(error);
    } else {
      setError('');
    }
  }, [secondsToWait]);

  /* Shows the hint, solution, and stats links if unlocked. */
  const getTopRightLinks = useMemo((): LinkData[] => {
    const topRightLinks: LinkData[] = [];
    if (puzzleData?.canViewHints) {
      topRightLinks.push({
        href: `/hints/${slug}`,
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
    return topRightLinks;
  }, [guesses, puzzleData]);

  /* In static mode (or post-hunt) this is used to check answers against a
   * base64 encoded answer. */
  const onSubmitLocalChecker = (e) => {
    e.preventDefault();
    const data = new FormData(e.target);
    e.target.reset(); // Clear the form input
    const guess = answerize(data.get('answer') as string);
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
      setError(
        "You've submitted too many guesses. You may request more guesses with the button below."
      );
    } else {
      const guessB64Encoded = btoa(guess);
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
      setGuessesLeft(totalGuesses - newGuesses.length);
      if (isCorrect) {
        setSolved(true);
      } else if (totalGuesses - newGuesses.length <= 0) {
        setRateLimited(true);
        setError(
          "You've submitted too many guesses. You may request more guesses with the button below."
        );
      }
    }
  };

  const moreGuessOnSubmitLocal = async (e) => {
    e.preventDefault();
    e.target.reset(); // Clear the form input

    setRateLimited(false);
    setTotalGuesses(totalGuesses + 20);
    setGuessesLeft(totalGuesses - guesses.length + 20);
    setError('');
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    const data = new FormData(e.target);
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
      setGuessesLeft(response.ratelimit_data.guessesLeft);
    }
    if (response?.guesses) {
      // A successful guess happened.
      const newGuesses = response.guesses;
      setGuesses(newGuesses);
      if (!isSolved && newGuesses[0]?.isCorrect) {
        setSolved(true);
      }
    }
    if (response?.ratelimit_data?.shouldLimit) {
      // We were already rate limited and tried to make a guess.
      // Do not update the error message, even if an error is defined, because
      // doing so overwrites the countdown.
    } else if (response?.form_errors) {
      // We were not rate limited but our answer submit was bad for some reason.
      setError(response.form_errors.answer || response.form_errors.__all__!);
    } else {
      setError(''); // wipe errors from previous guess
    }
    if (response?.ratelimit_data?.shouldLimit) {
      // Always turn on request button on final guess even if a request is
      // pending.
      if (!rateLimitedBefore) {
        setMoreGuessesPending(false);
      }
      // Is always defined, this is just so Typescript knows.
      if (response?.ratelimit_data?.secondsToWait !== undefined) {
        setSecondsToWait(response.ratelimit_data.secondsToWait);
      }
    }
  };

  const moreGuessOnSubmit = async (e) => {
    e.preventDefault();
    e.target.reset(); // Clear the form input

    const response = await clientFetch<MoreGuessResponse>(
      router,
      `/puzzle/${slug}/moreguesses`,
      { method: 'POST', body: {} }
    );
    setMoreGuessesPending(!response.granted);
  };

  const topRightElement = (
    <span>
      <h3 className="small-caps">
        {getTopRightLinks.map(({ href, text }, i) => (
          <LinkIfStatic key={`topright-${i}`} href={href} className="secondary">
            {text}
          </LinkIfStatic>
        ))}
      </h3>
      <style jsx>{`
        span {
          margin-left: auto;
        }
        h3 {
          display: flex;
          flex-wrap: wrap;
          font-size: 16px;
          margin: 0;
        }
        h3 :global(a) {
          padding: 0 0 0 16px;
        }
      `}</style>
    </span>
  );

  const displayedErrata = useMemo(
    () => (
      <div className="errata">
        {errata.map((err, i) => (
          <p className="error" key={`errata-${i}`}>
            <b>Erratum</b> on{' '}
            {err.formattedTime ??
              formattedDateTime(err.time, {
                month: 'numeric',
                year: '2-digit',
                second: undefined,
              })}
            : {parse(err.text)}
          </p>
        ))}

        <style jsx>{`
          .errata {
            margin: 0 auto;
            width: 80vw;
            max-width: 900px;
          }
        `}</style>
      </div>
    ),
    [errata]
  );

  return (
    <div className={cx('container', { maxWidth })}>
      {showTitle && (
        <Head>
          <title>{nameOverride ?? puzzleData.name}</title>
        </Head>
      )}

      <StoryNotifications onlyFinished />

      <div className="top-right flex-center-vert">{topRightElement}</div>
      <div className="puzzle-title-container flex-center-vert">
        {titleHtml || (
          <PuzzleTitle
            title={nameOverride ?? puzzleData.name}
            small={smallTitle}
          />
        )}
      </div>

      {errata?.length > 0 && displayedErrata}
      {!loggedIn && !huntIsOver ? (
        <div className="not-logged-in flex-center-vert">
          <InfoIcon>
            <em>
              You're currently not logged in! Feel free to look at the puzzle,
              but you'll need to sign up to check answers and progress through
              the hunt.
            </em>
          </InfoIcon>
        </div>
      ) : (
        <div className="guesses flex-center-vert">
          {!isSolved && (
            <div className="guess-box submission">
              <form
                onSubmit={
                  process.env.isStatic || (huntIsOver && !loggedIn)
                    ? onSubmitLocalChecker
                    : onSubmit
                }
              >
                <label
                  className="guess-header flex-center-vert"
                  htmlFor="answer"
                >
                  <h4 className="secondary small-caps">Submit a guess</h4>
                  <span>
                    <em>
                      {guessesLeft} guess
                      {guessesLeft !== 1 && 'es'} available
                    </em>
                  </span>
                </label>
                <div className="inputs">
                  <input
                    className="monospace"
                    name="answer"
                    id="answer"
                    disabled={isSubmitting}
                    type="text"
                  />
                  <input
                    className="small-caps"
                    type="submit"
                    disabled={isSubmitting || guessesLeft === 0}
                    value={isSubmitting ? 'Submitting' : 'Submit'}
                  />
                </div>
                {error && <p className="error">{error}</p>}
              </form>
              <form
                className="moreguesses"
                onSubmit={
                  process.env.isStatic || (huntIsOver && !loggedIn)
                    ? moreGuessOnSubmitLocal
                    : moreGuessOnSubmit
                }
              >
                {isRateLimited && (
                  <input
                    className="small-caps"
                    type="submit"
                    disabled={moreGuessesPending}
                    value={
                      moreGuessesPending
                        ? 'Request for more guesses pending approval'
                        : 'Request more guesses'
                    }
                  />
                )}
              </form>
            </div>
          )}
          {guesses.length > 0 && (
            <div className="guess-box log">
              <table className="center">
                <thead>
                  <tr>
                    <th className="small-caps">Guesses</th>
                    <th className="small-caps">Response</th>
                    <th className="small-caps">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {guesses.map(
                    ({ timestamp, guess, response, isCorrect }, i) => (
                      <tr key={i} className={isCorrect ? 'correct' : ''}>
                        <td
                          className={`guess monospace ${
                            guess.length >= 16 ? 'small' : ''
                          }`}
                        >
                          {guess}
                        </td>
                        <td>{parse(response)}</td>
                        <td suppressHydrationWarning>
                          {formattedDateTime(timestamp, {
                            month: 'numeric',
                            year: '2-digit',
                            second: 'numeric',
                          })}
                        </td>
                      </tr>
                    )
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      <Section>
        {
          /* Pass guesses to child if render is a function. */
          typeof children === 'function' ? children(guesses) : children
        }
      </Section>

      {getEndcapUrl(puzzleData) && (
        <Section center>
          <Link
            href={`/story${
              puzzleData.endcapSlug ? `#${puzzleData.endcapSlug}` : ''
            }`}
          >
            <a>
              <img className="endcap" src={getEndcapUrl(puzzleData)} />
            </a>
          </Link>
        </Section>
      )}

      <style jsx>{`
        .container {
          padding-bottom: 40px;
          margin: 0 auto;
        }

        .container.maxWidth,
        .container.maxWidth :global(section) {
          max-width: ${maxWidthPx}px;
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
          max-width: 80vw;
        }

        .puzzle-title-container {
          margin: 0 0 16px 0;
          filter: drop-shadow(2px 2px 0 rgba(0, 0, 0, 0.25));
        }

        :global(.darkmode) .puzzle-title-container {
          filter: drop-shadow(2px 2px 0 rgba(222, 197, 125, 0.25));
        }

        .guesses {
          flex-direction: column;
        }

        .guess-header {
          justify-content: space-between;
          padding-bottom: 8px;
        }

        .guess-box {
          margin-bottom: 50px;
          max-height: 240px;
          width: 80vw;
          max-width: 900px;
        }

        h4 {
          margin: 0;
        }

        .submission {
          display: flex;
          flex-direction: column;
          justify-content: center;
          text-align: center;
        }

        .log {
          border: 1px solid var(--text);
          overflow-y: auto;
          padding: 8px 12px;
        }

        .log table th {
          color: var(--muted);
        }

        table {
          margin: 8px 0;
          width: 100%;
        }

        .guess {
          font-size: 20px;
          white-space: normal;
          word-wrap: break-word;
          word-break: break-all;
          text-overflow: clip;
        }

        .guess.small {
          font-size: 16px;
        }

        td {
          padding: 4px 8px;
        }

        .correct {
          font-weight: bold;
          color: var(--primary);
        }

        form.moreguesses {
          margin-top: 0px;
          display: flex;
          justify-content: center;
        }

        form > div {
          display: flex;
        }

        .inputs {
          display: flex;
          justify-content: center;
          width: 100%;
        }

        input {
          font-size: 16px;
          padding: 8px 12px;
          width: 100%;
          flex: 1 0 300px;
        }

        input[type='submit'] {
          font-weight: bold;
          font-size: 18px;
          flex: 0 1 100px;
        }

        .endcap {
          margin-top: 24px;
          margin-left: -15%;
          width: 130%;
        }

        @media (max-width: 800px) {
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
      `}</style>
    </div>
  );
};

export default Puzzle;

/* Returns a prop getter for a particular puzzle. */
export const getPuzzleProps = (slug: string) => async (context) => {
  let puzzleData: PuzzleData;
  if (process.env.isStatic) {
    // Returns a static response for the puzzle data.
    puzzleData = require(`assets/json_responses/puzzles/${slug}.json`);
  } else {
    // Fetches data from the server.
    puzzleData = await serverFetch<PuzzleData>(context, `/puzzle/${slug}`);
  }

  return {
    props: {
      puzzleData,
    },
  };
};

export const getClientPuzzleProps = async (router, slug: string) => {
  const puzzleData = await clientFetch<PuzzleData>(router, `/puzzle/${slug}`);
  return puzzleData;
};
