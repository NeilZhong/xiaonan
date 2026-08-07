import { deduplicateChunksByContent } from './chunkUtils.js'

/**
 * 统一知识库检索工具名（新架构不再按知识库名注册工具）
 */
const KB_QUERY_TOOL_NAMES = new Set(['query_kb'])

/**
 * 消息处理工具类
 */
export class MessageProcessor {
  /**
   * 将工具结果与消息合并
   * @param {Array} msgs - 消息数组
   * @returns {Array} 合并后的消息数组
   */
  static convertToolResultToMessages(msgs) {
    const toolResponseMap = new Map()

    // 构建工具响应映射
    for (const item of msgs) {
      if (item.type === 'tool') {
        // 使用多种可能的ID字段来匹配工具调用
        const toolCallId = item.tool_call_id || item.id
        if (toolCallId) {
          toolResponseMap.set(toolCallId, item)
        }
      }
    }

    // 合并工具调用和响应
    const convertedMsgs = msgs.map((item) => {
      if (item.type === 'ai' && item.tool_calls && item.tool_calls.length > 0) {
        return {
          ...item,
          tool_calls: item.tool_calls.map((toolCall) => {
            const toolResponse = toolResponseMap.get(toolCall.id)
            return {
              ...toolCall,
              tool_call_result: toolResponse || null
            }
          })
        }
      }
      return item
    })

    return convertedMsgs
  }

  /**
   * 将服务器历史记录转换为对话格式
   * @param {Array} serverHistory - 服务器历史记录
   * @returns {Array} 对话数组
   */
  static convertServerHistoryToMessages(serverHistory) {
    // Filter out standalone 'tool' messages since tool results are already in AI messages' tool_calls
    // Backend new storage: tool results are embedded in AI messages' tool_calls array with tool_call_result field
    const filteredHistory = serverHistory.filter(
      (item) =>
        item.type !== 'tool' &&
        !(item.type === 'human' && item.extra_metadata?.source === 'ask_user_question_resume')
    )

    // 按照对话分组
    const conversations = []
    let currentConv = null

    for (const item of filteredHistory) {
      if (item.type === 'human') {
        // Start new conversation, finalize previous one
        if (currentConv) {
          // Find the last AI message and mark it as final
          for (let i = currentConv.messages.length - 1; i >= 0; i--) {
            if (currentConv.messages[i].type === 'ai') {
              currentConv.messages[i].isLast = true
              currentConv.status = 'finished'
              break
            }
          }
        }
        currentConv = {
          messages: [item],
          status: 'loading'
        }
        conversations.push(currentConv)
      } else if (item.type === 'ai' && currentConv) {
        currentConv.messages.push(item)
      }
    }

    // Mark the last conversation as finished
    if (currentConv && currentConv.messages.length > 0) {
      // Find the last AI message and mark it as final
      for (let i = currentConv.messages.length - 1; i >= 0; i--) {
        if (currentConv.messages[i].type === 'ai') {
          currentConv.messages[i].isLast = true
          currentConv.status = 'finished'
          break
        }
      }
    }

    return conversations
  }

  /**
   * 提取一轮对话中已成功登记的交付物路径。
   * @param {Object} conv - 单轮对话
   * @returns {Array<string>} 去重后的交付物路径
   */
  static extractArtifactsFromConversation(conv) {
    if (!conv || !Array.isArray(conv.messages)) return []

    const artifacts = []
    const seenPaths = new Set()
    for (const message of conv.messages) {
      if (message?.type !== 'ai' || !Array.isArray(message.tool_calls)) continue

      for (const toolCall of message.tool_calls) {
        const toolName = toolCall?.name || toolCall?.function?.name
        if (toolName !== 'present_artifacts') continue
        if (!toolCall.tool_call_result && toolCall.status !== 'success') continue

        let args = toolCall.args ?? toolCall.function?.arguments
        if (typeof args === 'string') {
          try {
            args = JSON.parse(args)
          } catch {
            continue
          }
        }

        const filepaths = Array.isArray(args?.filepaths) ? args.filepaths : []
        for (const filepath of filepaths) {
          const normalizedPath = typeof filepath === 'string' ? filepath.trim() : ''
          if (!normalizedPath || seenPaths.has(normalizedPath)) continue
          seenPaths.add(normalizedPath)
          artifacts.push(normalizedPath)
        }
      }
    }
    return artifacts
  }

