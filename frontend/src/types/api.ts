export type DomainCategory =
  | "pornography"
  | "explicit"
  | "erotica"
  | "malware"
  | "unspecified";

export type DomainStatus =
  | "active"
  | "inactive"
  | "pending_review"
  | "allowlisted";

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
  has_more: boolean;
}

export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
  timestamp: string;
}

export interface ReadinessResponse {
  status: string;
  database: string;
  version: string;
  timestamp: string;
}

export interface UserLoginRequest {
  username: string;
  password: string;
  device_identifier?: string | null;
  device_name?: string | null;
}

export interface AuthTokensResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface DeviceResponse {
  id: string;
  device_identifier: string;
  device_name: string;
  client_version: string;
  is_active: boolean;
  last_seen_at: string;
}

export interface UserProfileResponse {
  id: string;
  username: string;
  email: string | null;
  is_admin: boolean;
  created_at: string;
  devices: DeviceResponse[];
}

export interface AdminPendingRequestItem {
  request_id: string;
  user_id: string;
  username: string;
  partner_email: string;
  started_at: string;
  cooloff_days: number;
  status: string;
}

export interface AdminOverrideCreateRequest {
  request_id: string;
  reason: string;
}

export interface AdminOverrideResponse {
  override_id: string;
  request_id: string;
  reason: string;
  signed_token: string;
  issued_at: string;
}

export interface AdminPublicKeyResponse {
  public_key_pem: string;
  algorithm: string;
}

export interface BlocklistResponse {
  id: string;
  name: string;
  description: string | null;
  is_default: boolean;
  is_active: boolean;
  current_version: string;
  domain_count: number;
  created_at: string;
  updated_at: string;
}

export interface BlocklistCreate {
  name: string;
  description?: string | null;
  is_default?: boolean;
  is_active?: boolean;
}

export interface BlocklistUpdate {
  name?: string | null;
  description?: string | null;
  is_default?: boolean | null;
  is_active?: boolean | null;
}

export interface BlocklistVersionResponse {
  id: string;
  blocklist_id: string;
  version: string;
  content_hash: string;
  domain_count: number;
  changelog: string | null;
  created_at: string;
}

export interface DomainResponse {
  id: string;
  domain: string;
  category: DomainCategory;
  status: DomainStatus;
  source: string;
  confidence_score: number;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface FeedIngestRequest {
  content: string;
  source?: string;
  category?: DomainCategory;
}

export interface FeedIngestResponse {
  blocklist_id: string;
  parsed_count: number;
  new_domains_created: number;
  domains_associated: number;
  total_blocklist_domains: number;
}

export interface BlocklistPublishRequest {
  version?: string | null;
  changelog?: string | null;
  force?: boolean;
}

export interface BlocklistRollbackRequest {
  target_version: string;
  reason?: string | null;
}

export interface PartnerVerifyTokenResponse {
  valid: boolean;
  request_id: string | null;
  started_at: string | null;
  cooloff_days: number | null;
  status: string | null;
  message: string;
}

export interface PartnerCosignRequest {
  token: string;
  decision: "approve" | "reject";
  rejection_reason?: string | null;
}

