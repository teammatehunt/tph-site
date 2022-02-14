import { useRouter } from 'next/router';

import Register from 'components/register';
import Section from 'components/section';

const RegisterPage = () => {
  const router = useRouter();

  return (
    <Section narrow>
      <Register onRegister={() => router.push('/')} />
    </Section>
  );
};

export default RegisterPage;
