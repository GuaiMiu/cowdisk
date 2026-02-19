<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from '@/components/common/Button.vue'
import Input from '@/components/common/Input.vue'
import Modal from '@/components/common/Modal.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { getAvatar, getMe, updateMe, uploadAvatar } from '@/api/modules/auth'
import { useUserAvatar } from '@/composables/useUserAvatar'
import { useAuthStore } from '@/stores/auth'
import { useMessage } from '@/stores/message'

const { t } = useI18n({ useScope: 'global' })
const authStore = useAuthStore()
const message = useMessage()

const fileInputRef = ref<HTMLInputElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const selectedFile = ref<File | null>(null)
const localPreviewUrl = ref<string | null>(null)
const avatarModalOpen = ref(false)
const uploading = ref(false)
const savingNickname = ref(false)
const savingMail = ref(false)
const savingPassword = ref(false)

const userLabel = computed(() => authStore.me?.nickname || authStore.me?.username || '')
const { avatarFailed, avatarSrc, initials, onAvatarError } = useUserAvatar({
  label: userLabel,
  avatarPath: computed(() => authStore.me?.avatar_path),
  token: computed(() => authStore.token),
  loadAvatar: getAvatar,
})

const displayAvatar = computed(() => localPreviewUrl.value || avatarSrc.value || null)
const maxAvatarSize = 2 * 1024 * 1024
const allowedMime = new Set(['image/png', 'image/jpeg', 'image/webp'])

const profileNickname = ref(authStore.me?.nickname || '')
const profileMail = ref(authStore.me?.mail || '')
const currentPassword = ref('')
const newPassword = ref('')
const confirmNewPassword = ref('')
const editingNickname = ref(false)
const editingMail = ref(false)
const passwordModalOpen = ref(false)

const editorImage = ref<HTMLImageElement | null>(null)
const editorImageUrl = ref<string | null>(null)
const editorZoom = ref(1)
const editorRotation = ref(0)
const editorCropRatio = ref(0.8)
const editorOffsetX = ref(0)
const editorOffsetY = ref(0)
const isDragging = ref(false)
const dragStart = ref({ x: 0, y: 0, ox: 0, oy: 0 })

const syncProfileFromStore = () => {
  profileNickname.value = authStore.me?.nickname || ''
  profileMail.value = authStore.me?.mail || ''
}

const revokeLocalPreview = () => {
  if (localPreviewUrl.value) {
    URL.revokeObjectURL(localPreviewUrl.value)
  }
  localPreviewUrl.value = null
}

const revokeEditorImage = () => {
  if (editorImageUrl.value) {
    URL.revokeObjectURL(editorImageUrl.value)
  }
  editorImageUrl.value = null
  editorImage.value = null
}

const resetAvatarEditor = () => {
  editorZoom.value = 1
  editorRotation.value = 0
  editorCropRatio.value = 0.8
  editorOffsetX.value = 0
  editorOffsetY.value = 0
}

const drawAvatarEditor = () => {
  const canvas = canvasRef.value
  const image = editorImage.value
  if (!canvas || !image) {
    return
  }
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    return
  }
  const w = canvas.width
  const h = canvas.height
  const cropSize = Math.max(80, Math.floor(Math.min(w, h) * editorCropRatio.value))
  const cropX = Math.floor((w - cropSize) / 2)
  const cropY = Math.floor((h - cropSize) / 2)
  const cropRadius = cropSize / 2
  const cropCenterX = cropX + cropRadius
  const cropCenterY = cropY + cropRadius

  ctx.clearRect(0, 0, w, h)
  ctx.fillStyle = '#111'
  ctx.fillRect(0, 0, w, h)

  const baseScale = Math.max(cropSize / image.width, cropSize / image.height)
  const scale = baseScale * editorZoom.value
  const rad = (editorRotation.value * Math.PI) / 180

  ctx.save()
  ctx.translate(w / 2 + editorOffsetX.value, h / 2 + editorOffsetY.value)
  ctx.rotate(rad)
  ctx.scale(scale, scale)
  ctx.drawImage(image, -image.width / 2, -image.height / 2, image.width, image.height)
  ctx.restore()

  ctx.save()
  ctx.fillStyle = 'rgba(0, 0, 0, 0.5)'
  ctx.beginPath()
  ctx.rect(0, 0, w, h)
  ctx.moveTo(cropCenterX + cropRadius, cropCenterY)
  ctx.arc(cropCenterX, cropCenterY, cropRadius, 0, Math.PI * 2)
  ctx.fill('evenodd')
  ctx.restore()

  ctx.save()
  ctx.strokeStyle = '#ffffff'
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.arc(cropCenterX, cropCenterY, cropRadius, 0, Math.PI * 2)
  ctx.stroke()
  ctx.restore()
}

