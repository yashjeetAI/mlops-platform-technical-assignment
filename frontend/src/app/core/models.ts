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
  full_name: string;
  role: Role;
  created_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}
