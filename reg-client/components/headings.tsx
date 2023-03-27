import React from 'react';

// This set of components is to align on headings for the registration site only
// without impacting existing components/styles for the hunt site.

// The registration site has different expectations; for example,
// we expect a nontrivial number of people to view the registration site on mobile,
// and we don't expect the designs to necessarily align.

// Like an h1
export const sectionHeadingClassName =
  'text-4xl sm:text-5xl md:text-6xl lg:text-7xl xl:text-8xl font-bold';

export const SectionHeading = ({ children }) => (
  <div className={`text-primary text-center ${sectionHeadingClassName}`}>
    {children}
  </div>
);

// Like an h2
export const subsectionHeadingClassName = 'text-4xl font-bold';

export const SubsectionHeading = ({
  children,
}: {
  children: React.ReactNode;
}) => (
  <div className={`text-primary text-center ${subsectionHeadingClassName}`}>
    {children}
  </div>
);

const itemHeadingClassName = 'text-2xl';

// Like an h3, describing an item in a subsection
export const ItemHeading: React.FC<React.HTMLProps<HTMLDivElement>> = ({
  children,
  ...props
}) => (
  <div className={`text-primary ${itemHeadingClassName}`} {...props}>
    {children}
  </div>
);