const openFilePicker = () => {
  fileInputRef.value?.click()
}

const openAvatarModal = () => {
  avatarModalOpen.value = true
}

const loadAvatarEditorImage = (file: File) => {
  revokeEditorImage()
  const nextUrl = URL.createObjectURL(file)
  editorImageUrl.value = nextUrl
  const image = new Image()
  image.onload = () => {
    editorImage.value = image
    resetAvatarEditor()
    drawAvatarEditor()
  }
  image.onerror = () => {
    editorImage.value = null
    message.error(t('settings.avatar.uploadFailTitle'), t('settings.avatar.invalidType'))
  }
  image.src = nextUrl
}

const onSelectAvatar = (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) {
    return
  }
  if (!allowedMime.has(file.type)) {
    message.warning(t('settings.avatar.invalidType'))
    return
  }
  if (file.size > maxAvatarSize) {
    message.warning(t('settings.avatar.tooLarge'))
    return
  }
  selectedFile.value = file
  revokeLocalPreview()
  localPreviewUrl.value = URL.createObjectURL(file)
  loadAvatarEditorImage(file)
}

const clearSelectedAvatar = () => {
  selectedFile.value = null
  revokeLocalPreview()
  revokeEditorImage()
}

const closeAvatarModal = () => {
  if (uploading.value) {
    return
  }
  avatarModalOpen.value = false
  clearSelectedAvatar()
}

const rotateEditor = (delta: number) => {
  editorRotation.value = (editorRotation.value + delta + 360) % 360
}

const clampZoom = (value: number) => Math.min(3, Math.max(1, value))

const onCanvasWheel = (event: WheelEvent) => {
  if (!editorImage.value) {
    return
  }
  const delta = event.deltaY < 0 ? 0.06 : -0.06
  editorZoom.value = clampZoom(editorZoom.value + delta)
}

const onCanvasPointerDown = (event: PointerEvent) => {
  if (!editorImage.value) {
    return
  }
  isDragging.value = true
  dragStart.value = {
    x: event.clientX,
    y: event.clientY,
    ox: editorOffsetX.value,
    oy: editorOffsetY.value,
  }
}

const onWindowPointerMove = (event: PointerEvent) => {
  if (!isDragging.value) {
    return
  }
  const dx = event.clientX - dragStart.value.x
  const dy = event.clientY - dragStart.value.y
  editorOffsetX.value = dragStart.value.ox + dx
  editorOffsetY.value = dragStart.value.oy + dy
}

const onWindowPointerUp = () => {
  isDragging.value = false
}

const buildEditedAvatarFile = async (): Promise<File | null> => {
  if (!selectedFile.value || !editorImage.value || !canvasRef.value) {
    return null
  }
  const preview = canvasRef.value
  const outSize = 512
  const cropSize = Math.max(80, Math.floor(Math.min(preview.width, preview.height) * editorCropRatio.value))
  const cropX = Math.floor((preview.width - cropSize) / 2)
  const cropY = Math.floor((preview.height - cropSize) / 2)

  const outCanvas = document.createElement('canvas')
  outCanvas.width = outSize
  outCanvas.height = outSize
  const ctx = outCanvas.getContext('2d')
  if (!ctx) {
    return null
  }

  const image = editorImage.value
  const baseScale = Math.max(cropSize / image.width, cropSize / image.height)
  const scale = baseScale * editorZoom.value
  const ratio = outSize / cropSize
  const rad = (editorRotation.value * Math.PI) / 180

  ctx.fillStyle = '#111'
  ctx.fillRect(0, 0, outSize, outSize)
  ctx.save()
  ctx.translate((preview.width / 2 + editorOffsetX.value - cropX) * ratio, (preview.height / 2 + editorOffsetY.value - cropY) * ratio)
  ctx.rotate(rad)
  ctx.scale(scale * ratio, scale * ratio)
  ctx.drawImage(image, -image.width / 2, -image.height / 2, image.width, image.height)
  ctx.restore()

  const mimeType = selectedFile.value.type && allowedMime.has(selectedFile.value.type) ? selectedFile.value.type : 'image/png'
  const blob = await new Promise<Blob | null>((resolve) => {
    outCanvas.toBlob((value) => resolve(value), mimeType, 0.92)
  })
  if (!blob) {
    return null
  }
  const suffixMap: Record<string, string> = {
    'image/png': '.png',
    'image/jpeg': '.jpg',
    'image/webp': '.webp',
  }
  const suffix = suffixMap[mimeType] || '.png'
  return new File([blob], `avatar${suffix}`, { type: mimeType })
}

