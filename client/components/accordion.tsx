import React, { Fragment } from 'react';
import { Disclosure } from '@headlessui/react';
import { ChevronDownIcon } from '@heroicons/react/24/outline';
import cx from 'classnames';

// Defines an accordion UI (shows heading only, expanding inner content if it doesn't exist.

const Accordion = ({ heading, children }) => (
  <>
    <section className="accordion">
      <Disclosure>
        {({ open }) => (
          <>
            <Disclosure.Button
              className="cursor-pointer flex w-full text-left justify-between rounded-lg items-center h-fit border-b border-slate-200 hover:bg-slate-100 px-4"
              as="div"
            >
              <span className="text-primary text-2xl py-2 pr-4">{heading}</span>
              <ChevronDownIcon
                className={cx('h-5 w-5', open ? 'rotate-180 transform' : '')}
              />
            </Disclosure.Button>
            <Disclosure.Panel className="px-4 py-2">
              {children}
            </Disclosure.Panel>
          </>
        )}
      </Disclosure>
    </section>
  </>
);

export default Accordion;
