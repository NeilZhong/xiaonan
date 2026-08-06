/**
 * 数字警员漫画 Avatar 资产库与随机生成器
 *
 * 视觉风格：2D 手绘/线条漫画风，头肩部半身像，浅灰背景，局部警务蓝点缀。
 * 输出格式为 data:image/svg+xml 字符串，可直接作为 <img src> 使用。
 */

const AVATAR_VIEWBOX = '0 0 200 200'

const AVATAR_BACKGROUND = '#F4F5F7'
const STROKE_COLOR = '#1A202C'
const STROKE_WIDTH = 2.8
const POLICE_BLUE = '#2B6CB0'
const SKIN_LIGHT = '#F6E2D3'
const SKIN_MEDIUM = '#EBC8B2'
const ACCENT_RED = '#E53E3E'

const encodeSvg = (svg) =>
  `data:image/svg+xml;utf8,${encodeURIComponent(svg.replace(/\n\s*/g, ''))}`

const makeSvg = (content, { extraDefs = '' } = {}) => `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="${AVATAR_VIEWBOX}" width="200" height="200">
  <defs>${extraDefs}</defs>
  <rect width="200" height="200" rx="40" fill="${AVATAR_BACKGROUND}"/>
  ${content}
</svg>`

const AVATAR_LIBRARY = [
  {
    id: 'officer-male-tablet',
    name: '男警·平板办案',
    tags: ['男警', '平板', '技术研判'],
    svg: makeSvg(`
      <g transform="translate(0,10)">
        <ellipse cx="100" cy="170" rx="70" ry="22" fill="#E2E8F0" opacity="0.6"/>
        <path d="M55 170 Q55 115 100 115 Q145 115 145 170" fill="#2B6CB0" stroke="${STROKE_COLOR}" stroke-width="${STROKE_WIDTH}" stroke-linejoin="round"/>
        <path d="M75 170 L75 138 L125 138 L125 170" fill="#CBD5E0" stroke="${STROKE_COLOR}" stroke-width="${STROKE_WIDTH}" stroke-linejoin="round"/>
        <circle cx="100" cy="82" r="34" fill="${SKIN_LIGHT}" stroke="${STROKE_COLOR}" stroke-width="${STROKE_WIDTH}"/>
        <path d="M68 72 Q100 58 132 72 L132 82 Q100 68 68 82 Z" fill="#1A365D" stroke="${STROKE_COLOR}" stroke-width="${STROKE_WIDTH}" stroke-linejoin="round"/>
        <rect x="64" y="68" width="72" height="14" rx="4" fill="#2B6CB0" stroke="${STROKE_COLOR}" stroke-width="${STROKE_WIDTH}"/>
        <path d="M70 66 L72 56 L128 56 L130 66" fill="none" stroke="${STROKE_COLOR}" stroke-width="${STROKE_WIDTH}" stroke-linecap="round"/>
        <circle cx="88" cy="86" r="3.5" fill="#1A202C"/>
        <circle cx="112" cy="86" r="3.5" fill="#1A202C"/>
        <path d="M92 100 Q100 106 108 100" fill="none" stroke="${STROKE_COLOR}" stroke-width="2.2" stroke-linecap="round"/>
        <rect x="84" y="130" width="44" height="32" rx="4" fill="#FFFFFF" stroke="${STROKE_COLOR}" stroke-width="2.2" stroke-linejoin="round"/>
        <rect x="88" y="134" width="36" height="20" rx="2" fill="#EBF2FA" stroke="none"/>
        <circle cx="132" cy="148" r="6" fill="${POLICE_BLUE}"/>
      </g>
    `)
  },
  {
    id: 'officer-female-files',
    name: '女警·案卷管理',
    tags: ['女警', '案卷', '资料整理'],
    svg: makeSvg(`
      <g transform="translate(0,10)">
        <ellipse cx="100" cy="172" rx="72" ry="22" fill="#E2E8F0" opacity="0.6"/>
        <path d="M50 170 Q50 120 100 120 Q150 120 150 170" fill="#2B6CB0" stroke="${STROKE_COLOR}" stroke-width="${STROKE_WIDTH}" stroke-linejoin="round"/>
        <circle cx="100" cy="80" r="34" fill="${SKIN_MEDIUM}" stroke="${STROKE_COLOR}" stroke-width="${STROKE_WIDTH}"/>
        <path d="M66 68 Q100 48 134 68 L140 110 Q110 100 60 110 Z" fill="#1A365D" stroke="${STROKE_COLOR}" stroke-width="${STROKE_WIDTH}" stroke-linejoin="round"/>
        <path d="M68 70 Q100 55 132 70" fill="none" stroke="${STROKE_COLOR}" stroke-width="2.2" stroke-linecap="round"/>
        <ellipse cx="84" cy="84" rx="4" ry="5" fill="#1A202C"/>
        <ellipse cx="116" cy="84" rx="4" ry="5" fill="#1A202C"/>
        <path d="M93 98 Q100 104 107 98" fill="none" stroke="${STROKE_COLOR}" stroke-width="2.2" stroke-linecap="round"/>
        <path d="M70 140 L70 112 L110 112 L110 140" fill="#FFFFFF" stroke="${STROKE_COLOR}" stroke-width="2.2" stroke-linejoin="round"/>
        <path d="M72 118 L108 118 M72 126 L108 126 M72 134 L100 134" stroke="#CBD5E0" stroke-width="2"/>
        <rect x="85" y="108" width="18" height="8" rx="2" fill="${ACCENT_RED}"/>
      </g>
    `)
  },
  {
    id: 'officer-male-headset',
    name: '男警·通信指挥',
    tags: ['男警', '耳机', '指挥调度'],
    svg: makeSvg(`
      <g transform="translate(0,10)">
        <ellipse cx="100" cy="170" rx="70" ry="22" fill="#E2E8F0" opacity="0.6"/>
        <path d="M55 170 Q55 118 100 118 Q145 118 145 170" fill="#2B6CB0" stroke="${STROKE_COLOR}" stroke-width="${STROKE_WIDTH}" stroke-linejoin="round"/>
        <circle cx="100" cy="82" r="34" fill="${SKIN_LIGHT}" stroke="${STROKE_COLOR}" stroke-width="${STROKE_WIDTH}"/>
        <path d="M64 70 Q100 52 136 70 L132 90 Q100 78 68 90 Z" fill="#1A365D" stroke="${STROKE_COLOR}" stroke-width="${STROKE_WIDTH}" stroke-linejoin="round"/>
        <rect x="62" y="74" width="12" height="28" rx="5" fill="#4A5568" stroke="${STROKE_COLOR}" stroke-width="2.2"/>
        <path d="M74 82 L136 82" fill="none" stroke="#4A5568" stroke-width="2.2" stroke-linecap="round"/>
        <circle cx="88" cy="86" r="3.5" fill="#1A202C"/>
        <circle cx="112" cy="86" r="3.5" fill="#1A202C"/>
        <path d="M93 100 Q100 106 107 100" fill="none" stroke="${STROKE_COLOR}" stroke-width="2.2" stroke-linecap="round"/>
        <rect x="90" y="140" width="24" height="28" rx="4" fill="#FFFFFF" stroke="${STROKE_COLOR}" stroke-width="2.2"/>
        <rect x="94" y="146" width="16" height="14" rx="2" fill="#EBF2FA"/>
        <line x1="100" y1="144" x2="100" y2="164" stroke="${POLICE_BLUE}" stroke-width="2"/>
      </g>
    `)
  },
  {
    id: 'officer-female-magnifier',
    name: '女警·证据核查',
    tags: ['女警', '放大镜', '证据分析'],
    svg: makeSvg(`
      <g transform="translate(0,10)">
        <ellipse cx="100" cy="172" rx="72" ry="22" fill="#E2E8F0" opacity="0.6"/>
        <path d="M52 170 Q52 122 100 122 Q148 122 148 170" fill="#2B6CB0" stroke="${STROKE_COLOR}" stroke-width="${STROKE_WIDTH}" stroke-linejoin="round"/>
        <circle cx="100" cy="80" r="34" fill="${SKIN_MEDIUM}" stroke="${STROKE_COLOR}" stroke-width="${STROKE_WIDTH}"/>
        <path d="M66 62 Q100 48 134 62 L138 78 Q100 66 62 78 Z" fill="#1A365D" stroke="${STROKE_COLOR}" stroke-width="${STROKE_WIDTH}" stroke-linejoin="round"/>
        <path d="M72 64 L76 58 L124 58 L128 64" fill="none" stroke="${STROKE_COLOR}" stroke-width="2.2" stroke-linecap="round"/>
        <rect x="92" y="72" width="16" height="4" rx="1" fill="#4A5568"/>
        <ellipse cx="86" cy="84" rx="4" ry="5" fill="#1A202C"/>
        <ellipse cx="114" cy="84" rx="4" ry="5" fill="#1A202C"/>
        <path d="M93 98 Q100 104 107 98" fill="none" stroke="${STROKE_COLOR}" stroke-width="2.2" stroke-linecap="round"/>
        <circle cx="130" cy="148" r="16" fill="none" stroke="${STROKE_COLOR}" stroke-width="2.8"/>
        <line x1="142" y1="160" x2="152" y2="172" stroke="#4A5568" stroke-width="4" stroke-linecap="round"/>
        <circle cx="130" cy="148" r="12" fill="#EBF2FA" opacity="0.5"/>
      </g>
    `)
  },
  {
    id: 'officer-male-k9',
    name: '男警·警犬协作',
    tags: ['男警', '警犬', '现场勘查'],
    svg: makeSvg(`
      <g transform="translate(0,10)">
        <ellipse cx="100" cy="170" rx="70" ry="22" fill="#E2E8F0" opacity="0.6"/>
        <path d="M55 170 Q55 118 100 118 Q145 118 145 170" fill="#2B6CB0" stroke="${STROKE_COLOR}" stroke-width="${STROKE_WIDTH}" stroke-linejoin="round"/>
        <circle cx="92" cy="80" r="32" fill="${SKIN_LIGHT}" stroke="${STROKE_COLOR}" stroke-width="${STROKE_WIDTH}"/>
        <path d="M60 68 Q92 54 124 68 L124 80 Q92 66 60 80 Z" fill="#1A365D" stroke="${STROKE_COLOR}" stroke-width="${STROKE_WIDTH}" stroke-linejoin="round"/>
        <path d="M66 66 L68 56 L116 56 L118 66" fill="none" stroke="${STROKE_COLOR}" stroke-width="2.2" stroke-linecap="round"/>
        <circle cx="82" cy="84" r="3.5" fill="#1A202C"/>
        <circle cx="102" cy="84" r="3.5" fill="#1A202C"/>
        <path d="M86 98 Q92 103 98 98" fill="none" stroke="${STROKE_COLOR}" stroke-width="2.2" stroke-linecap="round"/>
        <ellipse cx="128" cy="152" rx="20" ry="14" fill="#A0AEC0" stroke="${STROKE_COLOR}" stroke-width="2.2"/>
        <circle cx="120" cy="148" r="4" fill="#1A202C"/>
        <path d="M110 156 Q120 164 130 156" fill="none" stroke="${STROKE_COLOR}" stroke-width="2.2" stroke-linecap="round"/>
        <path d="M138 148 Q146 144 148 154" fill="none" stroke="${STROKE_COLOR}" stroke-width="2.2" stroke-linecap="round"/>
      </g>
    `)
  },
  {
    id: 'officer-female-radio',
    name: '女警·无线调度',
    tags: ['女警', '对讲机', '巡逻执勤'],
    svg: makeSvg(`
      <g transform="translate(0,10)">
        <ellipse cx="100" cy="172" rx="72" ry="22" fill="#E2E8F0" opacity="0.6"/>
        <path d="M50 170 Q50 120 100 120 Q150 120 150 170" fill="#2B6CB0" stroke="${STROKE_COLOR}" stroke-width="${STROKE_WIDTH}" stroke-linejoin="round"/>
        <circle cx="100" cy="80" r="34" fill="${SKIN_MEDIUM}" stroke="${STROKE_COLOR}" stroke-width="${STROKE_WIDTH}"/>
        <path d="M66 60 Q100 44 134 60 L140 82 Q100 68 60 82 Z" fill="#1A365D" stroke="${STROKE_COLOR}" stroke-width="${STROKE_WIDTH}" stroke-linejoin="round"/>
        <path d="M72 58 L76 50 L124 50 L128 58" fill="none" stroke="${STROKE_COLOR}" stroke-width="2.2" stroke-linecap="round"/>
        <ellipse cx="84" cy="84" rx="4" ry="5" fill="#1A202C"/>
        <ellipse cx="116" cy="84" rx="4" ry="5" fill="#1A202C"/>
        <path d="M93 98 Q100 104 107 98" fill="none" stroke="${STROKE_COLOR}" stroke-width="2.2" stroke-linecap="round"/>
        <path d="M122 120 Q132 118 136 126 Q140 138 134 152 Q128 160 120 158 Q112 152 118 138 L116 128 Z" fill="#4A5568" stroke="${STROKE_COLOR}" stroke-width="2.2" stroke-linejoin="round"/>
        <line x1="126" y1="128" x2="138" y2="120" stroke="#4A5568" stroke-width="2.2" stroke-linecap="round"/>
        <circle cx="128" cy="142" r="3" fill="#81E6D9"/>
      </g>
    `)
  }
]

