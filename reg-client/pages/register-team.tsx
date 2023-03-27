import { useContext, useEffect } from 'react';
import Router from 'next/router';

import RegisterTeam from 'components/register_team';
import RegistrationPageBase from 'components/content_page_base';
import HuntInfoContext, { isLoggedInAs } from 'components/context';
import { SubsectionHeading } from 'components/headings';

const RegisterTeamPage = () => {
  const huntInfoContext = useContext(HuntInfoContext);
  const loggedInSlug: string | undefined =
    huntInfoContext.userInfo?.teamInfo?.slug;
  const loggedInAs = isLoggedInAs(huntInfoContext);

  // If someone tries to go to /register-team while logged in as an individual, direct them appropriately
  useEffect(() => {
    if (loggedInAs === 'individual') {
      Router.push('/register-individual');
    }
  }, []);

  return (
    <RegistrationPageBase title="FIXME HUNT - Register">
      <section className="mx-auto w-full lg:w-[50vw] px-4 py-12 lg:py-24 space-y-8">
        <SubsectionHeading>Register a team</SubsectionHeading>
        <RegisterTeam
          loggedInSlug={loggedInSlug}
          huntStarted={huntInfoContext.huntInfo.secondsToStartTime <= 0}
        />
      </section>
    </RegistrationPageBase>
  );
};

export default RegisterTeamPage;
