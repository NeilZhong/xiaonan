<script setup>
/**
 * ★ 案件独立工作区 Tab — 树状文件列表
 * 民警在案件生命周期中提交的材料、任务阶段性成果统一存放在工作区。
 */
import { onMounted, ref, computed, watch } from 'vue'
import { policeWorkspaceApi } from '@/apis/police_api'
import { apiGet } from '@/apis/base'
import { message, Modal, Input } from 'ant-design-vue'
import {
  UploadOutlined, FolderOutlined, FolderOpenOutlined, FileOutlined,
  FileTextOutlined, FileImageOutlined, FilePdfOutlined,
  DownloadOutlined, DeleteOutlined, EditOutlined,
  PlusOutlined, ArrowLeftOutlined,
} from '@ant-design/icons-vue'

const props = defineProps({ caseId: { type: Number, required: true } })

const loading = ref(false)
const workspace = ref({})
const tree = ref([])
const currentFolderId = ref(null)
const expandedKeys = ref(new Set())
const newFolderName = ref('')
const renameValue = ref('')
const renameNodeId = ref(null)

const breadcrumb = computed(() => {
  const list = [{ id: null, name: '工作区' }]
  const findPath = (nodes, targetId) => {
    for (const n of nodes) {
      if (n.id === targetId) return [n]
      if (n.children?.length) {
        const sub = findPath(n.children, targetId)
        if (sub) return [n, ...sub]
      }
    }
    return null
  }
  if (currentFolderId.value) {
    const path = findPath(tree.value, currentFolderId.value)
    if (path) list.push(...path.map(n => ({ id: n.id, name: n.name })))
  }
  return list
})

const currentNodes = computed(() => {
  let nodes = tree.value
  if (currentFolderId.value) {
    const find = (list, id) => {
      for (const n of list) {
        if (n.id === id) return n.children || []
        if (n.children?.length) {
          const found = find(n.children, id)
          if (found) return found
        }
      }
      return list
    }
    nodes = find(tree.value, currentFolderId.value)
  }
  return [...nodes].sort((a, b) => {
    if (a.node_type === b.node_type) return a.name.localeCompare(b.name, 'zh-CN')
    return a.node_type === 'folder' ? -1 : 1
  })
})

const stats = computed(() => {
  const s = workspace.value.stats || {}
  return {
    evidence: s.evidence_count || 0,
    materials: s.material_count || 0,
    artifacts: s.artifact_count || 0,
    totalSize: s.total_size || 0,
  }
})

function formatSize(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0, v = bytes
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++ }
  return `${v.toFixed(1)} ${units[i]}`
}

function fileIcon(node) {
  if (node.node_type === 'folder') return expandedKeys.value.has(node.id) ? FolderOpenOutlined : FolderOutlined
  const mime = node.mime_type || ''
  const name = node.name || ''
  if (mime.startsWith('image/')) return FileImageOutlined
  if (mime.includes('pdf') || name.endsWith('.pdf')) return FilePdfOutlined
  if (/\.(md|txt|json|doc|docx)$/i.test(name)) return FileTextOutlined
  return FileOutlined
}

async function loadData() {
  loading.value = true
  try {
    const res = await policeWorkspaceApi.get(props.caseId)
    workspace.value = res.data.workspace || {}
    tree.value = res.data.tree || []
  } catch (e) {
    message.error('加载工作区失败')
  } finally {
    loading.value = false
  }
}

function enterFolder(node) {
  if (node.node_type !== 'folder') return
  currentFolderId.value = node.id
  expandedKeys.value.add(node.id)
}

function jumpFolder(id) {
  currentFolderId.value = id
}

function goBack() {
  const list = breadcrumb.value
  if (list.length > 1) {
    currentFolderId.value = list[list.length - 2].id
  }
}

function customRequest({ file, onSuccess, onError }) {
  policeWorkspaceApi.upload(props.caseId, currentFolderId.value, file)
    .then(() => { onSuccess({}, file); message.success(`${file.name} 上传成功`); loadData() })
    .catch((e) => { onError(); message.error(e?.response?.data?.message || '上传失败') })
}

async function createFolder() {
  if (!newFolderName.value.trim()) return
  try {
    await policeWorkspaceApi.createFolder(props.caseId, {
      name: newFolderName.value.trim(),
      parent_id: currentFolderId.value,
    })
    message.success('文件夹创建成功')
    newFolderName.value = ''
    await loadData()
  } catch (e) {
    message.error(e?.response?.data?.message || '创建失败')
  }
}

