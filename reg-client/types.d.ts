export type DjangoFormErrors<T> = T & { __all__?: string };
export type DjangoFormResponse<T, R> = {
  form_errors?: DjangoFormErrors<T>;
  data?: R;
};

declare module 'react' {
  interface HTMLAttributes<T> extends AriaAttributes, DOMAttributes<T> {
    // Allow custom sort key on td for sorttable (see components/table.tsx)
    sorttable_customkey?: number | string;
  }
}
