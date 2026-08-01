<template>
  <a-drawer
    :open="open"
    :title="mode === 'edit' ? '编辑数字警员' : '新建数字警员'"
    width="560"
    :mask-closable="false"
    @close="emit('update:open', false)"
  >
    <!-- 图标 + 名称 -->
    <div class="form-profile-header">
      <div class="icon-upload-wrap">
        <a-upload
          :show-upload-list="false"
          :before-upload="beforeIconUpload"
          :disabled="iconUploading"
          accept="image/*"
        >
          <div
            class="icon-upload-box"
            :class="{ uploading: iconUploading, 'has-icon': form.icon }"
          >
            <FallbackAvatar
              v-if="form.icon"
              :src="form.icon"
              :name="form.name || '智能体'"
              :seed="form.name"
              kind="agent"
              :size="56"
              shape="rounded"
            />
            <template v-else>
              <Upload v-if="!iconUploading" :size="20" />
              <RefreshCw v-else :size="20" class="spinning" />
              <span>{{ form.icon ? '更换' : '上传' }}图标</span>
            </template>
          </div>
        </a-upload>
      </div>
      <div class="name-field">
        <a-form-item label="名称" name="name" :rules="[{ required: true, message: '请输入数字警员名称' }]">
          <a-input
            ref="nameInputRef"
            v-model:value="form.name"
            placeholder="如：资金分析师、笔录分析师…"
            allow-clear
          />
        </a-form-item>
      </div>
    </div>

    <a-form ref="formRef" :model="form" layout="vertical">
      <a-form-item label="描述" name="description">
        <a-textarea
          v-model:value="form.description"
          :rows="3"
          placeholder="简要描述该数字警员的定位与能力（可选）"
          allow-clear
        />
      </a-form-item>

      <!-- 共享权限 -->
      <div class="share-block">
        <div class="section-label">共享权限</div>
        <ShareConfigForm
          ref="shareConfigRef"
          v-model="shareConfig"
          :allowed-access-levels="allowedAccessLevels"
        />
      </div>
    </a-form>

    <template #footer>
      <div class="drawer-footer">
        <a-button @click="emit('update:open', false)">取消</a-button>
        <a-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ mode === 'edit' ? '保存' : '创建' }}
        </a-button>
      </div>
    </template>
  </a-drawer>
</template>

<script setup>
import { ref, reactive, watch, nextTick, computed } from 'vue'
import { Upload, RefreshCw } from 'lucide-vue-next'
import { message } from 'ant-design-vue'
import { policeAgentApi } from '@/apis/police_api'
import { userApi } from '@/apis/user_api'
import ShareConfigForm from '@/components/ShareConfigForm.vue'
import FallbackAvatar from '@/components/common/FallbackAvatar.vue'
import { useUserStore } from '@/stores/user'
import { storeToRefs } from 'pinia'
import { MAX_IMAGE_UPLOAD_SIZE_BYTES, MAX_IMAGE_UPLOAD_SIZE_MB } from '@/utils/upload_limits'

const props = defineProps({
  open: { type: Boolean, default: false },
  mode: { type: String, default: 'create' }, // 'create' | 'edit'
  agent: { type: Object, default: null },
})
const emit = defineEmits(['update:open', 'success'])

const userStore = useUserStore()
const { isAdmin } = storeToRefs(userStore)

const formRef = ref()
const nameInputRef = ref()
const shareConfigRef = ref()
const submitting = ref(false)
const iconUploading = ref(false)

const allowedAccessLevels = computed(() => {
  if (isAdmin.value) return ['global', 'department', 'user']
  return ['user']
})

/** 共享权限：管理员默认全局，普通用户默认仅自己 */
const defaultShareConfig = () => ({
  access_level: isAdmin.value ? 'global' : 'user',
  department_ids: [],
  user_uids: userStore.uid ? [userStore.uid] : [],
})

const shareConfig = ref(defaultShareConfig())

const emptyForm = () => ({
  name: '',
  description: '',
  icon: '',
})

