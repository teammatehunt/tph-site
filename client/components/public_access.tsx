import { useRouter } from 'utils/router';

import { clientFetch } from 'utils/fetch';
import { DjangoFormResponse } from 'types';
import { LoginFormProps } from 'components/login';

const PublicAccessLink = () => {
  const router = useRouter();

  const onPublicAccessLogin = async () => {
    const data = new FormData();
    data.append('username', 'public');
    data.append('password', 'public');
    data.append('json', '1');
    const resp = await clientFetch<
      { redirect?: string } & DjangoFormResponse<LoginFormProps, void>
    >(router, '/login', { method: 'POST', body: data });
    if (!resp?.form_errors) {
      router.push(resp.redirect ?? '/');
    }
  };

  return <a onClick={onPublicAccessLogin}>Public Access</a>;
};

export default PublicAccessLink;
