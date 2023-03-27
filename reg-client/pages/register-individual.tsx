import { useContext, useEffect } from 'react';
import Router from 'next/router';

import RegisterIndividual from 'components/register_individual';
import RegistrationPageBase from 'components/content_page_base';
import HuntInfoContext, { isLoggedInAs } from 'components/context';
import { SubsectionHeading } from 'components/headings';

const RegisterIndividualPage = () => {
  const huntInfoContext = useContext(HuntInfoContext);
  const loggedInAs = isLoggedInAs(huntInfoContext);

  // If someone tries to go to /register-individual while logged in as a team, direct them appropriately
  useEffect(() => {
    if (loggedInAs === 'team') {
      Router.push('/register-team');
    }
  }, []);

  return (
    <RegistrationPageBase title="FIXME HUNT - Register">
      <section className="mx-auto w-full lg:w-[50vw] px-4 py-12 lg:py-24 space-y-8">
        <SubsectionHeading>Register as an individual</SubsectionHeading>
        <RegisterIndividual
          isLoggedIn={!!huntInfoContext.userInfo}
          huntStarted={huntInfoContext.huntInfo.secondsToStartTime <= 0}
        />
      </section>
    </RegistrationPageBase>
  );
};

export default RegisterIndividualPage;
