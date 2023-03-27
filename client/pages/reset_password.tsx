import Link from 'components/link';
import { useRouter } from 'utils/router';
import { useState } from 'react';

import Section from 'components/section';
import HuntEmail from 'components/hunt_email';
import { clientFetch, serverFetch } from 'utils/fetch';
import { DjangoFormResponse, DjangoFormErrors } from 'types';

interface RegisterForm {
  username?: string;
  token?: string;
  new_password1?: string;
  new_password2?: string;
}

interface Props {
  valid?: boolean;
}

const ResetPassword = ({ valid }: Props) => {
  const router = useRouter();
  const [errors, setErrors] = useState<DjangoFormErrors<RegisterForm>>({});
  const [resetComplete, setResetComplete] = useState(false);

  const onSubmit = (e) => {
    e.preventDefault();
    const data = new FormData(e.target);
    clientFetch<DjangoFormResponse<RegisterForm, void>>(
      router,
      '/reset_password',
      {
        method: 'POST',
        body: data,
      }
    ).then((resp) => {
      if (!resp?.form_errors) {
        setResetComplete(true);
      } else {
        setErrors(resp.form_errors);
      }
    });
  };

  if (!valid) {
    return (
      <Section narrow heading="Reset team password">
        <p>
          The link you followed is not valid. It's possible that it has already
          been used, or it has expired.
        </p>
        <p>
          If you are having trouble accessing your account, please contact us at{' '}
          <HuntEmail />.
        </p>
      </Section>
    );
  }

  if (resetComplete) {
    return (
      <Section narrow heading="Password successfully reset">
        Your team's password has successfully been reset, and you should now be
        able to{' '}
        <Link href="/login">
          <a>log in</a>
        </Link>
        .
      </Section>
    );
  }

  const teamName = router.query['username'];
  const token = router.query['token'];

  return (
    <Section center heading="Reset team password">
      <form
        className="flex flex-col items-center justify-center mx-auto my-0"
        onSubmit={onSubmit}
      >
        <input
          hidden
          readOnly
          name="username"
          type="text"
          value={teamName}
          required
        />
        <input
          hidden
          readOnly
          name="token"
          type="text"
          value={token}
          required
        />

        <input
          name="new_password1"
          type="password"
          placeholder="New Password"
          required
        />
        {errors.new_password1 && (
          <p className="formerror">{errors.new_password1}</p>
        )}

        <input
          name="new_password2"
          type="password"
          placeholder="Confirm Password"
          required
        />
        {errors.new_password2 && (
          <p className="formerror">{errors.new_password2}</p>
        )}

        <button type="submit">Reset Password</button>
        {errors.__all__ && <p className="formerror">{errors.__all__}</p>}
      </form>

      <style jsx>{`
        form {
          max-width: 500px;
        }

        form > * {
          width: 100%;
          margin-top: 1em;
          font-size: 16px;
          padding: 4px 16px;
        }
      `}</style>
    </Section>
  );
};

export const getServerSideProps = async (context) => {
  const props = await serverFetch<Props>(context, '/validate_token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(context.query),
  });

  return { props };
};

export default ResetPassword;
