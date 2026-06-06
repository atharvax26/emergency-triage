import { UserRole } from "@/hooks/use-auth";

export interface RolePermissions {
  canViewQueue: boolean;
  canStartTriage: boolean;
  canViewDashboard: boolean;
  canOverrideAI: boolean;
  canActivateEmergency: boolean;
  canViewAuditLog: boolean;
  canExportAuditLog: boolean;
  canManageUsers: boolean;
  canViewConfidence: boolean;
  canViewReasoning: boolean;
}

export const rolePermissions: Record<UserRole, RolePermissions> = {
  nurse: {
    canViewQueue: true,
    canStartTriage: true,
    canViewDashboard: true,
    canOverrideAI: false, // Nurses cannot override AI decisions
    canActivateEmergency: true,
    canViewAuditLog: true,
    canExportAuditLog: false,
    canManageUsers: false,
    canViewConfidence: true,
    canViewReasoning: false, // Nurses see results but not AI reasoning
  },
  doctor: {
    canViewQueue: true,
    canStartTriage: true,
    canViewDashboard: true,
    canOverrideAI: true, // Doctors can override AI decisions
    canActivateEmergency: true,
    canViewAuditLog: true,
    canExportAuditLog: true,
    canManageUsers: false,
    canViewConfidence: true,
    canViewReasoning: true, // Doctors see full AI reasoning
  },
  admin: {
    canViewQueue: true,
    canStartTriage: false, // Admins don't perform triage
    canViewDashboard: true,
    canOverrideAI: false, // Admins don't override clinical decisions
    canActivateEmergency: false, // Admins don't activate emergency
    canViewAuditLog: true,
    canExportAuditLog: true,
    canManageUsers: true,
    canViewConfidence: true,
    canViewReasoning: true,
  },
};

export function hasPermission(role: UserRole | undefined, permission: keyof RolePermissions): boolean {
  if (!role) return false;
  return rolePermissions[role][permission];
}

export function getRoleLabel(role: UserRole): string {
  const labels: Record<UserRole, string> = {
    nurse: "Nurse",
    doctor: "Doctor",
    admin: "Administrator",
  };
  return labels[role];
}

export function getRoleBadgeColor(role: UserRole): string {
  const colors: Record<UserRole, string> = {
    nurse: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    doctor: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
    admin: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
  };
  return colors[role];
}
