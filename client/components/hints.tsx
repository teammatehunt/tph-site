import React, { useContext, useState } from 'react';
import Head from 'next/head';
import Link from 'components/link';
import cx from 'classnames';
import { useRouter } from 'utils/router';
import { ParsedUrlQuery } from 'querystring';

import { PuzzleData, RoundHeader, getPuzzleProps } from 'components/puzzle';
import HuntInfoContext from 'components/context';
import PuzzleTitle from 'components/puzzle_title';
import Section from 'components/section';

import { clientFetch } from 'utils/fetch';
import { formattedDateTime } from 'utils/timer';

interface UrlParams extends ParsedUrlQuery {
  slug: string;
}

interface Hint {
  isRequest: boolean;
  content: string;
  requiresResponse: boolean;
  submitTime: string;
}

interface PuzzleHint extends PuzzleData {
  hintThreads?: Hint[][];
}

interface Thread {
  threadId: number;
  status: string;
  hints: Hint[];
}

interface HintResponse {
  reply: string;
  hintThreads?: Thread[];
}

const HintForm = ({
  puzzleData,
  setThreads,
  threadId,
  onSubmitHint,
  children,
}) => {
  const router = useRouter();
  const info = useContext(HuntInfoContext).userInfo;
  const [isError, setIsError] = useState<boolean>(false);
  const [message, setMessage] = useState<string>('');

  const [isSubmitting, setSubmitting] = useState<boolean>(false);

  const isNewThread = threadId === null;

  const onSubmit = async (e) => {
    e.preventDefault();
    const warningMessage = puzzleData.isSolved
      ? 'You have already solved this puzzle! '
      : '';
    if (confirm(`${warningMessage}Are you sure about your hint request?`)) {
      const data = new FormData(e.target);
      if (!data.get('notify_emails')) {
        data.set('notify_emails', 'none');
      }
      e.target.reset(); // Clear the form input.
      setSubmitting(true);
      const response = await clientFetch<HintResponse>(
        router,
        `/puzzle/${puzzleData.slug}/hint`,
        {
          method: 'POST',
          body: data,
        }
      );
      setSubmitting(false);
      setIsError(response.statusCode !== 200);
      setMessage(response.reply);
      if (response.hintThreads !== undefined) {
        setThreads(response.hintThreads);
      }
      if (response.statusCode === 200) {
        onSubmitHint();
      }
    }
  };

  const inputSubmit = (
    <input
      className="ui-button px-2 py-1"
      type="submit"
      disabled={isSubmitting}
      value={isSubmitting ? 'Submitting' : 'Submit'}
    />
  );

  return (
    <>
      <form method="post" onSubmit={onSubmit}>
        <input type="hidden" name="thread_id" value={threadId ?? ''} />
        {children}
        <div>
          <textarea
            className="font-mono p-2"
            name="text_content"
            cols={40}
            rows={10}
            disabled={isSubmitting}
            required
          />
        </div>

        <p>
          <input name="notify_emails" type="checkbox" value="all" /> Notify team
          via email when your hint is answered?
          <br />
          (You will always receive a notification via hunt site.)
        </p>
        {inputSubmit}
      </form>
      <p className={isError ? 'error' : ''}>{message}</p>

      <style jsx>{`
        textarea {
          width: 100%;
          min-height: ${isNewThread ? '24ch' : '12ch'};
          ${isNewThread ? null : 'height: 12ch;'}
          font-size: 16px;
        }
        input {
          font-size: 16px;
          padding: 8px;
        }

        :global(.darkmode input[type='submit']),
        :global(.darkmode) p,
        :global(.darkmode) textarea {
          color: var(--white);
        }
        :global(.darkmode input[type='submit']),
        :global(.darkmode) textarea,
        :global(.darkmode) select {
          background: transparent;
          border-color: var(--white);
        }
      `}</style>
    </>
  );
};

