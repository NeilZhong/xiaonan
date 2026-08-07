import MessageProcessor from '@/utils/messageProcessor'
import { enrichTaskToolCalls } from '@/components/ToolCallingResult/toolRegistry'

const hasVisibleAssistantBody = (message) => {
  if (!message || message.type !== 'ai') return true

  const { content, reasoningContent } = MessageProcessor.parseAssistantMessageBody(message)
  return Boolean(
    content ||
    reasoningContent ||
    message.error_type ||
    message.extra_metadata?.error_type ||
    message.isStoppedByUser
  )
}

const defaultEnrichToolCalls = (message) => enrichTaskToolCalls(message?.tool_calls)

// 将 AI 消息拆成“正文块”和“工具块”，再跨消息合并相邻工具块。
export const getConversationDisplayItems = (
  conv,
  { enrichToolCalls = defaultEnrichToolCalls } = {}
) => {
  if (!Array.isArray(conv?.messages) || conv.messages.length === 0) return []

  const items = []
  let pendingToolGroup = null

  const flushToolGroup = () => {
    if (pendingToolGroup && pendingToolGroup.toolCalls.length > 0) {
      items.push(pendingToolGroup)
    }
    pendingToolGroup = null
  }

  conv.messages.forEach((message, index) => {
    if (message.type !== 'ai') {
      flushToolGroup()
      items.push({
        type: 'message',
        key: message.id || `message-${index}`,
        message,
        sourceIndex: index
      })
      return
    }

    if (hasVisibleAssistantBody(message)) {
      flushToolGroup()
      items.push({
        type: 'message',
        key: message.id || `message-${index}`,
        message,
        sourceIndex: index
      })
    }

    const toolCalls = enrichToolCalls(message)
    if (toolCalls.length === 0) return

    if (!pendingToolGroup) {
      pendingToolGroup = {
        type: 'tool-group',
        key: `tool-group-${message.id || index}`,
        toolCalls: []
      }
    }
    pendingToolGroup.toolCalls.push(...toolCalls)
  })

  flushToolGroup()

  // 标记同一轮对话中连续 AI 消息组的起始位置：
  // 同一次用户提问可能触发智能体多轮思考/工具调用/续写，产生多条 AI 消息，
  // 视觉上应归为同一“助手回复块”，仅首条显示头像、名称与时间。
  let lastMessageType = null
  items.forEach((item) => {
    if (item.type !== 'message') return
    if (item.message.type === 'ai') {
      item.isAssistantGroupStart = lastMessageType !== 'ai'
      lastMessageType = 'ai'
    } else {
      lastMessageType = item.message.type
    }
  })

  return items
}
