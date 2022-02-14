import { useRouter } from 'next/router';
import { useState } from 'react';

import HuntEmail from 'components/hunt_email';
import Title from 'components/title';
import { clientFetch } from 'utils/fetch';
import { DjangoFormErrors, DjangoFormResponse } from 'types';
import { FormRow } from 'components/form';

interface LoginFormProps {
  username?: string;
  password?: string;
}
type LoginFormErrors = DjangoFormErrors<LoginFormProps>;

interface ResetPwForm {
  username?: string;
}
type ResetPwFormErrors = DjangoFormErrors<ResetPwForm>;

const LoginForm = ({ onLoggedIn }) => {
  const router = useRouter();
  const [isLogin, setIsLogin] = useState(true);
  const [hasRequestedPwReset, setHasRequestedPwReset] = useState(false);
  const [loginErrors, setLoginErrors] = useState<LoginFormErrors>({});
  const [resetPwErrors, setResetPwErrors] = useState<ResetPwFormErrors>({});
  const [isSubmitting, setSubmitting] = useState<boolean>(false);

  const onSubmitLoginForm = async (e) => {
    setSubmitting(true);
    e.preventDefault();
    if (process.env.isStatic) {
      setSubmitting(false);
      const errors = {
        __all__:
          'The hunt has closed and teams can no longer register or log in.',
      };
      setLoginErrors(errors);
      return;
    }
    const data = new FormData(e.target);
    const resp = await clientFetch<DjangoFormResponse<LoginFormProps, void>>(
      router,
      '/login',
      { method: 'POST', body: data }
    );
    if (!resp?.form_errors) {
      onLoggedIn();
    } else {
      setLoginErrors(resp.form_errors);
    }
    setSubmitting(false);
  };

  const onSubmitResetPwForm = async (e) => {
    setSubmitting(true);
    e.preventDefault();
    const data = new FormData(e.target);
    const resp = await clientFetch<DjangoFormResponse<ResetPwForm, void>>(
      router,
      '/request_reset',
      { method: 'POST', body: data }
    );
    if (!resp?.form_errors) {
      setHasRequestedPwReset(true);
    } else {
      setResetPwErrors(resp.form_errors);
    }
    setSubmitting(false);
  };

  return (
    <>
      {isLogin ? (
        <div className="container">
          <Title removeMargin suppressPageTitle title="Log In" />

          <form onSubmit={onSubmitLoginForm}>
            <div className="form-group">
              <FormRow
                name="username"
                label="Team Username"
                required
                autofocus
                errors={loginErrors.username}
              />
              <FormRow
                name="password"
                label="Team Password"
                type="password"
                required
                errors={loginErrors.password}
              />
            </div>

            <div className="submit center">
              <button type="submit" disabled={isSubmitting}>
                Submit{isSubmitting ? 'ting' : ''}
              </button>
            </div>

            {loginErrors.__all__ && (
              <p className="formerror">{loginErrors.__all__}</p>
            )}
          </form>

          <div className="flex-center">
            <a onClick={() => void setIsLogin(false)}>Forgot your password?</a>
          </div>
        </div>
      ) : hasRequestedPwReset ? (
        <div>
          <h3>Password reset requested</h3>
          An email with instructions to reset your team's password has been sent
          to all email addresses registered to your team. If you are still
          having trouble logging into your account, please contact us at{' '}
          <HuntEmail />.
        </div>
      ) : (
        <div className="center">
          <h3>Forgot password?</h3>
          <form onSubmit={onSubmitResetPwForm}>
            {!process.env.isStatic && (
              <div className="form-group">
                <FormRow
                  name="username"
                  label="Team Username"
                  required
                  errors={resetPwErrors.username}
                />
              </div>
            )}

            <div className="submit center">
              <button type="submit" disabled={isSubmitting}>
                Submit{isSubmitting ? 'ting' : ''} request
              </button>
            </div>
            {resetPwErrors.__all__ && (
              <p className="formerror">{resetPwErrors.__all__}</p>
            )}

            <a onClick={() => setIsLogin(true)}>Back to login</a>
          </form>

          <p className="padTop">
            {process.env.isStatic ? (
              'The hunt has closed, and teams can no longer log in, but you may submit a password reset request if you want.'
            ) : (
              <>
                If you've forgotten your team's username, please contact us at{' '}
                <HuntEmail />.
              </>
            )}
          </p>
        </div>
      )}
      <style jsx>{`
        .container {
          display: flex;
          flex-direction: column;
          align-items: center;
          margin: 20px 8px 8px;
          height: 75%;
        }

        .container :global(h1) {
          font-size: 90px;
          line-height: 80px;
          margin-top: -40px;
        }

        .container :global(.subline) {
          margin: 0;
        }

        .form-group {
          display: grid;
          padding: 0 20px;
          justify-content: center;
          grid-template-columns: max-content 1fr;
          grid-gap: 0 12px;
          margin-bottom: 20px;
        }

        form > * {
          margin-top: 1em;
        }

        input {
          width: 100%;
        }

        .submit :global(h5) {
          font-size: 24px;
        }

        .padTop {
          margin-top: 2em;
        }

        @media (max-width: 550px) {
          .container {
            height: 60%;
            transform: scale(0.9);
          }

          .container :global(h1) {
            font-size: 50px;
            line-height: 50px;
          }
        }
      `}</style>
    </>
  );
};

export default LoginForm;