  /**
   * 提取一轮对话中所有知识库检索块
   * @param {Object} conv - 单轮对话
   * @param {Array} databases - 知识库列表
   * @returns {Array} 归一化后的检索块
   */
  static extractKnowledgeChunksFromConversation(conv, databases = []) {
    if (!conv || !Array.isArray(conv.messages) || conv.messages.length === 0) return []

    const dbList = Array.isArray(databases) ? databases : []
    // 旧架构：每个知识库注册为同名工具
    const databaseNames = new Set(
      dbList.map((db) => db?.name).filter((name) => typeof name === 'string' && name.trim())
    )
    // 新架构：统一 query_kb 工具，按 kb_id 反查知识库名称
    const kbNameById = new Map(
      dbList
        .map((db) => [
          String(db?.kb_id ?? db?.db_id ?? '').trim(),
          typeof db?.name === 'string' ? db.name : ''
        ])
        .filter(([kbId]) => kbId)
    )

    const normalizedChunks = []
    const dedupSet = new Set()

    const appendChunk = (chunk, kbName) => {
      if (!chunk || typeof chunk !== 'object') return
      const content = typeof chunk.content === 'string' ? chunk.content.trim() : ''
      if (!content) return

      const metadata = chunk.metadata && typeof chunk.metadata === 'object' ? chunk.metadata : {}
      // SearchResultSchema.id 即 chunk_id，metadata 中不一定重复携带
      const chunkId = String(metadata.chunk_id || chunk.chunk_id || chunk.id || '').trim()
      const dedupKey = chunkId ? `${kbName}::${chunkId}` : `${kbName}::${content}`
      if (dedupSet.has(dedupKey)) return
      dedupSet.add(dedupKey)

      const score =
        typeof chunk.score === 'number'
          ? chunk.score
          : typeof metadata.score === 'number'
            ? metadata.score
            : null
      normalizedChunks.push({
        kb_name: kbName,
        content,
        score,
        metadata: {
          source: metadata.source || '',
          file_id: metadata.file_id || chunk.file_id || '',
          chunk_id: chunkId,
          chunk_index: metadata.chunk_index
        }
      })
    }

    const parseToolResultContent = (content) => {
      if (Array.isArray(content)) return content
      if (content && typeof content === 'object') return content
      if (typeof content === 'string') {
        try {
          return JSON.parse(content)
        } catch {
          return null
        }
      }
      return null
    }

    for (const msg of conv.messages) {
      if (!msg || msg.type !== 'ai' || !Array.isArray(msg.tool_calls)) continue

      for (const toolCall of msg.tool_calls) {
        const toolName = toolCall?.name || toolCall?.function?.name
        if (!toolName) continue

        const isLegacyKbTool = databaseNames.has(toolName)
        const isQueryKbTool = KB_QUERY_TOOL_NAMES.has(toolName)
        if (!isLegacyKbTool && !isQueryKbTool) continue

        const content = toolCall?.tool_call_result?.content
        const parsed = parseToolResultContent(content)
        if (!parsed) continue

        const resolveKbName = (kbId) => {
          if (isLegacyKbTool) return toolName
          const byResult = kbNameById.get(String(kbId || '').trim())
          if (byResult) return byResult
          const args = parseToolResultContent(toolCall?.args ?? toolCall?.function?.arguments)
          return kbNameById.get(String(args?.kb_id || '').trim()) || '知识库'
        }

        // Milvus / Dify: 直接是 chunks 数组
        if (Array.isArray(parsed)) {
          const kbName = resolveKbName('')
          for (const chunk of parsed) appendChunk(chunk, kbName)
          continue
        }

        // 新版 query_kb: SearchOutputSchema -> { kb_id, results: [...] }
        if (Array.isArray(parsed?.results)) {
          const kbName = resolveKbName(parsed.kb_id)
          for (const chunk of parsed.results) appendChunk(chunk, kbName)
          continue
        }

        const wrappedChunks = parsed?.data?.chunks
        if (Array.isArray(wrappedChunks)) {
          const kbName = resolveKbName(parsed?.kb_id)
          for (const chunk of wrappedChunks) appendChunk(chunk, kbName)
        }
      }
    }

    // 对检索返回的重叠/近重复切片做二次去重，避免同一句话因不同切分窗口被标成多个来源。
    const deduplicatedChunks = deduplicateChunksByContent(normalizedChunks, {
      similarityThreshold: 0.85
    })

    deduplicatedChunks.sort((a, b) => {
      const scoreA = typeof a.score === 'number' ? a.score : Number.NEGATIVE_INFINITY
      const scoreB = typeof b.score === 'number' ? b.score : Number.NEGATIVE_INFINITY
      return scoreB - scoreA
    })

    return deduplicatedChunks
  }

