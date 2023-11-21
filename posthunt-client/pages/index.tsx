import Head from 'next/head';

const Page = () => {
  return (
    <div className="m-12">
      <Head>
        <title>Mystery Hunt 20xx</title>
      </Head>

      <h1>20xx MIT Mystery Hunt</h1>

      <p>
        The 20xx MIT Mystery Hunt started with teams working through a beginning
        round, before discovering a hidden new round.
      </p>

      <p>
        The Hunt kicked off on Friday, January xx at noon ET. On Someday,
        January xx, at Sometime, <b>The Winning Team</b> became the first team
        to find the coin, and won the hunt.
      </p>

      <h3>Links</h3>

      <p>
        <a href="/20xx/mypuzzlehunt.com">The Hunt</a>
      </p>
      <p>
        <a href="/20xx/registration.mypuzzlehunt.com">Registration site</a>
      </p>
    </div>
  );
};

export default Page;

export const getServerSideProps = () => {
  return {
    props: {
      bare: true,
    },
  };
};