const saveAvatar = async () => {
  if (!selectedFile.value || uploading.value) {
    return
  }
  uploading.value = true
  try {
    const file = await buildEditedAvatarFile()
    if (!file) {
      message.error(t('settings.avatar.uploadFailTitle'), t('settings.avatar.uploadFailMessage'))
      return
    }
    await uploadAvatar(file)
    authStore.me = await getMe()
    avatarModalOpen.value = false
    clearSelectedAvatar()
    message.success(t('settings.avatar.uploadSuccessTitle'))
  } catch (error) {
    message.error(
      t('settings.avatar.uploadFailTitle'),
      error instanceof Error ? error.message : t('settings.avatar.uploadFailMessage'),
    )
  } finally {
    uploading.value = false
  }
}

const saveNickname = async () => {
  if (savingNickname.value) {
    return
  }
  const nickname = profileNickname.value.trim()
  const oldNickname = authStore.me?.nickname || ''
  if (nickname === oldNickname) {
    message.warning(t('settings.profile.noChange'))
    return
  }
  savingNickname.value = true
  try {
    const updated = await updateMe({ nickname })
    authStore.me = { ...(authStore.me || {}), ...updated }
    syncProfileFromStore()
    editingNickname.value = false
    message.success(t('settings.profile.saveSuccessTitle'))
  } catch (error) {
    message.error(
      t('settings.profile.saveFailTitle'),
      error instanceof Error ? error.message : t('settings.profile.saveFailMessage'),
    )
  } finally {
    savingNickname.value = false
  }
}

const saveMail = async () => {
  if (savingMail.value) {
    return
  }
  const mail = profileMail.value.trim()
  const oldMail = authStore.me?.mail || ''
  if (mail === oldMail) {
    message.warning(t('settings.profile.noChange'))
    return
  }
  savingMail.value = true
  try {
    const updated = await updateMe({ mail })
    authStore.me = { ...(authStore.me || {}), ...updated }
    syncProfileFromStore()
    editingMail.value = false
    message.success(t('settings.profile.saveSuccessTitle'))
  } catch (error) {
    message.error(
      t('settings.profile.saveFailTitle'),
      error instanceof Error ? error.message : t('settings.profile.saveFailMessage'),
    )
  } finally {
    savingMail.value = false
  }
}

const openPasswordModal = () => {
  passwordModalOpen.value = true
}

const closePasswordModal = () => {
  if (savingPassword.value) {
    return
  }
  passwordModalOpen.value = false
  currentPassword.value = ''
  newPassword.value = ''
  confirmNewPassword.value = ''
}

const savePassword = async () => {
  if (savingPassword.value) {
    return
  }
  if (!currentPassword.value.trim()) {
    message.warning(t('settings.profile.currentPasswordRequired'))
    return
  }
  if (!newPassword.value.trim()) {
    message.warning(t('settings.profile.newPasswordRequired'))
    return
  }
  if (newPassword.value !== confirmNewPassword.value) {
    message.warning(t('settings.profile.passwordMismatch'))
    return
  }
  savingPassword.value = true
  try {
    await updateMe({
      current_password: currentPassword.value,
      new_password: newPassword.value,
    })
    closePasswordModal()
    message.success(t('settings.profile.saveSuccessTitle'))
  } catch (error) {
    message.error(
      t('settings.profile.saveFailTitle'),
      error instanceof Error ? error.message : t('settings.profile.saveFailMessage'),
    )
  } finally {
    savingPassword.value = false
  }
}

const toggleNicknameEdit = () => {
  editingNickname.value = !editingNickname.value
  if (!editingNickname.value) {
    profileNickname.value = authStore.me?.nickname || ''
  }
}

const toggleMailEdit = () => {
  editingMail.value = !editingMail.value
  if (!editingMail.value) {
    profileMail.value = authStore.me?.mail || ''
  }
}

