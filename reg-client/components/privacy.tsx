import Title from 'components/title';
import Head from 'next/head';

const PrivacyPolicy = () => {
  return (
    <div>
      <Head>
        <title>Privacy Policy</title>
      </Head>
      <h2>Privacy Policy</h2>
      <p>
        MIT Puzzle Club and teammate provide this Privacy Policy to describe how
        we collect, disclose, and otherwise process your information.
      </p>
      <p>
        <i>This is not a puzzle.</i>
      </p>
      <h4>Information we collect</h4>
      <p>
        We collect information directly from you (e.g., when you register or
        communicate with us) and automatically through the use of cookies and
        similar technologies.
      </p>
      <h4>How we process your information</h4>
      <p>
        We use your information to facilitate account creation and
        authentication, to deliver and facilitate delivery of services to the
        user, to offer personalization, to send promotional communications and
        updates, and to identify usage trends.
      </p>
      <h4>How we share your information</h4>
      <p>
        We may share tracking and usage information with third-party services
        including{' '}
        <a href="https://www.google.com/policies/privacy/partners/">
          Google Analytics
        </a>{' '}
        to monitor and analyze web traffic and track user behavior.
      </p>
      <style jsx>{`
        p {
          margin-block: 1rem;
        }
      `}</style>
    </div>
  );
};

export default PrivacyPolicy;
