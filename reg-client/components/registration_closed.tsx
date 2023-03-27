import React from 'react';
import Link from 'next/link';

export const RegistrationClosed = () => {
  return (
    <div className="bg-off-white p-6">
      <span className="space-y-4">
        <p>Registration is closed for 2023.</p>
        <p>
          If you have an existing registration for this year, you can still view
          it by <Link href="/login">logging in.</Link>
        </p>
      </span>
    </div>
  );
};
