import React from 'react';
import Link from 'components/link';

import Section from 'components/section';
import Title from 'components/title';

const DonationPage = () => {
  return (
    <>
      <Title title="Donate" />
      <Section>
        <p>
          You don't need to spend money to solve this hunt, but we appreciate
          all donations!
        </p>

        <p>
          Please enter the amount you wish to donate. You'll be redirected to
          Paypal.
        </p>

        <form method="POST" action="https://www.paypal.com/cgi-bin/webscr">
          &#36;
          <input type="hidden" name="cmd" value="_donations" />
          {/* FIXME: Update to link to your own Paypal account. */}
          <input type="hidden" name="business" value="RL35E3TW2S3M4" />
          <input type="hidden" name="currency_code" value="USD" />
          <input
            type="hidden"
            name="return"
            value={`https://${process.env.domainName}/faq`}
          />
          <input
            type="hidden"
            name="cancel_return"
            value={`https://${process.env.domainName}/donate`}
          />
          <input name="amount" type="number" step="0.01" required />
          <input type="submit" name="donate" value="Donate" />
        </form>

        <Link href="/faq">Back to FAQ</Link>
      </Section>

      <style jsx>{`
        form {
          font-size: 20px;
        }

        input {
          font-size: 16px;
          margin: 0 8px 40px;
          padding: 8px 16px;
        }
      `}</style>
    </>
  );
};

export default DonationPage;