  /**
   * 提取一轮对话中的网络搜索来源
   * @param {Object} conv - 单轮对话
   * @returns {Array} 归一化后的网络来源
   */
  static extractWebSourcesFromConversation(conv) {
    if (!conv || !Array.isArray(conv.messages) || conv.messages.length === 0) return []

    const webSources = []
    const dedupSet = new Set()

    const parseToolResultContent = (content) => {
      if (Array.isArray(content)) return content
      if (content && typeof content === 'object') return content
      if (typeof content === 'string') {
        try {
          return JSON.parse(content)
        } catch {
          return null
        }
      }
      return null
    }

    for (const msg of conv.messages) {
      if (!msg || msg.type !== 'ai' || !Array.isArray(msg.tool_calls)) continue

      for (const toolCall of msg.tool_calls) {
        const toolName = (toolCall?.name || toolCall?.function?.name || '').toLowerCase()
        if (!toolName.includes('tavily_search')) continue

        const content = toolCall?.tool_call_result?.content
        const parsed = parseToolResultContent(content)
        const results = Array.isArray(parsed?.results) ? parsed.results : []
        if (results.length === 0) continue

        for (const item of results) {
          const title = typeof item?.title === 'string' ? item.title.trim() : ''
          const url = typeof item?.url === 'string' ? item.url.trim() : ''
          if (!title || !url) continue
          if (dedupSet.has(url)) continue
          dedupSet.add(url)

          webSources.push({
            tool_name: toolCall?.name || toolCall?.function?.name || '网络搜索',
            title,
            url,
            score: typeof item?.score === 'number' ? item.score : null,
            content: typeof item?.content === 'string' ? item.content : '',
            published_date: typeof item?.published_date === 'string' ? item.published_date : ''
          })
        }
      }
    }

    webSources.sort((a, b) => {
      const scoreA = typeof a.score === 'number' ? a.score : Number.NEGATIVE_INFINITY
      const scoreB = typeof b.score === 'number' ? b.score : Number.NEGATIVE_INFINITY
      return scoreB - scoreA
    })

    return webSources
  }

  /**
   * 提取单个消息中的来源
   * @param {Object} message - 消息对象
   * @param {Array} databases - 知识库列表
   * @returns {{knowledgeChunks: Array, webSources: Array}}
   */
  static extractSourcesFromMessage(message, databases = []) {
    if (!message || message.type !== 'ai') return { knowledgeChunks: [], webSources: [] }

    // 复用提取逻辑，通过构建临时对话对象
    const mockConv = { messages: [message] }
    return {
      knowledgeChunks: MessageProcessor.extractKnowledgeChunksFromConversation(mockConv, databases),
      webSources: MessageProcessor.extractWebSourcesFromConversation(mockConv)
    }
  }

  /**
   * 提取一轮对话中的全部来源（知识库+网络搜索）
   * @param {Object} conv - 单轮对话
   * @param {Array} databases - 知识库列表
   * @returns {{knowledgeChunks: Array, webSources: Array}}
   */
  static extractSourcesFromConversation(conv, databases = []) {
    return {
      knowledgeChunks: MessageProcessor.extractKnowledgeChunksFromConversation(conv, databases),
      webSources: MessageProcessor.extractWebSourcesFromConversation(conv)
    }
  }

