import { FunctionComponent, useState } from 'react';
import dynamic from 'next/dynamic';
import { useRouter } from 'next/router';
const ReactTooltip = dynamic(() => import('react-tooltip'), {
  ssr: false,
});

import Title from 'components/title';
import { clientFetch } from 'utils/fetch';
import { DjangoFormResponse, DjangoFormErrors } from 'types';
import { FormRow } from 'components/form';

import { AlertCircle } from 'react-feather';

export interface TeamMembersForm {
  name1?: string;
  name2?: string;
  name3?: string;
  name4?: string;
  name5?: string;
  name6?: string;
  name7?: string;
  name8?: string;
  email1?: string;
  email2?: string;
  email3?: string;
  email4?: string;
  email5?: string;
  email6?: string;
  email7?: string;
  email8?: string;
}

interface RegisterForm extends TeamMembersForm {
  username?: string;
  team_name?: string;
  password1?: string;
  password2?: string;
}

const TEAM_MEMBER_NUMS = [1, 2, 3, 4, 5, 6, 7, 8];

export interface TeamMember {
  name: string;
  email?: string;
  rejected?: string;
}

export const TeamMemberFields: FunctionComponent<{
  members?: TeamMember[];
  showN?: number;
  errors: DjangoFormErrors<any>;
}> = ({ members = [], showN = 8, errors }) => (
  <>
    {TEAM_MEMBER_NUMS.slice(0, Math.max(showN, members?.length ?? 0)).map(
      (num) => {
        const required = num === 1;

        // a bit inelegant... but I didn't want to duplicate this block X times
        const nameError: string = errors[`name${num}`];
        const emailError: string = errors[`email${num}`];

        return (
          <div key={num} className="row">
            <div className="col-50 col-left form-group">
              <FormRow
                name={`name${num}`}
                label="Name"
                required={required}
                defaultValue={members[num - 1]?.name ?? ''}
                errors={nameError}
              />
            </div>

            <div className="col-50 col-right form-group">
              <FormRow
                name={`email${num}`}
                label="Email"
                type="email"
                required={required}
                defaultValue={members[num - 1]?.email ?? ''}
                errors={emailError}
              />
            </div>
            {(members[num - 1]?.rejected || null) && (
              <div>
                <div
                  className="rejected-email"
                  data-effect="solid"
                  data-place="top"
                  data-background-color="black"
                  data-multiline="true"
                  data-tip={
                    (members[num - 1]?.rejected === 'BOU'
                      ? `Emails to ${
                          members[num - 1]?.email ?? ''
                        } have bounced.`
                      : `${
                          members[num - 1]?.email ?? ''
                        } has unsubscribed from receiving emails.`) +
                    // FIXME: update email
                    ' Send an email to resubscribe@mypuzzlehunt.com from this address to resubscribe.'
                  }
                >
                  <AlertCircle />
                </div>
                <ReactTooltip />
              </div>
            )}
          </div>
        );
      }
    )}

    <style jsx>{`
      .form-group {
        box-sizing: border-box;
        display: grid;
        position: relative;
        justify-content: center;
        grid-template-columns: 20fr 75fr;
        grid-gap: 12px;
      }

      .col-50 {
        width: 50%;
      }

      .col-left {
        padding-right: 1em;
      }

      .col-right {
        padding-left: 1em;
      }

      .rejected-email {
        position: absolute;
        /* vertical padding should be sum of padding and border for input */
        padding: 5px 8px;
        color: red;
      }
      .rejected-email > :global(svg) {
        height: 16px;
        width: 16px;
      }
    `}</style>
  </>
);

const Register = ({ onRegister }) => {
  const router = useRouter();
  const [errors, setErrors] = useState<DjangoFormErrors<RegisterForm>>({});
  const [isSubmitting, setSubmitting] = useState<boolean>(false);
  const [showMoreTeammates, setShowMoreTeammates] = useState<boolean>(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setErrors({});
    setSubmitting(true);
    if (process.env.isStatic) {
      setSubmitting(false);
      const errors = {
        __all__:
          'The hunt has closed and teams can no longer register or log in.',
      };
      setErrors(errors);
      return;
    }
    const data = new FormData(e.target);
    setErrors({});
    const resp = await clientFetch<DjangoFormResponse<RegisterForm, void>>(
      router,
      '/register',
      {
        method: 'POST',
        body: data,
      }
    );
    if (!resp?.form_errors) {
      onRegister();
    } else {
      setErrors(resp.form_errors);
    }
    setSubmitting(false);
  };

  return (
    <div className="container">
      <Title removeMargin suppressPageTitle title="Register" />

      <form onSubmit={onSubmit}>
        <div className="form-group">
          <FormRow
            name="team_name"
            label="Team Name"
            errors={errors.team_name}
            required
            autofocus
          />
          <FormRow
            name="username"
            label="Team Username"
            errors={errors.username}
            required
          />
          <FormRow
            name="password1"
            label="Team Password"
            type="password"
            errors={errors.password1}
            required
          />
          <FormRow
            name="password2"
            label="Confirm Password"
            type="password"
            errors={errors.password2}
            required
          />
        </div>

        <h3 className="center small-caps">Teammates</h3>
        <div className="teammates">
          <TeamMemberFields errors={errors} showN={showMoreTeammates ? 8 : 4} />

          {!showMoreTeammates && (
            <a onClick={() => setShowMoreTeammates(true)}>Add more...</a>
          )}
        </div>

        <div className="submit center">
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Creating team...' : 'Submit!'}
          </button>
        </div>

        {errors.__all__ && <p className="formerror">{errors.__all__}</p>}
      </form>

      <style jsx>{`
        .container {
          position: relative;
          height: 100%;
          max-width: 720px;
          width: 100%;
        }

        .container :global(h1) {
          font-size: min(10vh, 120px);
          line-height: min(10vh, 120px);
          margin-top: 0;
        }

        form {
          font-size: 14px;
        }

        .form-group {
          display: grid;
          justify-content: center;
          grid-template-columns: max-content 1fr;
          grid-gap: 4px 12px;
        }

        form > * {
          width: 100%;
          margin-top: 1em;
        }

        .login {
          background: none;
          border: none;
          position: absolute;
          top: 125px;
          left: -24px;
          transform: rotate(-12deg);
        }

        h3 {
          margin-bottom: 0;
        }

        form .teammates {
          margin-top: 0;
          padding: 0 8px;
        }

        .teammates a {
          display: block;
          margin: 8px 0 -12px;
          text-align: right;
        }

        .submit :global(button) {
          margin-bottom: 12px;
        }

        .submit :global(h5) {
          font-size: 24px;
        }

        @media (max-width: 550px) {
          .container {
            transform: scale(0.9);
          }

          .container :global(h1) {
            font-size: 40px;
            line-height: 40px;
          }
        }
      `}</style>
    </div>
  );
};

export default Register;
