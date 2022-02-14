import { useRouter } from 'next/router';

import Login from 'components/login';
import Section from 'components/section';

const LoginPage = () => {
  const router = useRouter();

  return (
    <Section narrow>
      <Login onLoggedIn={() => router.push('/')} />
    </Section>
  );
};

export default LoginPage;
