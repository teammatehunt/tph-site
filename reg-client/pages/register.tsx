import { useContext } from 'react';
import Link from 'next/link';

import HuntInfoContext from 'components/context';
import RegistrationPageBase from 'components/content_page_base';
import {
  SubsectionHeading,
  sectionHeadingClassName,
  ItemHeading,
} from 'components/headings';
import { isLoggedInAs } from 'components/context';
import imgRegisterHero from 'assets/public/registration.jpeg';
import { ImageBanner } from 'components/content_page_image_banner';
import { serverFetch } from 'utils/fetch';

const RegisterPage = ({ teamsList }) => {
  const huntInfoContext = useContext(HuntInfoContext);
  const loggedInAs = isLoggedInAs(huntInfoContext);
  const loggedIn = !!huntInfoContext?.userInfo;

  const notLoggedInContent = (
    <>
      <p>
        Already registered?{' '}
        <Link href="/login">
          <a className="white">Click here to log in.</a>
        </Link>
      </p>
      <div className="flex flex-wrap lg:space-x-4 flex-col lg:flex-row">
        <div className="pt-3">
          <Link href="/register-team">
            <a className="button-link button-link-accent">Reserve as a team</a>
          </Link>
        </div>
        <div className="pt-3">
          <Link href="/register-individual">
            <a className="button-link button-link-white">
              Reserve without a team
            </a>
          </Link>
        </div>
      </div>
    </>
  );

  const loggedInTeamContent = (
    <div className="pt-3">
      <Link href="/register-team">
        <a className="button-link button-link-white">Your reservation</a>
      </Link>
    </div>
  );

  const loggedInIndividualContent = (
    <div className="pt-3">
      <Link href="/register-individual">
        <a className="button-link button-link-white">Your reservation</a>
      </Link>
    </div>
  );

  return (
    <RegistrationPageBase title="FIXME HUNT - Register">
      <ImageBanner imgSrc={imgRegisterHero}>
        <div className="flex flex-col space-y-6">
          <span className={sectionHeadingClassName}>
            {!process.env.isArchive && loggedIn
              ? 'Your tickets'
              : 'Reserve tickets'}
          </span>
          {!process.env.isArchive && (
            <>
              <span>
                {loggedIn
                  ? 'We look forward to seeing you and our other esteemed guests at our grand opening on January 13.'
                  : 'Don’t delay—reserve tickets before December 31 to guarantee your spot!'}
              </span>
              {loggedInAs === 'team'
                ? loggedInTeamContent
                : loggedInAs === 'individual'
                ? loggedInIndividualContent
                : notLoggedInContent}
            </>
          )}
        </div>
      </ImageBanner>

      {teamsList.length > 0 && (
        <section className="bg-off-white w-full p-12 lg:py-24 space-y-12">
          <SubsectionHeading>Our guests</SubsectionHeading>
          {!loggedInAs && (
            <p className="text-center">
              By reserving, you will join our other illustrious guests:
            </p>
          )}
          <div className="lg:w-1/2 mx-auto space-y-4 md:space-y-8">
            {teamsList.map((team) => (
              <div key={team.name}>
                <h3>{team.name}</h3>
                <p>{team.bio}</p>
              </div>
            ))}
          </div>
        </section>
      )}
    </RegistrationPageBase>
  );
};

export default RegisterPage;

export const getServerSideProps = async (context) => {
  const props = await serverFetch(context, '/registration_teams');
  return { props };
};
