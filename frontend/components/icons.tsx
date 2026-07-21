type IconProps = { className?: string };

const paths: Record<string, React.ReactNode> = {
  overview: <><path d="M4 10.5 12 4l8 6.5"/><path d="M6.5 9.5V20h11V9.5M10 20v-6h4v6"/></>,
  nameplate: <><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M7 9h4M7 13h10M7 16h7M16 9h1"/></>,
  technical: <><path d="M4 6h16M4 12h16M4 18h16"/><circle cx="8" cy="6" r="2"/><circle cx="15" cy="12" r="2"/><circle cx="10" cy="18" r="2"/></>,
  documents: <><path d="M6 3h8l4 4v14H6z"/><path d="M14 3v5h5M9 12h6M9 16h6"/></>,
  upload: <><path d="M12 16V4M7.5 8.5 12 4l4.5 4.5"/><path d="M4 15v5h16v-5"/></>,
  arrow: <><path d="M5 12h14M14 7l5 5-5 5"/></>,
  check: <path d="m5 12 4 4L19 6"/>,
};

export function Icon({ name, className }: IconProps & { name: keyof typeof paths }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {paths[name]}
    </svg>
  );
}
