import React, { useState } from 'react';
import { useRouter } from 'utils/router';

import InfoIcon from 'components/info_icon';
import { clientFetch } from 'utils/fetch';

export interface Interaction {
  slug: string;
  instructions?: string;
  ended?: boolean;
  comments?: string;
}

interface Response {
  message?: string;
}

const InteractionForm: React.FC<Interaction> = ({
  slug,
  instructions,
  ended,
  comments,
}) => {
  const router = useRouter();
  const [isSubmitting, setSubmitting] = useState<boolean>(false);
  const [message, setMessage] = useState(
    comments
      ? 'Your previous request has been confirmed. We will contact you as soon as we can.'
      : ''
  );

  if (ended) {
    return (
      <InfoIcon>
        This physical puzzle or interaction is no longer available to do on
        campus.
      </InfoIcon>
    );
  }

  const onSubmit = async (e) => {
    e.preventDefault();
    const data = new FormData(e.target);
    setSubmitting(true);
    const response = await clientFetch<Response>(
      router,
      `/interaction/${slug}`,
      {
        method: 'POST',
        body: data,
      }
    );
    setSubmitting(false);
    setMessage(response.message ?? '');
  };

  return (
    <div className="rounded-md border border-dashed border-black dark:border-white p-2 space-y-2 mb-4">
      <InfoIcon>
        {instructions
          ?.split(/\r?\n/)
          .map((line, i) => <p key={i}>{line}</p>) ?? (
          <p>This is a physical puzzle.</p>
        )}
      </InfoIcon>
      <form onSubmit={onSubmit}>
        <textarea
          name="comments"
          id="comments"
          className="w-full p-2"
          defaultValue={comments ?? ''}
        />
        <input
          className="ui-button px-2 py-1"
          type="submit"
          disabled={isSubmitting}
          value={isSubmitting ? 'Submitting' : 'Submit'}
        />
      </form>
      {message && <div>{message}</div>}
    </div>
  );
};

export default InteractionForm;
