import Section from 'components/section';
import PrivacyPolicy from 'components/privacy';

const PrivacyPage = () => {
  return (
    <Section narrow>
      <PrivacyPolicy />
    </Section>
  );
};

export default PrivacyPage;

export const getServerSideProps = () => {
  return {
    props: {
      bare: true,
    },
  };
};
