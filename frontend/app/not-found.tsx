import Link from "next/link";

export default function NotFound() {
  return <div className="page empty-state"><p className="eyebrow">404</p><h1>Page not found</h1><p>The requested passport section does not exist.</p><Link className="primary-button" href="/">Return to overview</Link></div>;
}
