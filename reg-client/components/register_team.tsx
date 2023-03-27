import { useContext, useEffect, useState } from 'react';
import { useRouter } from 'next/router';

import { clientFetch } from 'utils/fetch';
import { DjangoFormResponse, DjangoFormErrors } from 'types';
import { FormRow } from 'components/form';
import { RegistrationClosed } from 'components/registration_closed';
import Link from 'next/link';
import HuntEmail from './hunt_email';

// Represents a server.spoilr.registration.RegistrationInfo + user
interface RegisterTeamForm {
  username?: string; // For user creation during initial registration only
  password1?: string; // For user creation during initial registration only
  password2?: string; // For user creation during initial registration only
  team_name?: string;
  contact_name?: string;
  contact_pronouns?: string;
  contact_email?: string;
  contact_phone?: string;
  bg_bio?: string;
  bg_emails?: string;
  bg_playstyle?: string;
  bg_win?: string;
  bg_started?: string;
  bg_location?: string;
  bg_comm?: string;
  bg_on_campus?: string;
  tb_room?: string;
  tb_room_specs?: string;
  tb_location?: string;
  tm_total?: string;
  tm_last_year_total?: string;
  tm_undergrads?: string;
  tm_grads?: string;
  tm_alumni?: string;
  tm_faculty?: string;
  tm_other?: string;
  tm_minors?: string;
  tm_onsite?: string;
  tm_offsite?: string;
  other_unattached?: string;
  other_workshop?: string;
  other_puzzle_club?: string;
  other_how?: string;
  other?: string;
}

// Hook to await the loading of the logged-in team's registration info.
// Inspired by utils/assets.ts
export const useTeamRegistrationInfo = (
  loggedInSlug: string | undefined
): { isLoading: boolean; registrationInfo: RegisterTeamForm } => {
  const [isLoading, setLoading] = useState<boolean>(true);
  const [registrationInfo, setRegistrationInfo] = useState<RegisterTeamForm>(
    {}
  );
  const router = useRouter();

  const loadRegistrationInfo = async () => {
    if (!loggedInSlug) {
      return;
    }

    const registrationInfo = await clientFetch<any>(
      router,
      '/register/' + loggedInSlug,
      {
        method: 'GET',
      }
    );

    setRegistrationInfo(registrationInfo);
    setLoading(false);
  };

  useEffect(() => void loadRegistrationInfo(), [loggedInSlug]);

  if (!loggedInSlug) {
    return { isLoading: false, registrationInfo: {} };
  }

  return {
    isLoading,
    registrationInfo,
  };
};

