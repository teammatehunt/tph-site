import React, { useContext, useState } from 'react';
import Link from 'components/link';
import { useRouter } from 'utils/router';
import cx from 'classnames';

import Custom404 from 'pages/404';
import HuntInfoContext from 'components/context';
import InfoIcon from 'components/info_icon';
import Section from 'components/section';
import { clientFetch, serverFetch } from 'utils/fetch';

interface PuzzleData {
  slug: string;
  name: string;
}

interface FreeAnswerResponse {
  message: string;
  answer?: string;
}

interface Props {
  rounds: Record<string, PuzzleData[]>;
  currency: number;
  used: string[];
}

const FreeAnswerForm: React.FC<Props> = ({ rounds, currency, used }) => {
  const router = useRouter();
  const { huntInfo, userInfo } = useContext(HuntInfoContext);
  const [message, setMessage] = useState('');
  const [answer, setAnswer] = useState('');
  const [isSubmitting, setSubmitting] = useState(false);
  const [isError, setError] = useState(false);

  if (!rounds || !userInfo?.teamInfo) {
    return <Custom404 />;
  }

  const onSubmit = async (e) => {
    e.preventDefault();
    if (
      !confirm(
        "Are you sure you'd like to use a free answer for this puzzle? This cannot be reversed."
      )
    ) {
      return;
    }
    const data = new FormData(e.target);
    setSubmitting(true);
    const response = await clientFetch<FreeAnswerResponse>(
      router,
      `/free_answer/${data.get('slug')}`,
      {
        method: 'POST',
      }
    );
    setSubmitting(false);
    setMessage(response.message);
    setError(response.statusCode !== 200);
    setAnswer(response.answer ?? '');
  };

  return (
    <Section title="Use Free Answer" narrow>
      <div className="mt-4 border border-dashed border-black p-2 rounded">
        <InfoIcon>
          You have{' '}
          <b>
            {currency} event reward{currency === 1 ? '' : 's'}
          </b>
          .
        </InfoIcon>
      </div>
      <p>
        Return to <Link href="/events">Events page</Link>.
      </p>

      <div className="flex justify-between">
        <div className="w-3/4 grow">
          {userInfo?.public ? (
            <p className="chat-bubble">
              During hunt, you could redeem event rewards for free answers here.
            </p>
          ) : currency <= 0 ? (
            <p className="chat-bubble">
              You may redeem a free answer here when you have more event
              rewards.
            </p>
          ) : (
            <>
              <p className="chat-bubble">
                You may redeem a free answer for one of these puzzles:
              </p>
              <form onSubmit={onSubmit}>
                <select className="p-2" name="slug" id="slug">
                  {Object.entries(rounds).map(([round, puzzles]) => (
                    <optgroup key={round} label={round}>
                      {puzzles.map(({ slug, name }) => (
                        <option key={slug} value={slug}>
                          {name}
                        </option>
                      ))}
                    </optgroup>
                  ))}
                </select>

                <input
                  className="px-2 py-1"
                  type="submit"
                  disabled={!!answer || currency === 0 || isSubmitting}
                  value={isSubmitting ? 'Submitting' : 'Submit'}
                />
              </form>
            </>
          )}
        </div>
      </div>

      {message && (
        <p className={cx('chat-bubble', { error: isError })}>{message}</p>
      )}
      {answer && (
        <p>
          The answer is <span className="font-mono spoiler">{answer}</span>
        </p>
      )}
      {used.length > 0 && (
        <>
          <h4>Previous Uses</h4>
          {used.map((name, i) => (
            <p key={i}>
              <b>{name}</b>
            </p>
          ))}
        </>
      )}
    </Section>
  );
};

export default FreeAnswerForm;

export const getServerSideProps = async (context) => {
  const props = await serverFetch<Props>(context, '/free_answer', {
    method: 'GET',
  });
  return { props };
};
