import React, { useState } from 'react';
import { useRouter } from 'next/router';

import { FormRow } from 'components/form';
import Section from 'components/section';
import Title from 'components/title';
import { DjangoFormErrors, DjangoFormResponse } from 'types';
import { clientFetch, serverFetch } from 'utils/fetch';

interface UnsubscribeFormProps {
  email?: string;
}

const Unsubscribe = ({ hasError, endpointUrl, endpointKey }) => {
  const router = useRouter();
  const [unsubscribedAddress, setUnsubscribedAddress] = useState('');
  const [isSubmitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState('');
  const [serverError, setServerError] = useState(false);
  const onSubmit = async (e) => {
    e.preventDefault();
    const data = new FormData(e.target);
    const email = data.get('email') as string;
    if (!email) return;

    setSubmitting(true);
    setErrors('');
    setServerError(false);

    try {
      if (endpointUrl) {
        const response = await fetch(endpointUrl, {
          method: 'POST',
          mode: 'no-cors',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
          },
          body: `${endpointKey}=${encodeURIComponent(email)}`,
        });
        // status should be 0 due to CORS policy
        if (response.status === 200 || response.status === 0) {
          setUnsubscribedAddress(email);
        } else {
          setServerError(true);
        }
      } else {
        const response = await clientFetch<
          DjangoFormResponse<UnsubscribeFormProps, void>
        >(router, router.asPath, {
          method: 'POST',
          body: data,
        });

        if (response?.form_errors?.email) {
          setErrors(response.form_errors.email);
        } else if (response === undefined || response.statusCode !== 200) {
          setServerError(true);
        } else {
          setUnsubscribedAddress(email);
        }
      }
    } catch {
      setServerError(true);
    }
    setSubmitting(false);
  };
  // FIXME
  const unsubscribe_address = 'unsubscribe@mypuzzlehunt.com';
  return (
    <>
      <Title title="Unsubscribe" />
      <div className="main center">
        {(unsubscribedAddress && (
          <p>'{unsubscribedAddress}' has been unsubscribed from all emails.</p>
        )) ||
          (serverError && (
            <p className="error">
              Something unexpected happened when unsubscribing. Please send an
              email from the address you wish to unsubscribe to{' '}
              <a href={`mailto:${unsubscribe_address}`}>
                {unsubscribe_address}
              </a>{' '}
              to unsubscribe.
            </p>
          )) || (
            <>
              <p>Enter your email address to unsubscribe from all emails.</p>
              <form onSubmit={onSubmit}>
                <div className="row">
                  <div>
                    <FormRow name="email" label="Email" errors={errors} />
                  </div>
                  <input
                    type="submit"
                    disabled={isSubmitting}
                    value="Unsubscribe"
                  />
                </div>
              </form>
            </>
          )}
      </div>
      <style jsx>{`
        div.main {
          margin-top: 2em;
          max-width: 600px;
          margin-left: auto;
          margin-right: auto;
        }

        div.row {
          justify-content: center;
          align-items: flex-start;
        }

        input[type='submit'] {
          margin-left: 1em;
          padding: 4px 8px;
        }
      `}</style>
    </>
  );
};
export default Unsubscribe;

export const getServerSideProps = async (context) => {
  let notFound = false;
  let hasError = false;
  let endpointUrl: string | null = null;
  let endpointKey: string | null = null;
  if (process.env.isStatic) {
    // our unsubscribe google form
    endpointUrl = `https://docs.google.com/forms/d/e/${
      null /* FIXME */
    }/formResponse`;
    endpointKey = `entry.${12345 /* FIXME */}`;
  } else {
    const resp = await serverFetch(context, context.req.url);
    hasError = resp.statusCode !== 200;
    notFound = resp.statusCode === 404;
  }
  return {
    props: {
      hasError,
      endpointUrl,
      endpointKey,
    },
    notFound,
  };
};
