import { apiRequest } from "@/api/client";
import type {
  AdminOverrideCreateRequest,
  AdminOverrideResponse,
  AdminPendingRequestItem,
  AdminPublicKeyResponse,
  AuthTokensResponse,
  BlocklistCreate,
  BlocklistPublishRequest,
  BlocklistResponse,
  BlocklistRollbackRequest,
  BlocklistUpdate,
  BlocklistVersionResponse,
  DomainResponse,
  FeedIngestRequest,
  FeedIngestResponse,
  HealthResponse,
  PaginatedResponse,
  PartnerCosignRequest,
  PartnerVerifyTokenResponse,
  ReadinessResponse,
  UserLoginRequest,
  UserProfileResponse,
} from "@/types/api";

export const healthApi = {
  getHealth: () => apiRequest<HealthResponse>("/health", { auth: false }),
  getReadiness: () =>
    apiRequest<ReadinessResponse>("/health/ready", { auth: false }),
};

export const authApi = {
  login: (payload: UserLoginRequest) =>
    apiRequest<AuthTokensResponse>("/auth/login", {
      method: "POST",
      auth: false,
      body: JSON.stringify(payload),
    }),
  getMe: () => apiRequest<UserProfileResponse>("/auth/me"),
};

export const adminApi = {
  listPendingOverrides: () =>
    apiRequest<AdminPendingRequestItem[]>("/admin/override-requests/pending"),
  approveOverride: (payload: AdminOverrideCreateRequest) =>
    apiRequest<AdminOverrideResponse>("/admin/override-requests/approve", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getPublicKey: () =>
    apiRequest<AdminPublicKeyResponse>("/admin/public-key", { auth: false }),
};

export const blocklistsApi = {
  list: (offset = 0, limit = 50) =>
    apiRequest<PaginatedResponse<BlocklistResponse>>(
      `/blocklists?offset=${offset}&limit=${limit}`,
    ),
  getById: (id: string) =>
    apiRequest<BlocklistResponse>(`/blocklists/${id}`),
  create: (payload: BlocklistCreate) =>
    apiRequest<BlocklistResponse>("/blocklists", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  update: (id: string, payload: BlocklistUpdate) =>
    apiRequest<BlocklistResponse>(`/blocklists/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  remove: (id: string) =>
    apiRequest<void>(`/blocklists/${id}`, {
      method: "DELETE",
    }),
  listDomains: (id: string, offset = 0, limit = 100) =>
    apiRequest<PaginatedResponse<DomainResponse>>(
      `/blocklists/${id}/domains?offset=${offset}&limit=${limit}`,
    ),
  removeDomains: (id: string, domainIds: string[]) =>
    apiRequest<{ removed: number }>(`/blocklists/${id}/domains`, {
      method: "DELETE",
      body: JSON.stringify({ domain_ids: domainIds }),
    }),
  ingestFeed: (id: string, payload: FeedIngestRequest) =>
    apiRequest<FeedIngestResponse>(`/blocklists/${id}/ingest`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listVersions: (id: string, offset = 0, limit = 50) =>
    apiRequest<PaginatedResponse<BlocklistVersionResponse>>(
      `/blocklists/${id}/versions?offset=${offset}&limit=${limit}`,
    ),
  publishVersion: (id: string, payload: BlocklistPublishRequest) =>
    apiRequest<BlocklistVersionResponse>(`/blocklists/${id}/publish`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  rollbackVersion: (id: string, payload: BlocklistRollbackRequest) =>
    apiRequest<BlocklistVersionResponse>(`/blocklists/${id}/rollback`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

export const accountabilityApi = {
  verifyToken: (token: string) =>
    apiRequest<PartnerVerifyTokenResponse>(
      `/accountability/verify-token?token=${encodeURIComponent(token)}`,
      { auth: false },
    ),
  partnerCosign: (payload: PartnerCosignRequest) =>
    apiRequest<PartnerVerifyTokenResponse>("/accountability/partner-cosign", {
      method: "POST",
      auth: false,
      body: JSON.stringify(payload),
    }),
};

