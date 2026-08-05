const MARKDOWN_EXTENSIONS = new Set(['.md', '.markdown', '.mdx'])
const IMAGE_EXTENSIONS = new Set([
  '.apng',
  '.avif',
  '.png',
  '.jpg',
  '.jpeg',
  '.gif',
  '.bmp',
  '.webp',
  '.svg'
])
const PDF_EXTENSIONS = new Set(['.pdf'])
const HTML_EXTENSIONS = new Set(['.html', '.htm'])
// 需与后端 backend/package/yuxi/services/file_preview.py 的 _OFFICE_EXTENSIONS 保持一致
const OFFICE_EXTENSIONS = new Set([
  '.docx',
  '.doc',
  '.pptx',
  '.ppt',
  '.xlsx',
  '.xls',
  '.odt',
  '.ods',
  '.odp'
])
// preset-engineering 覆盖的格式（XMind / CAD / 3D / 压缩包 / PSD / Geo / Typst / EDA / Drawing）。
// 与 office 共用"原样吐字节 + FileViewer 渲染"通道，后端 detect_preview_type 命中后会
// 返回 preview_type="office"（见 backend/_ENGINEERING_EXTENSIONS）。
const ENGINEERING_EXTENSIONS = new Set([
  // XMind
  '.xmind',
  // 压缩包
  '.zip', '.zipx', '.7z', '.rar', '.tar', '.gz', '.gzip', '.tgz',
  '.bz2', '.bzip2', '.tbz', '.tbz2', '.xz', '.txz', '.lzma', '.zst',
  '.tzst', '.cab', '.ar', '.cpio', '.iso', '.xar', '.lha', '.lzh',
  '.jar', '.war', '.ear', '.apk', '.cbz', '.cbr',
  // CAD
  '.dxf', '.dwg', '.dwf', '.dwfx', '.xps',
  // 3D 模型
  '.glb', '.gltf', '.obj', '.stl', '.ply', '.fbx', '.dae', '.3ds',
  '.3mf', '.amf', '.usd', '.usda', '.usdc', '.usdz', '.kmz',
  '.step', '.stp', '.iges', '.igs', '.ifc', '.3dm', '.brep',
  '.pcd', '.wrl', '.vrml', '.xyz', '.vtk', '.vtp',
  // Geo
  '.geojson', '.kml', '.gpx', '.shp',
  // Typst
  '.typ', '.typst',
  // EDA
  '.olb', '.dra', '.gds', '.oas', '.oasis',
  // Drawing
  '.excalidraw', '.drawio', '.dio', '.mermaid', '.mmd', '.plantuml', '.puml',
  // PSD
  '.psd', '.psb'
])
const TEXT_EXTENSIONS = new Set([
  '.txt',
  '.text',
  '.log',
  '.json',
  '.jsonl',
  '.yaml',
  '.yml',
  '.toml',
  '.ini',
  '.cfg',
  '.conf',
  '.csv',
  '.tsv',
  '.py',
  '.js',
  '.ts',
  '.jsx',
  '.tsx',
  '.vue',
  '.html',
  '.htm',
  '.css',
  '.less',
  '.scss',
  '.xml',
  '.sql',
  '.sh',
  '.bash',
  '.zsh',
  '.fish',
  '.env',
  '.dockerfile',
  '.gitignore'
])
const CODE_LANGUAGE_ALIASES = {
  js: 'javascript',
  ts: 'typescript',
  py: 'python',
  sh: 'bash',
  shell: 'bash',
  yml: 'yaml',
  docker: 'dockerfile'
}

export const normalizeCodeLanguage = (lang) => {
  const language = String(lang || '')
    .trim()
    .split(/[\s:,]/)[0]
    .toLowerCase()

  return CODE_LANGUAGE_ALIASES[language] || language
}

const CODE_LANGUAGE_MAP = {
  '.py': 'python',
  '.js': 'javascript',
  '.mjs': 'javascript',
  '.cjs': 'javascript',
  '.ts': 'typescript',
  '.tsx': 'tsx',
  '.jsx': 'jsx',
  '.vue': 'xml',
  '.html': 'xml',
  '.htm': 'xml',
  '.xml': 'xml',
  '.css': 'css',
  '.less': 'less',
  '.scss': 'scss',
  '.json': 'json',
  '.yaml': 'yaml',
  '.yml': 'yaml',
  '.toml': 'ini',
  '.ini': 'ini',
  '.cfg': 'ini',
  '.conf': 'ini',
  '.sh': 'bash',
  '.bash': 'bash',
  '.zsh': 'bash',
  '.fish': 'bash',
  '.sql': 'sql',
  '.java': 'java',
  '.kt': 'kotlin',
  '.go': 'go',
  '.rs': 'rust',
  '.php': 'php',
  '.rb': 'ruby',
  '.c': 'c',
  '.h': 'c',
  '.cpp': 'cpp',
  '.cc': 'cpp',
  '.cxx': 'cpp',
  '.hpp': 'cpp',
  '.cs': 'csharp',
  '.swift': 'swift',
  '.dockerfile': 'dockerfile'
}