export const POLICE_AVATAR_IDS = AVATAR_LIBRARY.map((item) => item.id)

/**
 * 随机生成一个数字警员漫画 Avatar。
 * @param {string|number} [seed] 可选种子。传入后按种子确定性返回同一 Avatar；不传则真随机。
 * @returns {{ id: string, name: string, tags: string[], url: string }}
 */
export const generateRandomPoliceAvatar = (seed) => {
  let index
  if (seed != null && String(seed).trim() !== '') {
    const normalized = String(seed).trim()
    let hash = 0
    for (const char of normalized) {
      hash = (hash * 31 + char.codePointAt(0)) >>> 0
    }
    index = hash % AVATAR_LIBRARY.length
  } else {
    index = Math.floor(Math.random() * AVATAR_LIBRARY.length)
  }
  const item = AVATAR_LIBRARY[index]
  return {
    id: item.id,
    name: item.name,
    tags: [...item.tags],
    url: item.svg
  }
}

/**
 * 按 ID 查找 Avatar 定义。
 * @param {string} id
 * @returns {{ id: string, name: string, tags: string[], url: string } | null}
 */
export const getPoliceAvatarById = (id) => {
  const item = AVATAR_LIBRARY.find((a) => a.id === id)
  return item ? { id: item.id, name: item.name, tags: [...item.tags], url: item.svg } : null
}

/**
 * 判断一个 URL/字符串是否为数字警员 Avatar ID 标记。
 * 由于本库直接输出 data URL，该方法用于兼容未来可能的 `police-avatar:<id>` 标记。
 */
export const isPoliceAvatarUrl = (url) =>
  typeof url === 'string' && url.startsWith('data:image/svg+xml')

export default {
  POLICE_AVATAR_IDS,
  generateRandomPoliceAvatar,
  getPoliceAvatarById,
  isPoliceAvatarUrl
}
