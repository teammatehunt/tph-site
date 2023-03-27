import React from 'react';

export const ImageBanner = ({
  imgSrc,
  children,
}: {
  imgSrc: string;
  children: React.ReactNode;
}) => (
  <section>
    {/* Image max height is 70% of the viewport height on larger screens, clipping the top and bottom */}
    {/* Image min height is 100% of the viewport height on smaller screens, clipping the sides */}
    <div className="absolute flex justify-center w-full h-screen lg:h-[70vh]">
      <img
        className="object-cover justify-center w-full brightness-50"
        src={imgSrc}
        alt=""
      />
    </div>
    <div className="relative flex h-screen lg:h-[70vh] items-center text-white mx-auto w-full lg:w-[50vw] px-4">
      {children}
    </div>
  </section>
);
