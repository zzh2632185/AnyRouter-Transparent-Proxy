import '@testing-library/jest-dom'
import { config } from '@vue/test-utils'

config.global.stubs = {
  Teleport: true
}
