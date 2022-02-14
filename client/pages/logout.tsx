import { useRouter } from 'next/router';
import { clientFetch } from 'utils/fetch';
import Section from 'components/section';

const Logout = () => {
  const router = useRouter();

  clientFetch(router, '/logout', { method: 'GET' }, true).then(() => {
    router.push('/');
  });
  return <Section>Logging you out...</Section>;
};

export default Logout;
