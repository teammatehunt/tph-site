import React, { useContext, useState } from 'react';
import { useRouter } from 'next/router';
import { ParsedUrlQuery } from 'querystring';

import { PuzzleData } from 'components/puzzle';

import HuntInfoContext from 'components/context';
import Section from 'components/section';
import Title from 'components/title';

import { clientFetch, serverFetch } from 'utils/fetch';
import { formattedDateTime } from 'utils/timer';
import StoryNotifications from 'components/story_notifications';

interface UrlParams extends ParsedUrlQuery {
  slug: string;
}

interface Hint {
  isRequest: boolean;
  content: string;
  requiresResponse: boolean;
  submitTime: string;
}

interface Thread {
  threadId: number;
  status: string;
  hints: Hint[];
}

interface HintResponse {
  reply: string;
  introHintsRemaining?: number;
  nonIntroHintsRemaining?: number;
  hintThreads?: Thread[];
}

const HintForm = ({
  children,
  puzzleData,
  slug,
  introHintsLeft,
  setIntroHintsLeft,
  setNonIntroHintsLeft,
  setThreads,
  threadId,
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
      e.target.reset(); // Clear the form input.
      setSubmitting(true);
      const response = await clientFetch<HintResponse>(
        router,
        `/puzzle/${slug}/hint`,
        {
          method: 'POST',
          body: data,
        }
      );
      setSubmitting(false);
      setIsError(response.statusCode !== 200);
      setMessage(response.reply);
      if (isNewThread && response.statusCode === 200) {
        // something weird is happening with the caching, decrement it locally.
        if (puzzleData.isIntro && introHintsLeft > 0) {
          setIntroHintsLeft((introHintsLeft) => introHintsLeft - 1);
        } else {
          setNonIntroHintsLeft((hintsLeft) => hintsLeft - 1);
        }
      }
      if (response.hintThreads !== undefined) {
        setThreads(response.hintThreads);
      }
    }
  };

  const inputSubmit = (
    <input
      type="submit"
      disabled={isSubmitting}
      value={isSubmitting ? 'Submitting' : 'Submit'}
    />
  );

  return (
    <>
      <form method="post" onSubmit={onSubmit}>
        <input type="hidden" name="thread_id" value={threadId ?? ''} />
        <div>{children}</div>
        <div>
          <textarea
            name="text_content"
            cols={40}
            rows={10}
            disabled={isSubmitting}
            required
          ></textarea>
        </div>

        <p>
          When this is answered, send an email to:{' '}
          <select name="notify_emails">
            <option value="all">Everyone</option>

            <option value="none">No one</option>

            {info?.teamInfo?.members?.map((member, i) => {
              if (member.email) {
                return (
                  <option key={`emailchoices-${i}`} value={member.email}>
                    {member.name} ({member.email})
                  </option>
                );
              }
            })}
          </select>{' '}
          {isNewThread ? null : inputSubmit}
        </p>
        {!isNewThread ? null : inputSubmit}
      </form>
      <p className={isError ? 'error' : ''}>{message}</p>
      <style jsx>{`
        textarea {
          width: 100%;
          min-height: ${isNewThread ? '24ch' : '12ch'};
          ${isNewThread ? null : 'height: 12ch;'}
          font-family: monospace;
          font-size: 16px;
        }
        input {
          font-size: 16px;
          padding: 8px;
        }
      `}</style>
    </>
  );
};

