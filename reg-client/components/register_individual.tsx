import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';

import { clientFetch } from 'utils/fetch';
import { FormRow } from 'components/form';
import { RegistrationClosed } from 'components/registration_closed';
import { RegistrationClosed as IndividualRegistrationClosed } from 'components/individual_registration_closed';
import { DjangoFormResponse, DjangoFormErrors } from 'types';
import HuntEmail from './hunt_email';

// TODO: Update to check hunt start date.
const IS_REGISTRATION_CLOSED = false;

// Represents a server.spoilr.registration.RegistrationInfo + user
interface RegisterIndividualForm {
  username?: string; // For user creation during initial registration only
  password1?: string; // For user creation during initial registration only
  password2?: string; // For user creation during initial registration only
  contact_first_name?: string;
  contact_last_name?: string;
  contact_pronouns?: string;
  contact_email?: string;
  bg_mh_history?: string;
  bg_other_history?: string;
  bg_playstyle?: string;
  bg_other_prefs?: string;
  bg_on_campus?: string;
  bg_under_18?: string;
  bg_mit_connection?: string;
  other?: string;
}

// Hook to await the loading of the logged-in user's registration info.
// Inspired by utils/assets.ts
// TODO: Dedupe this with team registration info hook.
export const useIndividualRegistrationInfo = (
  isLoggedIn: boolean
): {
  isLoading: boolean;
  registrationInfo: RegisterIndividualForm;
} => {
  const [isLoading, setLoading] = useState<boolean>(true);
  const [registrationInfo, setRegistrationInfo] =
    useState<RegisterIndividualForm>({});
  const router = useRouter();

  const loadRegistrationInfo = async () => {
    if (!isLoggedIn) {
      return;
    }
    const registrationInfo = await clientFetch<any>(
      router,
      '/register_individual',
      {
        method: 'GET',
      }
    );

    setRegistrationInfo(registrationInfo);
    setLoading(false);
  };

  useEffect(() => void loadRegistrationInfo(), [isLoggedIn]);

  if (!isLoggedIn) {
    return { isLoading: false, registrationInfo: {} };
  }

  return {
    isLoading,
    registrationInfo,
  };
};

