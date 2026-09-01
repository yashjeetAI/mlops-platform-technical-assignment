/** Domain roles — must mirror the backend `Role` enum. */
export enum Role {
  VIEWER = 'VIEWER',
  ENGINEER = 'ENGINEER',
  APPROVER = 'APPROVER',
  ADMIN = 'ADMIN',
}

export interface User {
  id: string;
  username: string;
  email: string;
  fullName: string;
  role: Role;
  createdAt: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  accessToken: string;
  tokenType: string;
}