const ThreadList = ({ puzzleData, thread, setThreads }) => {
  const [showForm, setShowForm] = useState<boolean>(false);

  const hintRefunded = ['REF', 'OBS'].includes(thread.status);
  const hasSomeResponse = thread.hints.some((hint) => !hint.isRequest);
  // OBSOLETE and RESOLVED count as being responded to
  const hasResponseForAll = thread.hints.every(
    (hint) =>
      !hint.isRequest ||
      !hint.requiresResponse ||
      ['OBS', 'RES'].includes(hint.status)
  );

  const requestForMoreInfo = thread.status === 'MOR' && hasResponseForAll;
  const shouldShowForm = showForm || requestForMoreInfo;

  let formDescription = '';
  if (hasResponseForAll) {
    if (requestForMoreInfo)
      formDescription =
        'We’ve requested that you provide more information about what you know or what you have tried.';
    else if (hasSomeResponse)
      formDescription =
        'Did our hint not make sense or did we misunderstand your progress? Let us know.';
  }

  const onClick = (e) => {
    e.preventDefault();
    setShowForm(true);
  };
  const setThreadsAndResetForm = (...args) => {
    setThreads(...args);
    setShowForm(false);
  };

  return (
    <div>
      <hr />
      {!hintRefunded ? null : (
        <div>
          <strong>(hint refunded)</strong>
        </div>
      )}
      {thread.hints.map(
        ({ isRequest, content, requiresResponse, submitTime }, i) => (
          <React.Fragment key={i}>
            <div>
              <div>
                <strong>{isRequest ? 'Q' : 'A'}</strong> (
                {formattedDateTime(submitTime, {
                  month: 'numeric',
                  year: '2-digit',
                  second: 'numeric',
                })}
                ):
              </div>
              <div className="preserve-space">
                {content || (!isRequest ? <i>Resolved</i> : '')}
              </div>
              {!isRequest || !requiresResponse ? null : (
                <p>
                  <em>Waiting on response</em>
                </p>
              )}
            </div>
            <br />
          </React.Fragment>
        )
      )}

      {shouldShowForm ? (
        <HintForm
          threadId={thread.threadId}
          puzzleData={puzzleData}
          setThreads={setThreadsAndResetForm}
          onSubmitHint={() => void setShowForm(false)}
        >
          <div>
            <i>{formDescription}</i>
          </div>
        </HintForm>
      ) : (
        puzzleData.canAskForHints && (
          <div>
            <a href="#" className="form-description" onClick={onClick}>
              {formDescription}
            </a>
          </div>
        )
      )}

      <style jsx>{`
        .preserve-space {
          white-space: pre-line;
          word-break: break-word;
        }
        .form-description {
          font-style: italic;
          color: var(--primary);
        }
      `}</style>
    </div>
  );
};

interface Props {
  puzzleData: PuzzleHint;
  smallTitle?: boolean;
  title?: string;
  darkMode?: boolean;
  onBack?: () => void;
  className?: string;
}

export const HintComponent: React.FC<Props> = ({
  puzzleData,
  className,
  children,
}) => {
  const [hintRequested, setHintRequested] = useState(false);

  // Live update hint requests in place
  const [threads, setThreads] = useState<Hint[][]>(
    puzzleData.hintThreads ?? []
  );

  return (
    <Section className={cx('relative z-[1]', className)}>
      <div className="flex items-center">
        <p className="ml-4 mr-auto">
          <span className="p-2 chat-bubble">{puzzleData.hintReason}</span>
        </p>
      </div>

      {puzzleData.canAskForHints && !hintRequested && (
        <HintForm
          puzzleData={puzzleData}
          threadId={null}
          setThreads={setThreads}
          onSubmitHint={() => void setHintRequested(true)}
        >
          <p>
            Describe everything you’ve tried on this puzzle. We will provide a
            hint to help you move forward. The more detail you provide, the less
            likely it is that we’ll tell you something you already know.
          </p>
        </HintForm>
      )}
      {hintRequested && (
        <p>
          Your hint has been submitted. We will get back to you as soon as we
          can!
        </p>
      )}
      {puzzleData.canViewHints &&
        threads.map((thread, i) => (
          <ThreadList
            key={i}
            puzzleData={puzzleData}
            thread={thread}
            setThreads={setThreads}
          />
        ))}
      <style jsx>{``}</style>
    </Section>
  );
};

const HintPage: React.FC<Props> = ({
  puzzleData,
  smallTitle = false,
  title = undefined,
  darkMode = false,
  onBack = undefined,
  className,
  children,
}) => {
  return (
    <div
      className={cx('container', {
        darkmode: darkMode,
      })}
    >
      <Head>
        <title>{title ?? `Hints: ${puzzleData.name}`}</title>
      </Head>

      <div className="top-right">
        <Link
          href={puzzleData.url}
          className="bg-navbar p-1.5 rounded-lg mb-2"
          onClick={onBack}
        >
          Back to Puzzle
        </Link>
      </div>

      {puzzleData.round?.header && <RoundHeader round={puzzleData.round} />}

      <div className="flex items-center justify-center">
        <PuzzleTitle title={title ?? puzzleData.name} small={smallTitle} />
      </div>

      <HintComponent puzzleData={puzzleData} className={className} />

      {children}

      <style jsx>{`
        .container {
          margin: 0 auto;
        }

        .top-right {
          position: relative;
          z-index: 1;
          padding: 16px 0 8px;
          margin: 0 0 0 auto;
          width: fit-content;
        }

        .container,
        .container :global(section) {
          max-width: 900px;
        }

        :global(body) {
          background-image: ${puzzleData.round?.background
            ? `url(${puzzleData.round.background}) !important`
            : 'inherit'};
        }

        :global(.darkmode) p {
          color: white;
        }
      `}</style>
    </div>
  );
};

export default HintPage;

export const getHintServerSideProps =
  (act: number, round?: string) => async (context) => {
    const { params } = context;
    const { slug } = params || {};
    const { props } = await getPuzzleProps(slug)(context);
    const puzzleData = props?.puzzleData;
    if (!puzzleData || !puzzleData.round) {
      return { props };
    }

    if (
      puzzleData.round.act !== act ||
      (round && puzzleData?.round.slug !== round)
    ) {
      return {
        props: {
          statusCode: 404,
          puzzleData: null,
        },
      };
    }

    return {
      props,
    };
  };