const RegisterIndividual = ({
  isLoggedIn,
  huntStarted,
}: {
  isLoggedIn: boolean;
  huntStarted: boolean;
}) => {
  const router = useRouter();
  const [errors, setErrors] = useState<
    DjangoFormErrors<RegisterIndividualForm>
  >({});
  const [isSubmitting, setSubmitting] = useState<boolean>(false);
  const { isLoading, registrationInfo } =
    useIndividualRegistrationInfo(isLoggedIn);

  const onSubmit = async (e) => {
    e.preventDefault();
    setErrors({});
    setSubmitting(true);
    if (process.env.isStatic) {
      setSubmitting(false);
      const errors = {
        __all__: 'Hunt has closed and you can no longer register or log in.',
      };
      setErrors(errors);
      return;
    }
    const data = new FormData(e.target);
    setErrors({});

    try {
      const resp = await clientFetch<
        DjangoFormResponse<RegisterIndividualForm, void>
      >(router, '/register_individual', {
        method: 'POST',
        body: data,
      });

      if (!resp?.form_errors) {
        router.push('/register-individual');
      } else {
        setErrors({
          __all__:
            'There were errors with some submitted fields; please correct them and try again.',
          ...resp.form_errors,
        });
      }
    } catch (e) {
      setErrors({
        __all__:
          "Sorry, we encountered an internal error and couldn't process your registration. Please reach out to Hunt staff directly for help.",
      });
    } finally {
      setSubmitting(false);
    }
  };

  if (!isLoggedIn && IS_REGISTRATION_CLOSED) return <RegistrationClosed />;

  return (
    <>
      {isLoggedIn ? (
        <div className="bg-off-white p-6">
          <span className="space-y-4">
            <p>Thanks for your interest in FIXME HUNT! What's next:</p>
            <p>
              You should have received an confirmation email to the address you
              initially provided.
            </p>
            <p>
              If we're able to match you with a willing team, we'll let you know
              via your last-provided email address before Hunt starts.
            </p>
            <p>
              You can modify this form at any time by logging in with your
              username and password.
            </p>
            <p className="flex md:space-x-8">
              <Link href="/register">
                <a>See our illustrious guests</a>
              </Link>
              <Link href="/logout">
                <a>Click here to log out</a>
              </Link>
            </p>
          </span>
        </div>
      ) : (
        <>
          <p>
            This is the registration form for individual hunters, i.e.,
            currently unattached to a team. If you're part of a team already,
            you should have one of your team members sign up with the{' '}
            <Link href="/register-team">
              <a>team registration form,</a>
            </Link>{' '}
            not this one.
          </p>
          {IS_REGISTRATION_CLOSED ? (
            <IndividualRegistrationClosed />
          ) : (
            <p>
              You only need to fill out required fields (
              <span className="text-red-500">*</span>) at minimum, and you will
              have an opportunity to provide updated information in the future
              by logging in. You can omit any questions whose answers you don't
              know yet or just fill them in to the best of your ability.
            </p>
          )}
        </>
      )}
      {!IS_REGISTRATION_CLOSED && (
        <>
          <p>
            If you have further questions about registration, feel free to email
            us at <HuntEmail />.
          </p>
          <form
            onSubmit={onSubmit}
            onKeyDown={(e) => {
              // Disable Enter from submitting form by accident
              if (e.code === 'Enter') e.preventDefault();
            }}
          >
            {isLoading ? (
              <div>Loading your registration…</div>
            ) : (
              <div className="flex flex-col space-y-16">
                <section>
                  <FormRow
                    name="contact_first_name"
                    label="First (Given) name"
                    errors={errors.contact_first_name}
                    defaultValue={registrationInfo?.contact_first_name}
                    required
                    autofocus={!isLoggedIn}
                  />
                  <FormRow
                    name="contact_last_name"
                    label="Last (Family) name"
                    errors={errors.contact_last_name}
                    defaultValue={registrationInfo?.contact_last_name}
                    required
                  />
                  <FormRow
                    name="contact_email"
                    label="Email address"
                    errors={errors.contact_email}
                    defaultValue={registrationInfo?.contact_email}
                    required
                  />

                  {!isLoggedIn && (
                    <>
                      <FormRow
                        name="username"
                        label="Username"
                        info="Only for editing your registration. If we're able to match you with a team, the team will have a shared username and password for accessing Hunt."
                        errors={errors.username}
                        required
                      />
                      <FormRow
                        name="password1"
                        label="Password"
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
                    </>
                  )}
                </section>

                <section>
                  <h3>Background</h3>
                  <div>
                    Help us understand your preferences so we can match you with
                    a team better.
                  </div>
                  <FormRow
                    name="bg_mh_history"
                    label="Have you participated in the MIT Mystery Hunt before? If so, tell us about your Hunt history!"
                    info="(500 character limit)"
                    lines={3}
                    defaultValue={registrationInfo?.bg_mh_history}
                    errors={errors.bg_mh_history}
                  />
                  <FormRow
                    name="bg_other_history"
                    label="Have you played in other puzzle-type events before? If so, tell us about it!"
                    info="(500 character limit)"
                    lines={3}
                    defaultValue={registrationInfo?.bg_other_history}
                    errors={errors.bg_other_history}
                  />
                  <FormRow
                    name="bg_playstyle"
                    label="What describes your style of playing?"
                    options={{
                      fun: "I'm just playing for fun and would like to make some new friends.",
                      puzzles:
                        "I'm pretty into puzzles, but not so focused on winning.",
                      win: "I'm a puzzle machine, and I'd love to be on a team that wants to find the coin. I really want to see all of Hunt.",
                    }}
                    defaultValue={registrationInfo?.bg_playstyle}
                    errors={errors.bg_playstyle}
                  />
                  <FormRow
                    name="bg_other_prefs"
                    label="Do you have any other preferences about what team you want to join?"
                    info="For example, larger or smaller teams, teams of current students or alumni/older players, etc."
                    defaultValue={registrationInfo?.bg_other_prefs}
                    errors={errors.bg_other_prefs}
                  />
                  <FormRow
                    name="bg_on_campus"
                    label="Do you plan to participate on campus?"
                    options={{
                      yes: "Yes, I'll be on campus",
                      maybe: 'Maybe',
                      no: "No, I'll participate remotely",
                    }}
                    defaultValue={registrationInfo?.bg_on_campus}
                    errors={errors.bg_on_campus}
                  />
                  <FormRow
                    name="bg_under_18"
                    label="Are you under 18?"
                    info="Note: Non-MIT minors must be accompanied by a parent or guardian at all times, and may not attend kickoff, events, interactions away from their team’s HQ, or field puzzles."
                    options={{
                      yes: 'Yes',
                      no: 'No',
                    }}
                    defaultValue={registrationInfo?.bg_under_18}
                    errors={errors.bg_under_18}
                  />
                  <FormRow
                    name="bg_mit_connection"
                    label="Are you connected to the MIT community? If so, how?"
                    defaultValue={registrationInfo?.bg_mit_connection}
                    errors={errors.bg_mit_connection}
                  />
                  <FormRow
                    name="other"
                    label="Anything else you'd like to share with us?"
                    info="Comments, questions, puns?"
                    lines={3}
                    defaultValue={registrationInfo?.other}
                    errors={errors.other}
                  />
                </section>

                <div className="submit text-center">
                  <button type="submit" disabled={isSubmitting}>
                    {isLoggedIn ? 'Update registration' : 'Submit'}
                  </button>
                </div>

                {errors.__all__ && (
                  <p className="formerror">{errors.__all__}</p>
                )}
              </div>
            )}
          </form>
        </>
      )}
    </>
  );
};

export default RegisterIndividual;
