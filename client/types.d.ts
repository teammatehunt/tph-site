export type DjangoFormErrors<T> = T & { __all__?: string };
export type DjangoFormResponse<T, R> = {
  form_errors?: DjangoFormErrors<T>;
  data?: R;
};