watch([editorZoom, editorRotation, editorCropRatio, editorOffsetX, editorOffsetY, editorImage], () => {
  drawAvatarEditor()
})

onMounted(() => {
  window.addEventListener('pointermove', onWindowPointerMove)
  window.addEventListener('pointerup', onWindowPointerUp)
})

onBeforeUnmount(() => {
  revokeLocalPreview()
  revokeEditorImage()
  window.removeEventListener('pointermove', onWindowPointerMove)
  window.removeEventListener('pointerup', onWindowPointerUp)
})
</script>

<template>
  <section class="page">
    <PageHeader :title="t('settings.title')" :subtitle="t('settings.subtitle')" />

    <div class="settings__card">
      <div class="settings__card-title">{{ t('settings.profile.title') }}</div>
      <p class="settings__card-desc">{{ t('settings.profile.description') }}</p>

      <div class="settings__row">
        <div class="settings__label">{{ t('settings.avatar.title') }}</div>
        <div class="settings__value settings__value--avatar">
          <div class="settings__avatar">
            <img v-if="displayAvatar && !avatarFailed" :src="displayAvatar" :alt="userLabel" @error="onAvatarError" />
            <span v-else>{{ initials }}</span>
          </div>
        </div>
        <div class="settings__actions">
          <Button variant="secondary" @click="openAvatarModal">{{ t('settings.profile.change') }}</Button>
        </div>
      </div>

      <div class="settings__row">
        <div class="settings__label">{{ t('settings.profile.username') }}</div>
        <div class="settings__value">{{ authStore.me?.username || '-' }}</div>
        <div class="settings__actions"></div>
      </div>

      <div class="settings__row">
        <div class="settings__label">{{ t('settings.profile.nickname') }}</div>
        <div class="settings__value">
          <span v-if="!editingNickname">{{ authStore.me?.nickname || '-' }}</span>
          <Input v-else v-model="profileNickname" />
        </div>
        <div class="settings__actions">
          <Button v-if="!editingNickname" variant="secondary" @click="toggleNicknameEdit">{{ t('settings.profile.change') }}</Button>
          <template v-else>
            <Button :loading="savingNickname" @click="saveNickname">{{ t('settings.profile.saveButton') }}</Button>
            <Button variant="ghost" @click="toggleNicknameEdit">{{ t('settings.profile.cancel') }}</Button>
          </template>
        </div>
      </div>

      <div class="settings__row">
        <div class="settings__label">{{ t('settings.profile.mail') }}</div>
        <div class="settings__value">
          <span v-if="!editingMail">{{ authStore.me?.mail || '-' }}</span>
          <Input v-else v-model="profileMail" type="email" />
        </div>
        <div class="settings__actions">
          <Button v-if="!editingMail" variant="secondary" @click="toggleMailEdit">{{ t('settings.profile.change') }}</Button>
          <template v-else>
            <Button :loading="savingMail" @click="saveMail">{{ t('settings.profile.saveButton') }}</Button>
            <Button variant="ghost" @click="toggleMailEdit">{{ t('settings.profile.cancel') }}</Button>
          </template>
        </div>
      </div>

      <div class="settings__row">
        <div class="settings__label">{{ t('settings.profile.password') }}</div>
        <div class="settings__value">********</div>
        <div class="settings__actions">
          <Button variant="secondary" @click="openPasswordModal">{{ t('settings.profile.change') }}</Button>
        </div>
      </div>
    </div>

    <Modal :open="avatarModalOpen" :title="t('settings.avatar.title')" @close="closeAvatarModal">
      <div class="settings__avatar-modal">
        <input
          ref="fileInputRef"
          class="settings__avatar-input"
          type="file"
          accept="image/png,image/jpeg,image/webp"
          @change="onSelectAvatar"
        />
        <canvas
          ref="canvasRef"
          class="settings__avatar-canvas"
          width="320"
          height="320"
          @pointerdown="onCanvasPointerDown"
          @wheel.prevent="onCanvasWheel"
        ></canvas>
        <div class="settings__avatar-tip">{{ t('settings.avatar.tip') }}</div>
        <div class="settings__editor-controls">
          <label class="settings__control">
            <span>{{ t('settings.avatar.zoom') }}</span>
            <input v-model.number="editorZoom" type="range" min="1" max="3" step="0.01" />
          </label>
          <label class="settings__control">
            <span>{{ t('settings.avatar.crop') }}</span>
            <input v-model.number="editorCropRatio" type="range" min="0.5" max="1" step="0.01" />
          </label>
          <div class="settings__rotate">
            <Button variant="secondary" @click="rotateEditor(-90)">{{ t('settings.avatar.rotateLeft') }}</Button>
            <Button variant="secondary" @click="rotateEditor(90)">{{ t('settings.avatar.rotateRight') }}</Button>
            <Button variant="ghost" @click="resetAvatarEditor">{{ t('settings.avatar.reset') }}</Button>
          </div>
        </div>
      </div>
      <template #footer>
        <Button variant="ghost" :disabled="uploading" @click="closeAvatarModal">
          {{ t('settings.profile.cancel') }}
        </Button>
        <Button variant="secondary" :disabled="uploading" @click="openFilePicker">
          {{ t('settings.avatar.selectButton') }}
        </Button>
        <Button :loading="uploading" :disabled="!selectedFile" @click="saveAvatar">
          {{ t('settings.profile.saveButton') }}
        </Button>
      </template>
    </Modal>

    <Modal :open="passwordModalOpen" :title="t('settings.profile.changePasswordTitle')" @close="closePasswordModal">
      <div class="settings__password-grid settings__password-grid--modal">
        <Input v-model="currentPassword" :label="t('settings.profile.currentPassword')" type="password" />
        <Input v-model="newPassword" :label="t('settings.profile.newPassword')" type="password" />
        <Input
          v-model="confirmNewPassword"
          :label="t('settings.profile.confirmNewPassword')"
          type="password"
        />
      </div>
      <template #footer>
        <Button variant="ghost" :disabled="savingPassword" @click="closePasswordModal">
          {{ t('settings.profile.cancel') }}
        </Button>
        <Button :loading="savingPassword" @click="savePassword">
          {{ t('settings.profile.saveButton') }}
        </Button>
      </template>
    </Modal>
  </section>
