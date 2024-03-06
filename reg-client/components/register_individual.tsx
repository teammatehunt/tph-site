import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';

import { clientFetch } from 'utils/fetch';
import { FormRow } from 'components/form';
import { RegistrationClosed } from 'components/registration_closed';
import { RegistrationClosed as IndividualRegistrationClosed } from 'components/individual_registration_closed';
import { DjangoFormResponse, DjangoFormErrors } from 'types';
import HuntEmail from './hunt_email';

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

  if (!isLoggedIn) return <RegistrationClosed />;

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
              <Link href="/register">See our illustrious guests</Link>
              <Link href="/logout">Click here to log out</Link>
            </p>
          </span>
        </div>
      ) : (
        <>
          <p>
            This is the registration form for individual hunters, i.e.,
            currently unattached to a team. If you're part of a team already,
            you should have one of your team members sign up with the{' '}
            <Link href="/register-team">team registration form,</Link> not this
            one.
          </p>
          <IndividualRegistrationClosed />
        </>
      )}
    </>
  );
};

export default RegisterIndividual;
