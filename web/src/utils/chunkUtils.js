/**
 * Chunk 工具函数
 */

export const DEFAULT_CHUNK_PRESET_ID = 'general'

export const isPlainObject = (value) =>
  value !== null && typeof value === 'object' && !Array.isArray(value)

export const buildChunkParserConfigPayload = (source, { includeSizeOverlap = true } = {}) => {
  if (!isPlainObject(source)) {
    return {}
  }

  const config = {}
  if (includeSizeOverlap) {
    if (source.chunk_token_num !== undefined && source.chunk_token_num !== null) {
      config.chunk_token_num = source.chunk_token_num
    }
    if (source.overlapped_percent !== undefined && source.overlapped_percent !== null) {
      config.overlapped_percent = source.overlapped_percent
    }
  }
  if (source.delimiter) {
    config.delimiter = source.delimiter
  }

  return config
}

export const buildChunkParamsPayload = (source, options = {}) => {
  if (!isPlainObject(source)) {
    return {}
  }

  const payload = {}
  const chunkParserConfig = buildChunkParserConfigPayload(source.chunk_parser_config, options)
  if (Object.keys(chunkParserConfig).length > 0) {
    payload.chunk_parser_config = chunkParserConfig
  }
  if (source.chunk_preset_id) {
    payload.chunk_preset_id = source.chunk_preset_id
  }

  return payload
}

/**
 * 查找两个字符串的重叠部分
 * @param {string} str1 - 第一个字符串
 * @param {string} str2 - 第二个字符串
 * @returns {string} - 重叠部分的内容
 */
export function findOverlap(str1, str2) {
  if (!str1 || !str2) return ''

  const maxOverlap = Math.min(str1.length, str2.length)
  let overlap = ''

  // 从最长可能的重叠开始检查
  for (let i = maxOverlap; i > 10; i--) {
    const endStr1 = str1.slice(-i)
    const startStr2 = str2.slice(0, i)

    if (endStr1 === startStr2) {
      overlap = endStr1
      break
    }
  }

  return overlap
}

/**
 * 合并chunks并处理重叠内容
 * @param {Array} chunks - chunk数组，每个chunk包含id, content, chunk_order_index
 * @returns {Object} - 合并结果，包含content和chunks数组
 */
export function mergeChunks(chunks) {
  if (!chunks || chunks.length === 0) {
    return { content: '', chunks: [] }
  }

  // 按order排序
  const sorted = [...chunks].sort((a, b) => a.chunk_order_index - b.chunk_order_index)
  const merged = []
  let currentContent = ''

  for (let i = 0; i < sorted.length; i++) {
    const chunk = sorted[i]
    const content = chunk.content

    if (i === 0) {
      // 第一个chunk直接添加
      currentContent = content
      merged.push({
        ...chunk,
        startOffset: 0,
        endOffset: content.length
      })
    } else {
      // 查找重叠部分
      const overlap = findOverlap(currentContent, content)
      const newContent = content.slice(overlap.length)

      if (newContent.length > 0) {
        const startOffset = currentContent.length
        if (overlap.length > 0) {
          currentContent += newContent
        } else {
          currentContent += `\n${newContent}`
        }
        merged.push({
          ...chunk,
          startOffset,
          endOffset: currentContent.length
        })
      }
    }
  }

  return { content: currentContent, chunks: merged }
}

/**
 * 将文本分割成段落
 * @param {string} content - 文本内容
 * @returns {Array} - 段落数组
 */
export function splitIntoParagraphs(content) {
  if (!content) return []

  // 按换行符分割，保留空段落
  return content.split(/\n\n+/).filter((para) => para.trim() !== '')
}

/**
 * 为每个段落找到对应的chunk
 * @param {Array} paragraphs - 段落数组
 * @param {Array} mappedChunks - 映射后的chunks
 * @returns {Array} - 包含chunk信息的段落
 */
