import Head from 'next/head';

import Header from 'components/header';
import Footer from 'components/footer';

const RegistrationPageBase = ({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) => {
  return (
    <>
      <Head>
        <title>{title}</title>
      </Head>

      <Header />

      {children}

      <Footer />
    </>
  );
};

export default RegistrationPageBase;
