import { useRouter } from 'utils/router';
import { clientFetch } from 'utils/fetch';
import Section from 'components/section';
import { useEffect } from 'react';

const Logout = () => {
  const router = useRouter();

  useEffect(() => {
    clientFetch(router, '/logout', { method: 'GET' }, true).then(() => {
      router.push('/');
    });
  }, [router]);
  return <Section>Logging you out...</Section>;
};

export default Logout;
