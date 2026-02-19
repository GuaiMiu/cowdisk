import { request } from '@/api/request'
import type {
  PublicConfigOut,
  SetupDefaultsOut,
  SetupPayload,
  SetupProgressOut,
  SetupResultOut,
  SetupStatusOut,
} from '@/types/setup'

export const getSetupStatus = () =>
  request<SetupStatusOut>({
    url: '/api/v1/system/setup/status',
    method: 'GET',
  })

export const getPublicConfig = () =>
  request<PublicConfigOut>({
    url: '/api/v1/system/setup/public-config',
    method: 'GET',
  })

export const getSetupDefaults = () =>
  request<SetupDefaultsOut>({
    url: '/api/v1/system/setup/defaults',
    method: 'GET',
  })

export type SiteAssetType = 'logo' | 'favicon' | 'login_bg' | 'theme_image'

export const uploadSiteAsset = (assetType: SiteAssetType, file: File) => {
  const formData = new FormData()
  formData.append('logo', file)
  return request<{ asset_id: string; asset_url: string }>({
    url: `/api/v1/system/setup/site-asset/${assetType}`,
    method: 'POST',
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const submitSetup = (payload: SetupPayload) =>
  request<SetupResultOut>({
    url: '/api/v1/system/setup',
    method: 'POST',
    data: payload,
  })

export const getSetupProgress = () =>
  request<SetupProgressOut>({
    url: '/api/v1/system/setup/progress',
    method: 'GET',
  })