async function handleDownload(node) {
  try {
    const url = policeWorkspaceApi.download(props.caseId, node.id)
    const resp = await apiGet(url, {}, true, 'blob')
    const blob = await resp.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = node.name
    a.click()
    URL.revokeObjectURL(a.href)
  } catch (e) {
    message.error('下载失败')
  }
}

function confirmDelete(node) {
  Modal.confirm({
    title: `确认删除「${node.name}」？`,
    content: node.node_type === 'folder' ? '文件夹及其内容将被一并删除，且不可恢复。' : '文件删除后不可恢复。',
    okText: '删除',
    okType: 'danger',
    onOk: async () => {
      try {
        await policeWorkspaceApi.remove(props.caseId, node.id)
        message.success('已删除')
        await loadData()
      } catch (e) {
        message.error(e?.response?.data?.message || '删除失败')
      }
    },
  })
}

function startRename(node) {
  renameNodeId.value = node.id
  renameValue.value = node.name
}

async function submitRename() {
  if (!renameValue.value.trim() || !renameNodeId.value) return
  try {
    await policeWorkspaceApi.rename(props.caseId, {
      node_id: renameNodeId.value,
      name: renameValue.value.trim(),
    })
    renameNodeId.value = null
    renameValue.value = ''
    await loadData()
  } catch (e) {
    message.error(e?.response?.data?.message || '重命名失败')
  }
}

onMounted(loadData)
watch(() => props.caseId, () => { currentFolderId.value = null; loadData() })
</script>

<template>
  <div class="workspace-tab">
    <!-- 概览与统计 -->
    <div class="ws-overview">
      <div class="ws-overview-icon"><FolderOpenOutlined /></div>
      <div class="ws-overview-body">
        <div class="ws-overview-title">案件独立工作区</div>
        <div class="ws-overview-path">
          <span class="ws-label">存储路径</span>
          <code>{{ workspace.storage_prefix || 'cases/{case_number}/' }}</code>
          <a-tag size="small">MinIO: {{ workspace.storage_bucket || 'police-workspace' }}</a-tag>
        </div>
        <div class="ws-stats">
          <div class="ws-stat"><span class="ws-stat-num">{{ stats.evidence }}</span><span class="ws-stat-label">证据</span></div>
          <div class="ws-stat"><span class="ws-stat-num">{{ stats.materials }}</span><span class="ws-stat-label">材料</span></div>
          <div class="ws-stat"><span class="ws-stat-num">{{ stats.artifacts }}</span><span class="ws-stat-label">阶段性成果</span></div>
          <div class="ws-stat"><span class="ws-stat-num">{{ formatSize(stats.totalSize) }}</span><span class="ws-stat-label">总大小</span></div>
        </div>
      </div>
    </div>

    <!-- 工具栏 -->
    <div class="ws-toolbar">
      <a-breadcrumb class="ws-breadcrumb">
        <a-breadcrumb-item v-for="(item, idx) in breadcrumb" :key="item.id ?? 'root'">
          <a v-if="idx < breadcrumb.length - 1" @click="jumpFolder(item.id)">{{ item.name }}</a>
          <span v-else>{{ item.name }}</span>
        </a-breadcrumb-item>
      </a-breadcrumb>
      <div class="ws-actions">
        <a-button size="small" :disabled="!currentFolderId" @click="goBack">
          <template #icon><ArrowLeftOutlined /></template>返回
        </a-button>
        <a-input
          v-model:value="newFolderName"
          size="small"
          placeholder="新建文件夹"
          style="width: 160px"
          @pressEnter="createFolder"
        />
        <a-button size="small" type="primary" :disabled="!newFolderName.trim()" @click="createFolder">
          <template #icon><PlusOutlined /></template>新建
        </a-button>
        <a-upload :custom-request="customRequest" :show-upload-list="false">
          <a-button size="small" type="primary">
            <template #icon><UploadOutlined /></template>上传文件
          </a-button>
        </a-upload>
      </div>
    </div>

    <!-- 树状列表 -->
    <a-spin :spinning="loading">
      <div class="ws-tree">
        <div class="ws-tree-head">
          <span class="ws-tree-cell ws-tree-name">名称</span>
          <span class="ws-tree-cell ws-tree-size">大小</span>
          <span class="ws-tree-cell ws-tree-time">更新时间</span>
          <span class="ws-tree-cell ws-tree-actions">操作</span>
        </div>

        <div v-if="currentNodes.length" class="ws-tree-body">
          <div
            v-for="node in currentNodes"
            :key="node.id"
            class="ws-tree-row"
            :class="{ 'is-folder': node.node_type === 'folder' }"
            @dblclick="enterFolder(node)"
          >
            <span class="ws-tree-cell ws-tree-name">
              <component :is="fileIcon(node)" class="ws-row-icon" />
              <span v-if="renameNodeId !== node.id" class="ws-row-name" :title="node.name">{{ node.name }}</span>
              <div v-else class="ws-rename-wrap">
                <a-input v-model:value="renameValue" size="small" @pressEnter="submitRename" @blur="submitRename" />
              </div>
            </span>
            <span class="ws-tree-cell ws-tree-size">{{ node.size ? formatSize(node.size) : '-' }}</span>
            <span class="ws-tree-cell ws-tree-time">{{ node.updated_at?.substring(0, 16) || '-' }}</span>
            <span class="ws-tree-cell ws-tree-actions">
              <a-button v-if="node.node_type === 'file'" type="link" size="small" @click="handleDownload(node)">
                <template #icon><DownloadOutlined /></template>
              </a-button>
              <a-button type="link" size="small" @click="startRename(node)">
                <template #icon><EditOutlined /></template>
              </a-button>
              <a-button type="link" size="small" danger @click="confirmDelete(node)">
                <template #icon><DeleteOutlined /></template>
              </a-button>
            </span>
          </div>
        </div>

        <a-empty v-else description="当前文件夹为空" style="padding: 40px" />
      </div>
    </a-spin>
  </div>
