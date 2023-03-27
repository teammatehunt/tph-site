import { useEffect, useRef, FunctionComponent, HTMLProps } from 'react';

interface FormRowProps extends HTMLProps<HTMLInputElement> {
  name: string;
  label: string;
  info?: string;
  options?: Record<string, string>;
  autofocus?: boolean;
  errors?: string;
  lines?: number;
}

export const FormRow: FunctionComponent<FormRowProps> = ({
  name,
  label,
  info,
  options,
  defaultValue,
  errors,
  autofocus = false,
  lines = 1,
  children,
  ...props
}) => {
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (autofocus && ref.current) {
      ref.current.focus();
    }
  }, []);

  const inputClassName =
    'w-full h-[3em] px-[1em] rounded-md border-2 outline-2';

  return (
    <div className="mt-6">
      <label htmlFor={name}>
        <div>
          <strong>{label}</strong>
          {props.required && <span className="text-red-500"> *</span>}
        </div>
        <div className="mb-2">{info}</div>
      </label>
      <div className="flex">
        {options ? (
          <select
            className={inputClassName}
            name={name}
            defaultValue={defaultValue ?? ''}
          >
            <option disabled hidden value="" />
            {Object.keys(options).map((optionValue) => (
              <option key={optionValue} value={optionValue}>
                {options[optionValue]}
              </option>
            ))}
          </select>
        ) : lines > 1 ? (
          <textarea
            className={inputClassName}
            name={name}
            rows={lines}
            defaultValue={defaultValue}
          />
        ) : (
          <input
            className={inputClassName}
            name={name}
            ref={ref}
            defaultValue={defaultValue}
            {...props}
          />
        )}
        {children}
      </div>
      {errors && <p className="formerror">{errors}</p>}

      <style jsx>{`
        input,
        select,
        textarea {
          border-color: var(--muted);
        }
        input:focus,
        select:focus,
        textarea:focus {
          outline-color: var(--primary);
        }
        textarea {
          padding: 8px;
          height: 92px;
        }
      `}</style>
    </div>
  );
};