export function mapParagraphsToChunks(paragraphs, mappedChunks) {
  if (!paragraphs || !mappedChunks) return []

  let currentOffset = 0
  return paragraphs.map((paragraph) => {
    const paragraphLength = paragraph.length + 2 // +2 for the \n\n

    // 找到包含此位置的chunk
    const chunk =
      mappedChunks.find(
        (chunk) => currentOffset >= chunk.startOffset && currentOffset < chunk.endOffset
      ) || mappedChunks[0]

    const result = {
      content: paragraph,
      chunk,
      startOffset: currentOffset,
      endOffset: currentOffset + paragraphLength
    }

    currentOffset += paragraphLength
    return result
  })
}

/**
 * 归一化文本，用于相似度比较
 * @param {string} text - 原始文本
 * @returns {string} - 去除空白并小写后的文本
 */
const normalizeForDedup = (text) => String(text || '').replace(/\s+/g, '').toLowerCase()

/**
 * 计算两段文本基于字符 bigram 的 Jaccard 相似度
 * @param {string} a - 第一个文本
 * @param {string} b - 第二个文本
 * @returns {number} - 相似度 0~1
 */
export function computeContentSimilarity(a, b) {
  const na = normalizeForDedup(a)
  const nb = normalizeForDedup(b)

  if (na === nb) return 1
  if (!na || !nb) return 0

  // 互为子串时视为完全重复（检索返回的重叠切片常见这种情况）
  if (na.length > nb.length) {
    if (na.includes(nb)) return 1
  } else if (nb.includes(na)) {
    return 1
  }

  const buildBigrams = (s) => {
    const set = new Set()
    for (let i = 0; i < s.length - 1; i++) {
      set.add(s.slice(i, i + 2))
    }
    return set
  }

  const setA = buildBigrams(na)
  const setB = buildBigrams(nb)
  if (setA.size === 0 || setB.size === 0) return 0

  let intersection = 0
  for (const gram of setA) {
    if (setB.has(gram)) intersection++
  }
  return intersection / (setA.size + setB.size - intersection)
}

/**
 * 按内容相似度对 chunk 列表去重。
 * 重叠/近重复的 chunk 会合并为一条，保留最高 score 的元信息。
 * @param {Array} chunks - chunk 数组
 * @param {Object} options - 配置
 * @param {number} options.similarityThreshold - 判定为重复的相似度阈值，默认 0.85
 * @returns {Array} - 去重后的 chunk 数组
 */
export function deduplicateChunksByContent(chunks, { similarityThreshold = 0.85 } = {}) {
  if (!Array.isArray(chunks) || chunks.length === 0) return []

  const result = []

  for (const chunk of chunks) {
    const content = typeof chunk.content === 'string' ? chunk.content.trim() : ''
    if (!content) continue

    let duplicateOf = null
    for (const existing of result) {
      if (computeContentSimilarity(existing.content, content) >= similarityThreshold) {
        duplicateOf = existing
        break
      }
    }

    if (duplicateOf) {
      const score =
        typeof chunk.score === 'number'
          ? chunk.score
          : typeof chunk.metadata?.score === 'number'
            ? chunk.metadata.score
            : null
      const shouldUpgradeScore =
        score !== null && (typeof duplicateOf.score !== 'number' || score > duplicateOf.score)
      const shouldUpgradeContent = content.length > (duplicateOf.content || '').length

      if (shouldUpgradeScore) {
        duplicateOf.score = score
      }
      if (shouldUpgradeScore || shouldUpgradeContent) {
        if (duplicateOf.metadata && chunk.metadata) {
          duplicateOf.metadata = { ...duplicateOf.metadata, ...chunk.metadata }
        }
      }
      if (shouldUpgradeContent) {
        duplicateOf.content = content
      }
      continue
    }

    result.push({ ...chunk })
  }

  return result
}

/**
 * 获取chunk的预览文本
 * @param {string} content - chunk内容
 * @param {number} maxLength - 最大长度
 * @returns {string} - 预览文本
 */
export function getChunkPreview(content, maxLength = 100) {
  if (!content) return ''

  const text = content.replace(/\n+/g, ' ').trim()
  if (text.length <= maxLength) return text

  return text.slice(0, maxLength) + '...'
}