  /**
   * 支持的引用 token 格式（原始输出 / 已渲染 HTML）：
   * - 模型原始输出：`[ref:CHUNK_ID]`（半角）或 `【ref:CHUNK_ID】`（全角）
   * - 渲染后：`<cite data-chunk-id="CHUNK_ID">`
   */
  static get CITATION_TOKEN_PATTERNS() {
    return [
      /<cite[^>]+data-chunk-id=["']([^"']+)["'][^>]*>/g,
      /\[ref:\s*([^\]\s]+)\s*\]/g,
      /【ref:\s*([^】\s]+)\s*】/g
    ]
  }

  /**
   * 从正文内容中提取实际被引用的 chunk_id，按出现顺序去重。
   * @param {string} content - 助手消息正文（原始输出或已渲染 HTML）
   * @returns {Array<string>} 按引用顺序去重后的 chunk_id 列表
   */
  static extractCitedChunkIds(content) {
    if (typeof content !== 'string' || !content) return []
    const ids = []
    const seen = new Set()
    for (const regex of MessageProcessor.CITATION_TOKEN_PATTERNS) {
      let match
      while ((match = regex.exec(content)) !== null) {
        const id = match[1].trim()
        if (id && !seen.has(id)) {
          seen.add(id)
          ids.push(id)
        }
      }
    }
    return ids
  }

  /**
   * 解析助手消息正文与推理内容，保持渲染和列表拆分使用同一套规则。
   * @param {Object} message - AI 消息对象
   * @returns {{content: string, reasoningContent: string}}
   */
  static parseAssistantMessageBody(message) {
    let content = typeof message?.content === 'string' ? message.content.trim() : ''
    let reasoningContent = message?.additional_kwargs?.reasoning_content || ''

    if (!reasoningContent && content) {
      const thinkRegex = /<think>(.*?)<\/think>|<think>(.*?)$/s
      const thinkMatch = content.match(thinkRegex)

      if (thinkMatch) {
        reasoningContent = (thinkMatch[1] || thinkMatch[2] || '').trim()
        content = content.replace(thinkMatch[0], '').trim()
      }
    }

    return { content, reasoningContent }
  }

  /**
   * 合并消息块
   * @param {Array} chunks - 消息块数组
   * @returns {Object|null} 合并后的消息
   */
  static mergeMessageChunk(chunks) {
    if (chunks.length === 0) return null

    // 深拷贝第一个chunk作为结果
    const result = JSON.parse(JSON.stringify(chunks[0]))

    // 处理用户消息的内容格式 - 确保显示纯文本
    if (result.type === 'human' || result.role === 'user') {
      // 如果content是数组格式（LangChain多模态消息），提取文本部分
      if (Array.isArray(result.content)) {
        const textPart = result.content.find((item) => item.type === 'text')
        result.content = textPart ? textPart.text : ''
      } else {
        result.content = result.content || ''
      }
    } else {
      result.content = result.content || ''
    }

    // 合并后续chunks
    for (let i = 1; i < chunks.length; i++) {
      const chunk = chunks[i]

      // 合并内容
      if (chunk.content) {
        result.content += chunk.content
      }

      // 合并reasoning_content
      if (chunk.reasoning_content) {
        if (!result.reasoning_content) {
          result.reasoning_content = ''
        }
        result.reasoning_content += chunk.reasoning_content
      }

      // 合并additional_kwargs中的reasoning_content
      if (chunk.additional_kwargs?.reasoning_content) {
        if (!result.additional_kwargs) result.additional_kwargs = {}
        if (!result.additional_kwargs.reasoning_content) {
          result.additional_kwargs.reasoning_content = ''
        }
        result.additional_kwargs.reasoning_content += chunk.additional_kwargs.reasoning_content
      }

      // 合并tool_calls (处理新的数据结构)
      MessageProcessor._mergeToolCalls(result, chunk)
    }

    // 处理AIMessageChunk类型
    if (result.type === 'AIMessageChunk') {
      result.type = 'ai'
    }

    return result
  }

  /**
   * 合并工具调用
   * @private
   * @param {Object} result - 结果对象
   * @param {Object} chunk - 当前块
   */
  static _mergeToolCalls(result, chunk) {
    if (chunk.tool_call_chunks && chunk.tool_call_chunks.length > 0) {
      // 确保 result 有 tool_calls 数组
      if (!result.tool_calls) result.tool_calls = []

      for (const toolCallChunk of chunk.tool_call_chunks) {
        // 使用 index 来标识工具调用（因为可能有多个工具调用）
        const existingToolCallIndex = result.tool_calls.findIndex(
          (t) => t.index === toolCallChunk.index
        )

        if (existingToolCallIndex !== -1) {
          // 合并相同index的tool call
          const existingToolCall = result.tool_calls[existingToolCallIndex]

          // 更新名称和ID（如果存在）
          if (toolCallChunk.name && !existingToolCall.function?.name) {
            if (!existingToolCall.function) existingToolCall.function = {}
            existingToolCall.function.name = toolCallChunk.name
          }

          if (toolCallChunk.id && !existingToolCall.id) {
            existingToolCall.id = toolCallChunk.id
          }

          // 合并参数
          if (toolCallChunk.args) {
            if (!existingToolCall.function) existingToolCall.function = {}
            if (!existingToolCall.function.arguments) existingToolCall.function.arguments = ''
            existingToolCall.function.arguments += toolCallChunk.args
          }
        } else {
          // 添加新的tool call
          const newToolCall = {
            index: toolCallChunk.index,
            id: toolCallChunk.id,
            function: {
              name: toolCallChunk.name || null,
              arguments: toolCallChunk.args || ''
            }
          }
          result.tool_calls.push(newToolCall)
        }
      }
    }
  }
}

export default MessageProcessor
