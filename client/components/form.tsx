import { useEffect, useRef, FunctionComponent, HTMLProps } from 'react';

interface FormRowProps extends HTMLProps<HTMLInputElement> {
  name: string;
  label: string;
  autofocus?: boolean;
  errors?: string;
}

export const FormRow: FunctionComponent<FormRowProps> = ({
  name,
  label,
  errors,
  autofocus = false,
  ...props
}) => {
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (autofocus && ref.current) {
      ref.current.focus();
    }
  }, []);

  return (
    <>
      <label htmlFor={name}>{label}</label>
      <input name={name} id={name} ref={ref} {...props} />
      {errors && <p className="formerror">{errors}</p>}

      <style jsx>{`
        label {
          color: var(--primary);
          text-align: right;
          height: 28px;
          padding-top: 8px;
        }

        input {
          border: none;
          border-bottom: 1px solid var(--text);
          font-size: 16px;
          height: 28px;
          min-width: 50%;
          max-width: 600px;
          padding: 0 4px;
        }

        .formerror {
          grid-column: 1 / 3;
        }

        @media (max-width: 800px) {
          input {
            padding: 4px;
          }
        }
      `}</style>
    </>
  );
};
