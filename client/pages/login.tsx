import { useRouter } from 'utils/router';

import Login from 'components/login';
import Section from 'components/section';

const LoginPage = () => {
  const router = useRouter();

  return (
    <Section narrow>
      <Login />
    </Section>
  );
};

export default LoginPage;