</template>

<style scoped>
.page {
  display: grid;
  gap: var(--space-4);
  grid-template-rows: auto auto;
  align-content: start;
  min-height: 0;
}

.settings__card {
  padding: var(--space-6);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  display: grid;
  gap: var(--space-4);
}

.settings__card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
}

.settings__card-desc {
  margin: 0;
  font-size: 13px;
  color: var(--color-muted);
}

.settings__row {
  display: grid;
  grid-template-columns: 120px 1fr auto;
  align-items: center;
  gap: var(--space-4);
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border);
}

.settings__label {
  font-size: 13px;
  color: var(--color-muted);
}

.settings__value {
  min-height: 36px;
  display: flex;
  align-items: center;
  color: var(--color-text);
}

.settings__value--avatar {
  gap: var(--space-3);
}

.settings__actions {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}

.settings__avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  border: 1px solid var(--color-border);
  background: var(--color-surface-2);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text);
  font-size: 22px;
  font-weight: 700;
  overflow: hidden;
}

.settings__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.settings__avatar-input {
  display: none;
}

.settings__avatar-tip {
  font-size: 12px;
  color: var(--color-muted);
}

.settings__avatar-modal {
  display: grid;
  justify-items: center;
  gap: var(--space-3);
  padding-top: var(--space-2);
}

.settings__avatar-canvas {
  width: 320px;
  height: 320px;
  max-width: 100%;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  touch-action: none;
  cursor: move;
}


.settings__editor-controls {
  width: min(320px, 100%);
  display: grid;
  gap: var(--space-2);
}

.settings__control {
  display: grid;
  gap: var(--space-1);
  font-size: 12px;
  color: var(--color-muted);
}

.settings__rotate {
  display: inline-flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.settings__password-grid {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
}

.settings__password-grid--modal {
  grid-template-columns: 1fr;
}

@media (max-width: 768px) {
  .settings__row {
    grid-template-columns: 72px minmax(0, 1fr) auto;
    align-items: center;
    gap: var(--space-2);
  }

  .settings__actions {
    flex-wrap: nowrap;
    white-space: nowrap;
  }

  .settings__actions :deep(.btn) {
    min-height: 32px;
    padding: 0 var(--space-2);
    font-size: 12px;
  }

  .settings__label {
    font-size: 12px;
  }

  .settings__avatar {
    width: 52px;
    height: 52px;
    font-size: 18px;
  }

  .settings__password-grid {
    grid-template-columns: 1fr;
  }

}
</style>
