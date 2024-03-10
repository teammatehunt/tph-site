import Head from 'next/head';
import Link from 'next/link';
import RegistrationPageBase from 'components/content_page_base';
import { SubsectionHeading } from 'components/headings';

export default function Custom404() {
  return (
    <RegistrationPageBase title="404 - Page Not Found">
      <section className="bg-off-white mx-auto flex flex-col items-center justify-center text-center h-[40vh] sm:h-[65vh]">
        <SubsectionHeading>Page Not Found</SubsectionHeading>
        <Link href="/" className="mt-4">
          Back to the museum
        </Link>
      </section>
    </RegistrationPageBase>
  );
}
