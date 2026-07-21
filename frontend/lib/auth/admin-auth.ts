export type AdminSession = {
  authenticated: boolean;
  displayName?: string;
};

/**
 * Admin authentication boundary. The MVP deliberately returns a local demo
 * session. Replace with a Keycloak-backed server session before deployment.
 */
export async function getAdminSession(): Promise<AdminSession> {
  return { authenticated: true, displayName: "Demo administrator" };
}
