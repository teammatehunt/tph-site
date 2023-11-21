import React, { useContext, useState } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import Router, { useRouter } from 'next/router';

import HuntInfoContext from 'components/context';
import { Countdown } from 'components/countdown';
import Header from 'components/header';
import Footer from 'components/footer';
import {
  displayTime,
  formattedDateTime,
  getTimeLeft,
  TimeConfig,
  pluralize,
} from 'utils/timer';
import cx from 'classnames';
import imgSplash from 'assets/public/splash.jpeg';
import imgHighlight1 from 'assets/public/curated-collection.jpeg';
import imgHighlight2 from 'assets/public/marble-head.jpeg';
import imgHighlight3 from 'assets/public/kresge.jpeg';
import {
  ItemHeading,
  SectionHeading,
  sectionHeadingClassName,
  SubsectionHeading,
} from 'components/headings';

const CountdownField = ({ number, unit }) => (
  <div className="flex flex-row items-center stify-center space-x-4 md:flex-col w-28 xl:w-36">
    <div className="text-8xl xl:text-9xl font-black">{number}</div>
    <span>{unit}</span>
  </div>
);

const displayTimeLeftBig = (
  tick: number,
  fps: number,
  options: TimeConfig = {}
) => {
  const [days, hours, minutes, seconds] = getTimeLeft(tick, fps, options);
  const { showHours = false, showDays = false } = options;

  return (
    <div className="flex flex-col md:flex-row md:space-x-16">
      {showDays && (
        <span suppressHydrationWarning>
          <CountdownField number={days} unit={pluralize(days, ' day')} />
        </span>
      )}
      {showHours && (
        <span>
          <CountdownField
            number={displayTime(hours, 2)}
            unit={pluralize(hours, ' hour')}
          />
        </span>
      )}

      <span suppressHydrationWarning>
        <CountdownField number={displayTime(minutes, 2)} unit={' min'} />
      </span>

      <span suppressHydrationWarning>
        <CountdownField number={displayTime(seconds, 2)} unit={' sec'} />
      </span>
    </div>
  );
};

const HuntCountdown = () => {
  const { huntInfo } = useContext(HuntInfoContext);
  // Note that hunt info is calculated once at site load, so this state only
  // changes if someone is viewing the page at expiration time
  const [expired, setExpired] = useState(huntInfo.secondsToStartTime <= 0);
  const router = useRouter();
  let huntLink = '/hunt';
  if (process.env.isArchive) {
    // the redirect set by /hunt doesn't allow for paths outside the basePath
    // so we have to skip the server side redirect
    huntLink = '/20xx/mypuzzlehunt.com';
  }
  return (
    <>
      <div className="w-full">
        <span className={sectionHeadingClassName}>
          The museum{' '}
          <span className="whitespace-nowrap">
            {expired ? 'is open!' : 'opens in'}
          </span>
        </span>
        <Countdown
          seconds={huntInfo.secondsToStartTime}
          textOnCountdownFinish={
            <div className="pt-9">
              <a href={huntLink} className="button-link button-link-white">
                Enter →
              </a>
            </div>
          }
          countdownFinishCallback={() => {
            setExpired(true);
          }}
          showHours
          render={displayTimeLeftBig}
        />
      </div>
    </>
  );
};

const Splash = () => {
  const { huntInfo } = useContext(HuntInfoContext);
  const splashSizeClass = 'justify-center h-screen';
  return (
    <section>
      {/* Background */}
      {/* Color matches the background of the image, which is not perfectly black */}
      <div
        className={`absolute flex ${splashSizeClass} z-[1] w-full bg-[#080609] z-[1]`}
      ></div>
      {/* Splash image */}
      {/* At small sizes, text overlays it and image is darker for contrast */}
      {/* At larger sizes, image is on opposing side */}
      <div
        className={`relative ${splashSizeClass} lg:flex lg:flex-row lg:px-[10vw]`}
      >
        {/* Countdown text */}
        <div
          className={`absolute flex ${splashSizeClass} z-[3] w-full px-6 items-center text-white lg:relative lg:px-0 lg:w-3/4`}
        >
          <HuntCountdown />
        </div>
        <div
          className={`absolute flex ${splashSizeClass} z-[2] w-full brightness-[70%] lg:relative lg:w-1/2 lg:-ml-60`}
        >
          <img
            className="object-cover justify-center max-h-screen lg:object-contain"
            src={imgSplash}
            alt=""
          />
        </div>
      </div>
    </section>
  );
};

const HighlightEntry = ({ imgSrc, children, ...props }) => {
  return (
    <div className="flex flex-col space-y-2 p-6 pt-12 md:py-24 max-w-full min-w-full md:max-w-[33%] md:min-w-[33%]">
      <img src={imgSrc} className="mb-6" {...props} />
      {children}
    </div>
  );
};

