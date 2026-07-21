import { AdminUploadForm } from "@/components/admin-upload-form";
import { PageHeader } from "@/components/page-header";
import { getAdminSession } from "@/lib/auth/admin-auth";

export default async function AdminUploadPage() {
  const session = await getAdminSession();
  if (!session.authenticated) return <div className="page"><PageHeader eyebrow="Restricted area" title="Administrator sign-in required" description="Authenticate with the configured identity provider to import product data." /><section className="content-card"><p>Keycloak sign-in will be connected at this authentication boundary.</p></section></div>;
  return <div className="page"><PageHeader eyebrow="Restricted area" title="Admin Upload" description="Import or replace product source data. This MVP validates files using a mock service." /><div className="admin-session"><span className="status-dot" />Signed in as <strong>{session.displayName}</strong><span className="mock-chip">Mock session</span></div><AdminUploadForm /></div>;
}
