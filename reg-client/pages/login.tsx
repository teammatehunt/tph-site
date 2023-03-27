import Login from 'components/login';
import RegistrationPageBase from 'components/content_page_base';
import { SubsectionHeading } from 'components/headings';

const LoginPage = () => {
  return (
    <RegistrationPageBase title="FIXME HUNT - Login">
      <section className="mx-auto w-full lg:w-[50vw] px-4 py-12 lg:py-24 space-y-12">
        <SubsectionHeading>Login</SubsectionHeading>
        <Login />
      </section>
    </RegistrationPageBase>
  );
};

export default LoginPage;
