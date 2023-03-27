import Link from 'next/link';
import cx from 'classnames';

import Accordion from 'components/accordion';
import RegistrationPageBase from 'components/content_page_base';
import {
  ItemHeading,
  sectionHeadingClassName,
  SubsectionHeading,
} from 'components/headings';
import imgFaqSplash from 'assets/public/campus.jpeg';
import HuntEmail from 'components/hunt_email';

const KnowBeforeYouGoItem = ({
  icon,
  content,
}: {
  icon: React.ReactNode;
  content: React.ReactNode;
}) => (
  <div className="flex flex-row space-x-4 items-center">
    <div className="min-w-[80px] text-right">{icon}</div>
    <div>{content}</div>
  </div>
);

// "ticket" icon from heroicons
const SvgTicket = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    fill="none"
    viewBox="0 0 24 24"
    strokeWidth={0.6}
    stroke="currentColor"
    className="w-16 h-16"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M16.5 6v.75m0 3v.75m0 3v.75m0 3V18m-9-5.25h5.25M7.5 15h3M3.375 5.25c-.621 0-1.125.504-1.125 1.125v3.026a2.999 2.999 0 010 5.198v3.026c0 .621.504 1.125 1.125 1.125h17.25c.621 0 1.125-.504 1.125-1.125v-3.026a2.999 2.999 0 010-5.198V6.375c0-.621-.504-1.125-1.125-1.125H3.375z"
    />
  </svg>
);

// "shield-check" icon from heroicons
const SvgShield = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    fill="none"
    viewBox="0 0 24 24"
    strokeWidth={0.6}
    stroke="currentColor"
    className="w-16 h-16"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
    />
  </svg>
);

// "users" icon from heroicons
const SvgPeople = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    fill="none"
    viewBox="0 0 24 24"
    strokeWidth={0.6}
    stroke="currentColor"
    className="w-16 h-16"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z"
    />
  </svg>
);

// "building-library" icon from heroicons
const SvgBuilding = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    fill="none"
    viewBox="0 0 24 24"
    stroke-width={0.6}
    stroke="currentColor"
    className="w-16 h-16"
  >
    <path
      stroke-linecap="round"
      stroke-linejoin="round"
      d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.36 48.36 0 0012 9.75c-2.551 0-5.056.2-7.5.582V21M3 21h18M12 6.75h.008v.008H12V6.75z"
    />
  </svg>
);

