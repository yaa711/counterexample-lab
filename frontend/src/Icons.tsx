type Name =
  | "flask"
  | "play"
  | "arrow"
  | "download"
  | "code"
  | "check"
  | "copy"
  | "book"
  | "terminal"
  | "layers"
  | "close";
const paths: Record<Name, string> = {
  flask: "M9 3h6M10 3v6L4 19a1 1 0 0 0 1 2h14a1 1 0 0 0 1-2L14 9V3M8 14h8",
  play: "m9 5 11 7-11 7V5Z",
  arrow: "M4 12h16m-6-6 6 6-6 6",
  download: "M12 3v12m-5-5 5 5 5-5M5 16v5h14v-5",
  code: "m8 5-6 7 6 7m8-14 6 7-6 7m-3-16-2 18",
  check: "m5 12 4 4L19 6",
  copy: "M9 9h12v12H9zM15 9V3H3v12h6",
  book: "M12 5v16M3 3h5l4 2 4-2h5v16h-5l-4 2-4-2H3z",
  terminal: "m5 6 5 6-5 6m8 0h6",
  layers: "m12 3 10 5-10 5L2 8l10-5Zm-9 10 9 5 9-5M3 18l9 5 9-5",
  close: "m6 6 12 12M6 18 18 6",
};
export function Icon({ name, size = 18 }: { name: Name; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[name]} />
    </svg>
  );
}