const RegisterTeam = ({
  loggedInSlug,
  huntStarted,
}: {
  loggedInSlug: string | undefined;
  huntStarted: boolean;
}) => {
  const router = useRouter();
  const [errors, setErrors] = useState<DjangoFormErrors<RegisterTeamForm>>({});
  const [isSubmitting, setSubmitting] = useState<boolean>(false);
  const { isLoading, registrationInfo } = useTeamRegistrationInfo(loggedInSlug);

  const onSubmit = async (e) => {
    e.preventDefault();
    setErrors({});
    setSubmitting(true);
    if (process.env.isStatic) {
      setSubmitting(false);
      const errors = {
        __all__: 'Hunt has closed and teams can no longer register or log in.',
      };
      setErrors(errors);
      return;
    }
    const data = new FormData(e.target);
    setErrors({});

    try {
      let path: string;
      if (loggedInSlug) {
        // If logged in, treat this as a team edit operation.
        // Users should be able to edit all fields except for team username and password.
        path = '/register/' + loggedInSlug;
      } else {
        // If not logged in, treat this as a new signup.
        path = '/register';
      }
      const resp = await clientFetch<
        DjangoFormResponse<RegisterTeamForm, void>
      >(router, path, {
        method: 'POST',
        body: data,
      });

      if (!resp?.form_errors) {
        router.push('/register-team');
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

  if (!loggedInSlug) return <RegistrationClosed />;

  return (
    <>
      {loggedInSlug ? (
        <div className="bg-off-white p-6">
          <span className="space-y-4">
            <p>You're signed up for FIXME HUNT! What's next:</p>
            <p>
              You should have received an email to the primary contact's email
              address confirming your registration.
            </p>
            <p>
              Let your teammates know the team username and team password you've
              chosen! You and your teammates will use this to log in when Hunt
              starts.
            </p>
            <p>
              Anyone with the team username and team password can also modify
              your team's registration at any time until Hunt starts.
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
            This is the registration form for the FIXME HUNT. Please have only
            one person on your team fill this form out!
          </p>
          <p>
            You only need to fill out required fields (
            <span className="text-red-500">*</span>) at minimum to create your
            team, and you will have an opportunity to provide updated
            information in the future by logging in. You can omit any questions
            whose answers you don't know yet or just fill them in to the best of
            your ability.
          </p>
        </>
      )}
      <p>
        If you have further questions about registration, feel free to email us
        at <HuntEmail />.
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
                name="team_name"
                label="Team Name"
                info="Your team's public name, which will be visible on the guest list"
                errors={errors.team_name}
                defaultValue={registrationInfo?.team_name}
                required
                autofocus={!loggedInSlug}
              />
              {!loggedInSlug && (
                <>
                  <FormRow
                    name="username"
                    label="Team Username"
                    info="Only members of your team will use this to log in"
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
                </>
              )}
              <FormRow
                name="bg_bio"
                label="Team Bio"
                info="About your team (280-character limit; will be visible publicly)"
                lines={3}
                defaultValue={registrationInfo?.bg_bio}
                errors={errors.bg_bio}
              />
              <FormRow
                name="bg_emails"
                label="Team-wide Email List"
                info="Mailing list that only members of your team have access to, for receiving hunt-wide announcements"
                placeholder="example-group@mit.edu"
                defaultValue={registrationInfo?.bg_emails}
                errors={errors.bg_emails}
              />
            </section>

            <section>
              <h3>Primary contact</h3>
              <div>
                Mystery Hunt staff needs contact details of one person
                designated as the primary contact, just in case we need to talk
                to someone on your team directly.
              </div>
              <FormRow
                name="contact_name"
                label="Name"
                defaultValue={registrationInfo?.contact_name}
                errors={errors.contact_name}
                required
              />
              <FormRow
                name="contact_pronouns"
                label="Pronouns"
                defaultValue={registrationInfo?.contact_pronouns}
                errors={errors.contact_pronouns}
              />
              <FormRow
                name="contact_email"
                label="Email"
                placeholder="jdoe@mit.edu"
                defaultValue={registrationInfo?.contact_email}
                errors={errors.contact_email}
                required
              />
              <FormRow
                name="contact_phone"
                label="Phone Number"
                placeholder="1234567890"
                defaultValue={registrationInfo?.contact_phone}
                errors={errors.contact_phone}
                required
              />
            </section>

            <section>
              <h3>Team background</h3>
              <div>Help us understand your team better.</div>
              <FormRow
                name="bg_playstyle"
                label="What describes your team's style of playing?"
                options={{
                  fun: 'We’re playing for fun!',
                  puzzles:
                    'We’re pretty into puzzles but we’re not so focused on winning.',
                  win: 'We’re serious about solving. We really want to see the entire Hunt and maybe find the coin.',
                }}
                defaultValue={registrationInfo?.bg_playstyle}
                errors={errors.bg_playstyle}
              />
              <FormRow
                name="bg_win"
                label="Is your team aiming to win Hunt?"
                options={{
                  yes: 'Yes (🤞)',
                  no: 'No',
                  unsure: 'Unsure',
                }}
                defaultValue={registrationInfo?.bg_win}
                errors={errors.bg_win}
              />
              <FormRow
                name="bg_started"
                label="When was your team established?"
                defaultValue={registrationInfo?.bg_started}
                errors={errors.bg_started}
              />
              <FormRow
                name="bg_location"
                label="What cities or metropolitan areas will you have teammates in during Hunt?"
                info="If you have a large or dispersed team, just list the main ones"
                defaultValue={registrationInfo?.bg_location}
                errors={errors.bg_location}
              />
              <FormRow
                name="bg_comm"
                label="What communication application will your team be using to communicate during Hunt?"
                defaultValue={registrationInfo?.bg_comm}
                errors={errors.bg_comm}
              />
              <FormRow
                name="bg_on_campus"
                label="Does your team plan to have an on-campus presence this year?"
                options={{
                  yes: 'Yes, we will have team members on campus',
                  no: 'No, we will be hunting remotely only',
                }}
                defaultValue={registrationInfo?.bg_on_campus}
                errors={errors.bg_on_campus}
              />
            </section>

            <section>
              <h3>Team base</h3>
              <div>
                <strong>Note:</strong> Due to MIT policy, teams will no longer
                be allowed to solve in classrooms on campus from 1am to 6am each
                night.
              </div>
              <FormRow
                name="tb_room"
                label="What space will your team use as a team base?"
                info="If you need a classroom to use as a team base, you may request a room through this form by December 15."
                options={{
                  no: 'We already have a team base at or near MIT',
                  no_remote: 'We will be hunting remotely only',
                  maybe:
                    'We would like a classroom as a team base, but we have a backup plan in case Hunt is unable to secure a room',
                  yes: 'We absolutely need a classroom as a team base',
                }}
                defaultValue={registrationInfo?.tb_room}
                errors={errors.tb_room}
                required
              />
              <FormRow
                name="tb_room_specs"
                label="If you are requesting a room, what specifications would you like for your team base?"
                info="For example, specific rooms or room attributes. Please also indicate whether you expect your team to use this team base in the evenings, between 6pm and 1am."
                lines={3}
                defaultValue={registrationInfo?.tb_room_specs}
                errors={errors.tb_room_specs}
              />
              <FormRow
                name="tb_location"
                label="If you are not requesting a classroom, where is your team base? Do we need any special instructions to access your HQ?"
                info="If remote, please provide instructions for how we can contact you virtually (e.g. Zoom link, Discord server, Google Meet, etc.)"
                lines={3}
                defaultValue={registrationInfo?.tb_location}
                errors={errors.tb_location}
              />
            </section>

            <section>
              <h3>Team composition</h3>
              <div>
                Each year, the Mystery Hunt writing team must have at least two
                current MIT undergraduate or graduate students to effectively
                organize on-campus logistics. In order to facilitate this, teams
                anticipating having a chance of winning the Hunt are strongly
                encouraged to have at least two student members.
              </div>
              {/* Note that unfilled numerical fields come back as null, but React prefers empty strings over null */}
              <FormRow
                name="tm_total"
                label="How many people are in your team in total?"
                type="number"
                defaultValue={registrationInfo?.tm_total ?? ''}
                errors={errors.tm_total}
                min={0}
              />
              <FormRow
                name="tm_onsite"
                label="How many people will your team have on campus?"
                type="number"
                defaultValue={registrationInfo?.tm_onsite ?? ''}
                errors={errors.tm_onsite}
                min={0}
              />
              <FormRow
                name="tm_last_year_total"
                label="How many people were on your team last year?"
                type="number"
                defaultValue={registrationInfo?.tm_last_year_total ?? ''}
                errors={errors.tm_last_year_total}
                min={0}
              />
              <FormRow
                name="tm_undergrads"
                label="How many MIT undergraduates?"
                type="number"
                defaultValue={registrationInfo?.tm_undergrads ?? ''}
                errors={errors.tm_undergrads}
                min={0}
              />
              <FormRow
                name="tm_grads"
                label="How many MIT graduate students?"
                type="number"
                defaultValue={registrationInfo?.tm_grads ?? ''}
                errors={errors.tm_grads}
                min={0}
              />
              <FormRow
                name="tm_alumni"
                label="How many MIT alumni?"
                type="number"
                defaultValue={registrationInfo?.tm_alumni ?? ''}
                errors={errors.tm_alumni}
                min={0}
              />
              <FormRow
                name="tm_faculty"
                label="How many members from MIT faculty and staff?"
                type="number"
                defaultValue={registrationInfo?.tm_faculty ?? ''}
                errors={errors.tm_faculty}
                min={0}
              />
              <FormRow
                name="tm_other"
                label="How many people are not affiliated with MIT?"
                type="number"
                defaultValue={registrationInfo?.tm_other ?? ''}
                errors={errors.tm_other}
                min={0}
              />
              <FormRow
                name="tm_minors"
                label="How many minors (age under 18) participating?"
                info="Note: Non-MIT minors must be accompanied by a parent or guardian at all times, and may not attend kickoff, events, interactions away from their team’s HQ, or field puzzles."
                type="number"
                defaultValue={registrationInfo?.tm_minors ?? ''}
                errors={errors.tm_minors}
                min={0}
              />
            </section>

            <section>
              <h3>Other information</h3>
              <FormRow
                name="other_unattached"
                label='We’re inviting new solvers to sign up as "unattached hunters" so we can match them to teams with similar playstyles. Is your team willing to accept unattached hunters?'
                options={{
                  yes: 'Yes',
                  no: 'No',
                }}
                defaultValue={registrationInfo?.other_unattached}
                errors={errors.other_unattached}
              />
              <FormRow
                name="other_workshop"
                label="Would your team like to participate in the How to Hunt workshop before the event?"
                options={{
                  yes: 'Yes',
                  no: 'No',
                }}
                defaultValue={registrationInfo?.other_workshop}
                errors={errors.other_workshop}
              />
              <FormRow
                name="other_puzzle_club"
                label="Does your team have a member that would like to be involved in ongoing puzzle organization at MIT?"
                info="For example, sending an MIT student as a representative to join the Puzzle Club student activity group"
                options={{
                  yes: 'Yes',
                  no: 'No',
                  already:
                    'We already have someone from Puzzle Club on the team',
                }}
                defaultValue={registrationInfo?.other_puzzle_club}
                errors={errors.other_puzzle_club}
              />
              <FormRow
                name="other_how"
                label="How did you hear about the MIT Mystery Hunt?"
                options={{
                  past: 'We’ve played in the past',
                  group:
                    'Through a puzzle interest group (e.g. National Puzzlers’ League)',
                  'word-of-mouth':
                    'Word of mouth from past participants or organizers',
                  social: 'Through e-mail or social media',
                  'puzzle-club': 'Through the MIT Puzzle Club',
                  other: 'Other',
                }}
                defaultValue={registrationInfo?.other_how}
                errors={errors.other_how}
              />
              <FormRow
                name="other"
                label="Anything else you’d like to share with us?"
                info="Comments, questions, puns?"
                lines={3}
                errors={errors.other}
              />
            </section>
            <div>
              Putting on a world-class puzzle event is expensive.{' '}
              <a
                href="https://giving.mit.edu/give/to?fundId=2720842"
                target="_blank"
              >
                Is your team interested in making a tax-deductible donation to
                help defray the costs (opens in a new tab)?
              </a>
            </div>

            <div className="submit text-center">
              <button type="submit" disabled={isSubmitting}>
                {loggedInSlug ? 'Update registration' : 'Submit'}
              </button>
            </div>

            {errors.__all__ && <p className="formerror">{errors.__all__}</p>}
          </div>
        )}
      </form>
    </>
  );
};

export default RegisterTeam;