const form = reactive(emptyForm())

// 打开时聚焦名称输入框 & 回显数据
watch(
  () => props.open,
  async (val) => {
    if (!val) return
    formRef.value?.clearValidate?.()
    if (props.mode === 'edit' && props.agent) {
      const a = props.agent
      Object.assign(form, {
        name: a.name || '',
        description: a.description || '',
        icon: a.icon || '',
      })
      // 回显共享权限（优先使用 agent 自身的 share_config，否则用默认值）
      shareConfig.value = a.share_config
        ? { ...a.share_config }
        : defaultShareConfig()
    } else {
      Object.assign(form, emptyForm())
      shareConfig.value = defaultShareConfig()
    }
    // 聚焦名称输入框
    await nextTick()
    nameInputRef.value?.focus?.()
  }
)

/* ---- 图标上传 ---- */
function beforeIconUpload(file) {
  if (!file.type.startsWith('image/')) {
    message.error('只能上传图片文件')
    return false
  }
  if (file.size > MAX_IMAGE_UPLOAD_SIZE_BYTES) {
    message.error(`图片大小不能超过 ${MAX_IMAGE_UPLOAD_SIZE_MB}MB`)
    return false
  }
  uploadIcon(file)
  return false
}

async function uploadIcon(file) {
  iconUploading.value = true
  try {
    const data = await userApi.uploadImage(file)
    form.icon = data.image_url || data.url || ''
    message.success('图标已上传')
  } catch (e) {
    message.error('图标上传失败')
  } finally {
    iconUploading.value = false
  }
}

/* ---- 提交 ---- */
async function handleSubmit() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  // 校验共享权限
  const shareValidation = shareConfigRef.value?.validate?.()
  if (shareValidation && !shareValidation.valid) {
    message.error(shareValidation.message)
    return
  }

  submitting.value = true

  // 构造精简 payload，仅传核心字段
  const payload = {
    name: form.name.trim(),
    description: form.description.trim() || null,
    icon: form.icon.trim() || null,
    share_config: normalizeShareConfig(),
  }

  try {
    if (props.mode === 'edit' && props.agent) {
      payload.badge_number = props.agent.badge_number || null
      await policeAgentApi.update(props.agent.id, payload)
      message.success('数字警员已更新')
    } else {
      await policeAgentApi.create(payload)
      message.success('数字警员已创建，可立即发起对话')
    }
    emit('update:open', false)
    emit('success')
  } catch (e) {
    message.error((props.mode === 'edit' ? '更新' : '创建') + '失败: ' + (e.message || e))
  } finally {
    submitting.value = false
  }
}

/** 将共享权限组件的值规整为后端格式 */
function normalizeShareConfig() {
  const cfg = shareConfig.value || defaultShareConfig()
  const level = cfg.access_level || 'global'
  return {
    access_level: level,
    department_ids: level === 'department' ? (cfg.department_ids || []) : [],
    user_uids: level === 'user' ? (cfg.user_uids || []) : [],
  }
}
</script>

<style scoped>
.form-profile-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 18px;
}

.icon-upload-wrap {
  flex-shrink: 0;
}

.icon-upload-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  width: 56px;
  height: 56px;
  border-radius: 12px;
  border: 1px dashed var(--gray-300);
  background: var(--gray-0);
  color: var(--gray-500);
  font-size: 11px;
  cursor: pointer;
  transition: border-color 0.16s, background 0.16s;

  &:hover,
  &:focus-within {
    border-color: var(--main-400);
    background: var(--main-10);
  }

  &.has-icon {
    border-style: solid;
    border-color: var(--gray-200);
  }

  &.uploading {
    cursor: wait;
  }
}

.name-field {
  flex: 1;
  min-width: 0;
}

.name-field :deep(.ant-form-item) {
  margin-bottom: 0;
}

.share-block {
  margin-top: 8px;
  padding-top: 16px;
  border-top: 1px solid var(--gray-150);
}

.section-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--gray-900);
  margin-bottom: 12px;
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