export const getPreviewFileExtension = (path) => {
  const normalizedPath = String(path || '')
    .trim()
    .toLowerCase()
  if (!normalizedPath) return ''

  const fileName = normalizedPath.split('/').pop() || ''
  const dotIndex = fileName.lastIndexOf('.')
  if (dotIndex <= 0) return ''
  return fileName.slice(dotIndex)
}

export const isMarkdownPreview = (path, previewType) => {
  if (previewType === 'markdown') return true
  return MARKDOWN_EXTENSIONS.has(getPreviewFileExtension(path))
}

export const getPreviewTypeByPath = (path) => {
  const extension = getPreviewFileExtension(path)
  if (IMAGE_EXTENSIONS.has(extension)) return 'image'
  if (PDF_EXTENSIONS.has(extension)) return 'pdf'
  if (MARKDOWN_EXTENSIONS.has(extension)) return 'markdown'
  if (HTML_EXTENSIONS.has(extension)) return 'html'
  if (OFFICE_EXTENSIONS.has(extension) || ENGINEERING_EXTENSIONS.has(extension)) return 'office'
  if (TEXT_EXTENSIONS.has(extension)) return 'text'
  return 'unsupported'
}

export const getCodeLanguageByPath = (path) =>
  normalizeCodeLanguage(CODE_LANGUAGE_MAP[getPreviewFileExtension(path)] || '')

export const isHtmlPreview = (path) => HTML_EXTENSIONS.has(getPreviewFileExtension(path))

export const getPreviewTypeByContentType = (contentType) => {
  const normalized = String(contentType || '').toLowerCase()
  if (normalized.includes('application/pdf')) return 'pdf'
  if (normalized.startsWith('image/')) return 'image'
  if (normalized.includes('text/markdown')) return 'markdown'
  if (normalized.includes('text/html')) return 'html'
  if (normalized.startsWith('text/')) return 'text'
  if (normalized.includes('application/json')) return 'json'
  // 办公文档（OOXML / ODF / RTF 等）：交给前端 File Viewer 渲染
  if (
    normalized.includes('officedocument') ||
    normalized.includes('ms-word') ||
    normalized.includes('ms-powerpoint') ||
    normalized.includes('ms-excel') ||
    normalized.includes('opendocument') ||
    normalized.includes('wordprocessingml') ||
    normalized.includes('spreadsheetml') ||
    normalized.includes('presentationml') ||
    normalized === 'application/rtf' ||
    normalized.includes('application/msword') ||
    normalized.includes('application/vnd.ms-')
  ) {
    return 'office'
  }
  return 'unsupported'
}

export const isOfficePreview = (path) => {
  const extension = getPreviewFileExtension(path)
  // 名称沿用 isOfficePreview，但同时覆盖 preset-engineering 格式：
  // 后端对二者都返回 preview_type="office" 并原样透传字节，
  // 前端 FileViewer 合并了 office + engineering preset 后都能渲染。
  return OFFICE_EXTENSIONS.has(extension) || ENGINEERING_EXTENSIONS.has(extension)
}

export const normalizePreviewResponse = async (response, baseFile = {}) => {
  const contentType = response?.headers?.get?.('content-type') || ''

  if (contentType.includes('application/json')) {
    const payload = await response.json()
    const previewType = payload.preview_type || payload.previewType || payload.kind || 'text'
    return {
      ...baseFile,
      ...payload,
      content: payload.content ?? '',
      previewType,
      supported: payload.supported !== false,
      message: payload.message || '',
      previewUrl: ''
    }
  }

  const previewType =
    response?.headers?.get?.('x-yuxi-preview-type') || getPreviewTypeByContentType(contentType)
  const blob = await response.blob()

  return {
    ...baseFile,
    content: null,
    previewType,
    supported: previewType !== 'unsupported',
    message: previewType === 'unsupported' ? '当前文件暂不支持预览，请下载后查看' : '',
    // 办公文档由 File Viewer 直接渲染原始字节，需要 Blob 而非 object URL
    rawBlob: blob,
    previewUrl: window.URL.createObjectURL(blob)
  }
}

// 从 Content-Disposition 响应头解析真实文件名。
// File Viewer 纯靠 filename 扩展名识别格式，而知识库列表 entry 的 name 可能不带扩展名，
// 必须从下载接口的 Content-Disposition（后端返回的上传原始文件名）取真实名，否则误判为 unsupported。
// 兼容 RFC 5987 写法（filename*=UTF-8''xxx.docx）与退化写法（filename=xxx.docx）。
export const parseContentDispositionFilename = (header) => {
  if (!header) return ''
  const rfc5987Match = header.match(/filename\*\s*=\s*[^']*''\s*([^;]+)/i)
  if (rfc5987Match && rfc5987Match[1]) {
    try {
      return decodeURIComponent(rfc5987Match[1].trim())
    } catch {
      return rfc5987Match[1].trim()
    }
  }
  const legacyMatch = header.match(/filename\s*=\s*("?)([^";]+)\1/i)
  if (legacyMatch && legacyMatch[2]) {
    return legacyMatch[2].trim()
  }
  return ''
}