const ThreadList = ({
  puzzleData,
  slug,
  thread,
  introHintsLeft,
  setIntroHintsLeft,
  setNonIntroHintsLeft,
  setThreads,
}) => {
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

  // TODO: Determine if we want to let teams add to their requests before we've responded.
  let formDescription = '';
  if (hasResponseForAll) {
    if (requestForMoreInfo)
      formDescription =
        'We’ve requested that you provide more information about what you know or what you have tried.';
    else if (hasSomeResponse)
      formDescription =
        'Did our hint not make sense or did we misunderstand your progress? Let us know. This does not cost a hint.';
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
              <div className="preserve-space">{content}</div>
              {!isRequest || !requiresResponse ? null : (
                <>
                  <br />
                  <div>
                    <em>Waiting on response</em>
                  </div>
                </>
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
          slug={slug}
          introHintsLeft={introHintsLeft}
          setIntroHintsLeft={setIntroHintsLeft}
          setNonIntroHintsLeft={setNonIntroHintsLeft}
          setThreads={setThreadsAndResetForm}
        >
          <div>
            <i>{formDescription}</i>
          </div>
        </HintForm>
      ) : (
        <div>
          <a href="#" className="form-description" onClick={onClick}>
            {formDescription}
          </a>
        </div>
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

const HintPage = ({ puzzleData, slug }) => {
  // Live update hint requests in place
  const [introHintsLeft, setIntroHintsLeft] = useState<number>(
    puzzleData.introHintsRemaining
  );
  const [nonIntroHintsLeft, setNonIntroHintsLeft] = useState<number>(
    puzzleData.nonIntroHintsRemaining
  );
  const [threads, setThreads] = useState<Hint[][]>(
    puzzleData.hintThreads ?? []
  );

  return (
    <Section>
      <Title title={`Hints: ${puzzleData.name}`} />
      <StoryNotifications onlyFinished />
      {puzzleData.canAskForHints && (
        <p>
          You have{' '}
          <strong>
            {introHintsLeft} hint{introHintsLeft === 1 ? '' : 's'}
          </strong>{' '}
          usable on the first round of puzzles.
        </p>
      )}
      {puzzleData.canAskForHints && (
        <p>
          You have{' '}
          <strong>
            {nonIntroHintsLeft} hint{nonIntroHintsLeft === 1 ? '' : 's'}
          </strong>{' '}
          usable on any puzzle.
        </p>
      )}
      {!puzzleData.canAskForHints && (
        <p>
          You may no longer ask for hints. Any previous hints you've asked are
          shown below.
        </p>
      )}

      {puzzleData.canAskForHints &&
        (!puzzleData.isIntro && puzzleData.nonIntroHintsRemaining == 0 ? (
          <p>You do not have any hints usable on this puzzle.</p>
        ) : (
          <HintForm
            puzzleData={puzzleData}
            slug={slug}
            threadId={null}
            introHintsLeft={introHintsLeft}
            setIntroHintsLeft={setIntroHintsLeft}
            setNonIntroHintsLeft={setNonIntroHintsLeft}
            setThreads={setThreads}
          >
            Describe everything you’ve tried on this puzzle. We will provide a
            hint to help you move forward. The more detail you provide, the less
            likely it is that we’ll tell you something you already know.
          </HintForm>
        ))}
      {puzzleData.canViewHints ? (
        threads.map((thread, i) => (
          <ThreadList
            key={i}
            puzzleData={puzzleData}
            thread={thread}
            slug={slug}
            introHintsLeft={introHintsLeft}
            setIntroHintsLeft={setIntroHintsLeft}
            setNonIntroHintsLeft={setNonIntroHintsLeft}
            setThreads={setThreads}
          />
        ))
      ) : (
        <p>Hints are no longer viewable</p>
      )}
    </Section>
  );
};

export default HintPage;

export const getServerSideProps = async (context) => {
  const { params } = context;
  const { slug } = params || {};
  let puzzleData: PuzzleData;
  if (process.env.isStatic) {
    puzzleData = require(`assets/json_responses/puzzles/${slug}.json`);
  } else {
    puzzleData = await serverFetch<PuzzleData>(context, `/puzzle/${slug}`);
  }

  return {
    props: {
      puzzleData,
      slug,
    },
  };
};

/*
export const getStaticPaths = async () => {
  return require('assets/json_responses/puzzle_paths.json');
};
*/
