export type ConfigValueType = 'string' | 'number' | 'boolean' | 'json'

export interface ValidationOptions {
  allowEmptyString?: boolean
  trimString?: boolean
  numberMin?: number
  numberMax?: number
  numberAllowFloat?: boolean
  jsonSchemaValidator?: (value: unknown) => true | string
}

export interface ValidationResult<T = unknown> {
  valid: boolean
  normalized?: T
  error?: string
}

export type ValidationErrorMessages = {
  string: { required: string; type: string }
  number: { required: string; type: string; range: (min?: number, max?: number) => string }
  boolean: { required: string; type: string }
  json: { required: string; type: string; parse: (reason: string) => string }
}

const defaultMessages: ValidationErrorMessages = {
  string: {
    required: '不能为空',
    type: '必须为字符串'
  },
  number: {
    required: '不能为空',
    type: '必须为数字',
    range: (min?: number, max?: number) => {
      if (min !== undefined && max !== undefined) return `必须在 ${min}-${max} 范围内`
      if (min !== undefined) return `必须大于等于 ${min}`
      if (max !== undefined) return `必须小于等于 ${max}`
      return '超出允许范围'
    }
  },
  boolean: {
    required: '不能为空',
    type: '必须为布尔值'
  },
  json: {
    required: '不能为空',
    type: '必须为对象或数组',
    parse: (reason: string) => `JSON 解析失败：${reason}`
  }
}

export const validateString = (
  value: unknown,
  options: ValidationOptions = {},
  messages: ValidationErrorMessages['string'] = defaultMessages.string
): ValidationResult<string> => {
  if (value === undefined || value === null || value === '') {
    if (options.allowEmptyString) return { valid: true, normalized: '' }
    return { valid: false, error: messages.required }
  }
  if (typeof value !== 'string') return { valid: false, error: messages.type }
  const normalized = options.trimString === false ? value : value.trim()
  if (!options.allowEmptyString && normalized === '') return { valid: false, error: messages.required }
  return { valid: true, normalized }
}

export const validateNumber = (
  value: unknown,
  options: ValidationOptions = {},
  messages: ValidationErrorMessages['number'] = defaultMessages.number
): ValidationResult<number> => {
  if (value === undefined || value === null || value === '') {
    return { valid: false, error: messages.required }
  }
  const parsed =
    typeof value === 'number'
      ? value
      : typeof value === 'string'
      ? Number(value.trim())
      : NaN
  if (Number.isNaN(parsed) || typeof parsed !== 'number') {
    return { valid: false, error: messages.type }
  }
  if (!options.numberAllowFloat && !Number.isInteger(parsed)) {
    return { valid: false, error: messages.type }
  }
  if (options.numberMin !== undefined && parsed < options.numberMin) {
    return { valid: false, error: messages.range(options.numberMin, options.numberMax) }
  }
  if (options.numberMax !== undefined && parsed > options.numberMax) {
    return { valid: false, error: messages.range(options.numberMin, options.numberMax) }
  }
  return { valid: true, normalized: parsed }
}

export const validateBoolean = (
  value: unknown,
  _options: ValidationOptions = {},
  messages: ValidationErrorMessages['boolean'] = defaultMessages.boolean
): ValidationResult<boolean> => {
  if (value === undefined || value === null || value === '') {
    return { valid: false, error: messages.required }
  }
  if (typeof value === 'boolean') return { valid: true, normalized: value }
  if (typeof value === 'string') {
    if (value.toLowerCase() === 'true') return { valid: true, normalized: true }
    if (value.toLowerCase() === 'false') return { valid: true, normalized: false }
  }
  return { valid: false, error: messages.type }
}

export const validateJson = (
  value: unknown,
  options: ValidationOptions = {},
  messages: ValidationErrorMessages['json'] = defaultMessages.json
): ValidationResult<Record<string, unknown> | unknown[]> => {
  if (value === undefined || value === null || value === '') {
    return { valid: false, error: messages.required }
  }

  let parsed: unknown = value
  if (typeof value === 'string') {
    try {
      parsed = JSON.parse(value)
    } catch (err) {
      return { valid: false, error: messages.parse((err as Error).message) }
    }
  }

  const isObject = parsed !== null && typeof parsed === 'object'
  if (!isObject) return { valid: false, error: messages.type }

  if (options.jsonSchemaValidator) {
    const result = options.jsonSchemaValidator(parsed)
    if (result !== true) return { valid: false, error: typeof result === 'string' ? result : messages.type }
  }

  return { valid: true, normalized: parsed as Record<string, unknown> | unknown[] }
}

export const validateByType = (
  valueType: ConfigValueType,
  value: unknown,
  options: ValidationOptions = {},
  messages: ValidationErrorMessages = defaultMessages
): ValidationResult => {
  switch (valueType) {
    case 'string':
      return validateString(value, options, messages.string)
    case 'number':
      return validateNumber(value, options, messages.number)
    case 'boolean':
      return validateBoolean(value, options, messages.boolean)
    case 'json':
      return validateJson(value, options, messages.json)
    default:
      return { valid: false, error: '未知类型' }
  }
}