const Highlights = () => {
  return (
    <section className="pb-6 pt-12 md:pb-12 md:pt-24">
      <SubsectionHeading>Highlights</SubsectionHeading>
      <div className="flex flex-wrap max-w-[90%] md:max-w-full lg:max-w-[80%] mx-auto md:place-content-between">
        <HighlightEntry imgSrc={imgHighlight1} aria-labelledBy="collection">
          <ItemHeading id="collection">A world-class collection</ItemHeading>
          <p>
            For the last forty years, we've been curating a world-class
            collection that is sure to astound.
          </p>
        </HighlightEntry>
        <HighlightEntry imgSrc={imgHighlight2} aria-labelledBy="exhibits">
          <ItemHeading id="exhibits">Explore our new exhibits</ItemHeading>
          <p>
            Artistic masterpieces and historical artifacts will keep you busy
            the whole weekend.
          </p>
        </HighlightEntry>
        <HighlightEntry imgSrc={imgHighlight3} aria-labelledBy="celebrate">
          <ItemHeading id="celebrate">Celebrate with us</ItemHeading>
          <p>
            Our Grand Opening Ceremony is on January 13th at noon in the
            brand-new Kresge auditorium.
          </p>
        </HighlightEntry>
      </div>
    </section>
  );
};

const WideBanner = (props) => {
  return (
    <div className="flex bg-teal-900">
      <div className="flex max-w-[80%] mx-auto">
        <div className="flex flex-col py-16 md:py-24 space-y-8">
          {props.children}
        </div>
      </div>
    </div>
  );
};

type Update = {
  date: string;
  text: React.ReactNode;
};

// Add updates here in reverse chronological order (will be shown in this same order)
const updates: Update[] = [
  {
    date: 'Jan 12, 2023',
    text: (
      <>
        <p>
          We're excited to see you all for our Grand Opening in{' '}
          <a href="http://whereis.mit.edu/?go=W16">Kresge Auditorium</a> at
          12:00pm EST on Friday, January 13th, 2023.
        </p>

        <p>
          The Grand Opening will be livestreamed on <a href="FIXME">FIXME</a>.
        </p>
      </>
    ),
  },
  {
    date: 'Jan 8, 2023',
    text: (
      <>
        <p>
          COVID wastewater levels have been growing steadily. While we still
          plan on running Mystery Hunt in person, we want to remind everyone to
          stay safe, whether it be masking up indoors, getting boosted, or
          opting to stay isolated if you feel sick.
        </p>
        <p>
          If you do not have an MIT ID, you can{' '}
          <a href="https://tim-tickets.atlas-apps.mit.edu/x9UnbQR21HW4C6VN7">
            register for a Tim Ticket
          </a>{' '}
          to access campus from 6am to 7pm each day.
        </p>
        <p>
          In the evenings from 7pm-1am, campus access will be available for MIT
          ID holders or via the south exterior entrance of Building 26 next to
          26-100, which will be staffed in the evening.
        </p>
        <p>
          Campus will be closed from 1am-6am. Other than students in their
          dorms, participants should not be on campus during these hours,
          whether in their classrooms or elsewhere on campus.
        </p>
        <p>
          Wear your hunt badge at all times while in public spaces on campus.
        </p>
        <p>
          We will be selling FIXME HUNT T-shirts and other merch at wrap-up on
          Monday, January 16th. It will be cash only, so remember to bring some
          cash with you! Merch will also be available online after the hunt is
          over.
        </p>
        <p>
          We will close Hunt HQ at 6pm on Sunday or when the coin is found,
          whichever is later. At that point, all physical puzzle pickups,
          interactive rooms and hints will no longer be available. The hunt
          website will stay up, and the answer checker will be available until
          at least wrap-up on Monday. Submissions after Monday 10am ET will not
          be considered for standings.
        </p>
      </>
    ),
  },
  {
    date: 'Jan 6, 2023',
    text: (
      <>
        <p>
          Palindrome will be hosting a How to Hunt seminar in room 4-159 on{' '}
          <strong>Thursday, January 12th, from 6-8pm ET.</strong> Everyone
          interested is welcome to attend, and please tell your friends to come
          as well! It's going to be a much more interactive session than the one
          online last month. Teams may still want to reference{' '}
          <a href="https://www.youtube.com/watch?v=I1i87mwfomw">this video</a>{' '}
          for some background on the Hunt and notes on hunting safely.
        </p>
        <p>All attendees should bring a laptop.</p>
      </>
    ),
  },
  {
    date: 'Jan 3, 2023',
    text: (
      <>
        <p>
          Team captains should have received Health and Safety information and
          must complete the Health and Safety Quiz by Sunday, January 8th.
        </p>
        <p>
          All on-campus participants must complete a{' '}
          <a href="https://na2.docusign.net/Member/PowerFormSigning.aspx?PowerFormId=207c5223-684e-4dbe-9415-1f6f89f70fe6&env=na2&acct=a76475db-2ab3-4a5f-b7bd-1ba6a5dd7f4e&v=2">
            liability waiver
          </a>{' '}
          by Thursday, January 12th. If you are an adult, please fill in your
          own information in every instance of "Parent/Guardian".
        </p>
        <p>
          We will be in touch by early next week with more information about
          classroom assignments (for any teams that have requested a classroom)
          and other logistical information, including Tim Tickets. If you have
          any questions, feel free to email us.
        </p>
      </>
    ),
  },
  {
    date: 'Dec 8, 2022',
    text: (
      <>
        <p>
          We have negotiated room blocks at two hotels for this year's Hunt.
          These are the only room blocks that will be available this year. A
          booking link is provided below for each hotel. Please note that
          availability is limited within each room block.
        </p>
        <p>
          <address className="not-italic">
            Hyatt Regency Boston / Cambridge
            <br />
            575 Memorial Dr.
            <br />
            Cambridge, MA, 02139
          </address>
          Booking link:{' '}
          <a href="https://www.hyatt.com/en-US/group-booking/BOSRC/G-MIHU">
            https://www.hyatt.com/en-US/group-booking/BOSRC/G-MIHU
          </a>
          <br />
          Booking cutoff: 12/22/2022 (or when all rooms in the block are booked)
        </p>
        <p>
          <address className="not-italic">
            Le Méridien Boston Cambridge
            <br />
            20 Sidney St.
            <br />
            Cambridge, MA 02139
          </address>
          Booking link:{' '}
          <a href="https://www.marriott.com/events/start.mi?id=1670516109456&key=GRP">
            https://www.marriott.com/events/start.mi?id=1670516109456&key=GRP
          </a>
          <br />
          Booking cutoff: 12/29/2022 (or when all rooms in the block are booked)
        </p>
      </>
    ),
  },
  {
    date: 'Nov 29, 2022',
    text: (
      <p>
        Last year's hunt writing team, Palindrome, will be running “How to Hunt”
        on Saturday, December 17 at 7:00pm ET. Tune in at{' '}
        <a href="https://www.youtube.com/watch?v=I1i87mwfomw">
          https://www.youtube.com/watch?v=I1i87mwfomw
        </a>
        !
      </p>
    ),
  },
  {
    date: 'Nov 29, 2022',
    text: (
      <p>
        In a change to the previously published minors policy, minors will be
        allowed to attend Mystery Hunt if they are accompanied by a parent or
        guardian at all times. Minors may not go to kickoff, events,
        interactions away from their team's HQ, or field puzzles.
      </p>
    ),
  },
  {
    date: 'Oct 21, 2022',
    text: (
      <p>
        We're excited to announce the opening of the Museum of Interesting
        Things! Come visit us on our opening weekend starting Friday, January
        13, 2023.
      </p>
    ),
  },
];