</template>

<style scoped>
.workspace-tab { padding: 12px 0; }

/* 概览 */
.ws-overview {
  display: flex; gap: 14px; align-items: flex-start;
  padding: 16px; border: 1px solid var(--gray-50, #e2e8f0); border-radius: 12px;
  background: var(--gray-10, #f7fafc); margin-bottom: 16px;
}
.ws-overview-icon { font-size: 30px; color: var(--main-color, #24839b); padding-top: 2px; }
.ws-overview-body { flex: 1; min-width: 0; }
.ws-overview-title { font-size: 15px; font-weight: 600; margin-bottom: 6px; }
.ws-overview-path { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 12px; color: var(--gray-600, #4a5568); margin-bottom: 10px; }
.ws-label { color: var(--gray-500, #718096); }
.ws-overview-path code { background: var(--gray-0, #fff); padding: 2px 8px; border-radius: 6px; border: 1px solid var(--gray-50, #e2e8f0); font-family: monospace; }
.ws-stats { display: flex; gap: 24px; }
.ws-stat { display: flex; flex-direction: column; }
.ws-stat-num { font-size: 18px; font-weight: 600; color: var(--main-color, #24839b); }
.ws-stat-label { font-size: 12px; color: var(--gray-500, #718096); }

/* 工具栏 */
.ws-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; margin-bottom: 12px; flex-wrap: wrap;
}
.ws-breadcrumb { font-size: 13px; }
.ws-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

/* 树状列表 */
.ws-tree {
  border: 1px solid var(--gray-50, #e2e8f0); border-radius: 10px;
  background: var(--gray-0, #fff); overflow: hidden;
}
.ws-tree-head, .ws-tree-row {
  display: grid;
  grid-template-columns: 1fr 100px 150px 110px;
  align-items: center;
  padding: 0 16px;
  min-height: 44px;
  font-size: 13px;
}
.ws-tree-head {
  background: var(--gray-10, #f7fafc);
  color: var(--gray-600, #4a5568);
  font-weight: 500;
  border-bottom: 1px solid var(--gray-50, #e2e8f0);
}
.ws-tree-row {
  border-bottom: 1px solid var(--gray-50, #e2e8f0);
  cursor: pointer;
  transition: background 0.12s;
}
.ws-tree-row:last-child { border-bottom: none; }
.ws-tree-row:hover { background: var(--gray-10, #f7fafc); }
.ws-tree-row.is-folder { font-weight: 500; }
.ws-tree-cell { overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.ws-tree-name { display: flex; align-items: center; gap: 10px; }
.ws-row-icon { font-size: 18px; color: var(--main-color, #24839b); flex-shrink: 0; }
.ws-row-name { overflow: hidden; text-overflow: ellipsis; }
.ws-tree-size, .ws-tree-time { color: var(--gray-500, #718096); }
.ws-tree-actions { display: flex; gap: 2px; }
.ws-rename-wrap { width: 160px; }

@media (max-width: 768px) {
  .ws-tree-head, .ws-tree-row { grid-template-columns: 1fr 80px 90px; }
  .ws-tree-time { display: none; }
}
</style>