const Faq = () => {
  return (
    <RegistrationPageBase title="FIXME HUNT - FAQ">
      <section>
        {/* Image max height is 70% of the viewport height on larger screens, clipping the top and bottom */}
        {/* Image min height is 100% of the viewport height on smaller screens, clipping the sides */}
        <div className="absolute flex justify-center w-full h-screen lg:h-[70vh]">
          <img
            className="object-cover justify-center w-full brightness-50"
            src={imgFaqSplash}
          />
        </div>
        <div className="relative flex h-screen lg:h-[70vh] items-center text-white mx-auto w-full lg:w-[50vw] px-4 sm:px-8">
          <div className="flex flex-col space-y-6">
            <span className={cx('text-5xl', sectionHeadingClassName)}>
              Plan your visit
            </span>
            <span>
              <p>77 Massachusetts Avenue</p>
              <p>Cambridge, MA 02139</p>
            </span>
            <h3 className="text-white">Opening hours</h3>
            <span>
              <p>Open: 12:00 pm ET, Friday January 13, 2023</p>
              <p>Close: 6:00 pm ET, Sunday January 15, 2023</p>
              <p>Wrap-Up: 12:00 pm ET, Monday January 16, 2023</p>
            </span>
          </div>
        </div>
      </section>

      <section className="px-4 py-24 bg-off-white w-full">
        <div className="mx-auto max-w-[90%] lg:w-[50vw] space-y-16">
          <SubsectionHeading>Know before you go</SubsectionHeading>
          <div className="space-y-8">
            <KnowBeforeYouGoItem
              icon={<SvgTicket />}
              content={
                <>
                  <Link href="/register">
                    <a>Reserve tickets</a>
                  </Link>{' '}
                  before December 31 to guarantee your spot.
                </>
              }
            />
            <KnowBeforeYouGoItem
              icon={<SvgShield />}
              content={
                <>
                  Masks are currently recommended but not required. See the FAQ
                  below for more information on how we’re keeping everyone safe.
                </>
              }
            />
            <KnowBeforeYouGoItem
              icon={<SvgPeople />}
              content={
                <>
                  The Museum of Interesting Things is best enjoyed with up to 60
                  friends. Looking for a group to go with?{' '}
                  <Link href="/register-individual">
                    <a>Let us know,</a>
                  </Link>{' '}
                  and we’ll find you a group to join.
                </>
              }
            />
            <KnowBeforeYouGoItem
              icon={<SvgBuilding />}
              content={
                <>
                  As a guest, you will have access to our buildings from 6am –
                  1am ET, so you can make the most out of your visit.
                </>
              }
            />
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-[90%] lg:w-[50vw] px-4 py-24 space-y-16">
        <SubsectionHeading>Frequently asked questions</SubsectionHeading>

        <div className="space-y-2">
          <Accordion heading="What is all this?">
            <p className="text-lg">
              This is where your team can register for the 2023 MIT Mystery
              Hunt! See the{' '}
              <a href="https://puzzles.mit.edu/">Mystery Hunt website</a> for
              more background and history about the Hunt.
            </p>
          </Accordion>

          <Accordion heading="Will Mystery Hunt take place at MIT?">
            <p className="text-lg">
              Yes! We are actively working with MIT admin and Puzzle Club to
              host this large-scale event, with MIT’s new campus policies.{' '}
            </p>
          </Accordion>

          <Accordion heading="What are Mystery Hunt’s COVID policies?">
            <p className="text-lg">
              Per MIT policy, masks are currently recommended but not required.
              Prior to arriving on campus, as part of the Tim Ticket process,
              attendees will be asked to attest to being fully vaccinated and
              boosted or to having a religious belief or medical condition that
              prevents them from receiving the vaccine.
            </p>
          </Accordion>

          <Accordion heading="How will campus access work at this year’s Hunt?">
            <p className="text-lg">
              Prior to Hunt, we will distribute an online form for each
              non-MIT-affiliated on-campus participant to acquire a QR code
              known as a Tim Ticket. A valid MIT ID or Tim Ticket will be
              required to access the MIT campus. Hunt participants will also be
              required to wear badges (distributed to team captains at kickoff)
              for the duration of the event. Due to MIT policy, campus will be
              closed from 1am to 6am each night.
            </p>
          </Accordion>

          <Accordion heading="Will there be hotel blocks for Mystery Hunt this year?">
            <p className="text-lg">
              Yes! Please see the <a href="/#updates">Updates</a> section on the
              homepage for details.
            </p>
          </Accordion>

          <Accordion heading="Are minors allowed on campus?">
            <p className="text-lg">
              Non-MIT minors must be accompanied by a parent or guardian at all
              times, and may not attend kickoff, events, interactions away from
              their team’s HQ, or field puzzles.
            </p>
          </Accordion>

          <Accordion heading="Can teams participate without an on-campus presence?">
            <p>
              You are welcome to solve as a fully remote team! We are making our
              best effort to provide a great experience for remote teams. That
              said, there will be some puzzles where being in-person will be
              helpful, and in select cases, potentially required. Remote teams
              will still be able to finish Hunt.
            </p>
          </Accordion>

          <Accordion heading="How much does Mystery Hunt cost?">
            <p className="text-lg">
              It's free to participate and the event is open to everyone! That
              said, Mystery Hunt costs approximately $10 per person to run, and
              we welcome donations to offset the costs for everything that goes
              into running Hunt. If you would like to donate to the Mystery Hunt
              fund, you can go to{' '}
              <a
                href="https://giving.mit.edu/form/?fundId=2720842"
                target="_blank"
              >
                MIT Giving
              </a>
              .
            </p>
          </Accordion>

          <Accordion heading="Other questions?">
            <p className="text-lg">
              Please feel free to email us at <HuntEmail /> with any additional
              questions.
            </p>
          </Accordion>
        </div>
      </section>
    </RegistrationPageBase>
  );
};

export default Faq;
