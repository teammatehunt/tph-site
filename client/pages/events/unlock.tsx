import React, { useContext, useState } from 'react';
import Link from 'components/link';
import { useRouter } from 'utils/router';
import cx from 'classnames';

import Custom404 from 'pages/404';
import HuntInfoContext from 'components/context';
import InfoIcon from 'components/info_icon';
import Section from 'components/section';
import { clientFetch, serverFetch } from 'utils/fetch';

interface RoundData {
  slug: string;
  name: string;
}

interface UsesData {
  name: string;
  count: number;
}

interface UnlockResponse {
  message: string;
}

interface Props {
  rounds: RoundData[];
  currency: number;
  used: UsesData[];
}

const UnlockForm: React.FC<Props> = ({ rounds, currency, used }) => {
  const router = useRouter();
  const { huntInfo, userInfo } = useContext(HuntInfoContext);
  const [message, setMessage] = useState('');
  const [isSubmitting, setSubmitting] = useState(false);
  const [isError, setError] = useState(false);

  if (!rounds || !userInfo?.teamInfo) {
    return <Custom404 />;
  }

  const onSubmit = async (e) => {
    e.preventDefault();
    if (
      !confirm(
        "Are you sure you'd like to unlock a puzzle in this round? This cannot be reversed."
      )
    ) {
      return;
    }
    const data = new FormData(e.target);
    setSubmitting(true);
    const response = await clientFetch<UnlockResponse>(
      router,
      `/free_unlock/${data.get('slug')}`,
      {
        method: 'POST',
      }
    );
    setSubmitting(false);
    setError(response.statusCode !== 200);
    setMessage(response.message);
  };

  return (
    <Section title="Unlock New Puzzle" narrow>
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
        Return to{' '}
        <Link href="/events">
          <a>Events page</a>
        </Link>
        .
      </p>

      <div className="flex justify-between">
        <div className="w-3/4 grow">
          {userInfo?.public ? (
            <p className="chat-bubble">
              During hunt, you could redeem event rewards for free answers here.
            </p>
          ) : currency <= 0 ? (
            <p className="chat-bubble">
              You may unlock a new puzzle here when you have more event rewards.
            </p>
          ) : (
            <>
              <p className="chat-bubble">
                You may unlock a new puzzle in one of these rounds:
              </p>
              <form onSubmit={onSubmit}>
                <select className="p-2" name="slug" id="slug">
                  {rounds.map(({ name, slug }) => (
                    <option key={slug} value={slug}>
                      {name}
                    </option>
                  ))}
                </select>

                <input
                  className="px-2 py-1"
                  type="submit"
                  disabled={!!message || currency === 0 || isSubmitting}
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
      {used.length > 0 && (
        <>
          <h4>Previous Uses</h4>
          {used.map(({ name, count }, i) => (
            <p key={i}>
              <b>{name}:</b> {count} reward{count === 1 ? '' : 's'} used.
            </p>
          ))}
        </>
      )}
    </Section>
  );
};

export default UnlockForm;

export const getServerSideProps = async (context) => {
  const props = await serverFetch<Props>(context, '/free_unlock', {
    method: 'GET',
  });
  return { props };
};