const Updates = () => {
  const [maxToShow, setMaxToShow] = useState<number>(3);
  const [showMoreButtonNotYetClicked, setShowMoreButtonNotYetClicked] =
    useState<boolean>(true);
  // "Show more" button on page if there are more updates than we want to initially show (maxToShow),
  // and the user has not yet clicked it
  const showMoreButtonVisible =
    updates.length > maxToShow && showMoreButtonNotYetClicked;
  const updateElements = updates.map((update: Update, index: number) => (
    <li key={`${update.date}-${index}`} data-date={update.date}>
      {update.text}
    </li>
  ));

  return (
    <section id="updates" className="pb-6 pt-12 md:pb-12 md:pt-24 bg-off-white">
      <div className="max-w-[70%] md:max-w-[50%] mx-auto pb-12">
        <SubsectionHeading>Updates</SubsectionHeading>
        <ul
          className={cx('timeline', {
            'fade-last': showMoreButtonVisible,
          })}
        >
          {updateElements.slice(0, maxToShow)}
          {!showMoreButtonVisible && <span className="end" />}
        </ul>
        <div className="text-center">
          <a
            className={cx({
              hidden: !showMoreButtonVisible,
            })}
            onClick={() => {
              setMaxToShow(updates.length);
              setShowMoreButtonNotYetClicked(false);
            }}
          >
            Show more
          </a>
        </div>
      </div>
    </section>
  );
};

const LandingPage = (props) => {
  return (
    <>
      <Head>
        <title>FIXME HUNT</title>
      </Head>
      <Header isHomepage />
      <Splash />
      <Highlights />
      <Updates />
      <WideBanner>
        <Link href="/register">
          <a className="call-to-action text-3xl lg:text-5xl">
            Reserve your tickets now →
          </a>
        </Link>
      </WideBanner>
      <Footer />
    </>
  );
};

export default LandingPage;
