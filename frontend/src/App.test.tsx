import { render, screen } from '@testing-library/react'
import { App } from './App'

Object.defineProperty(window, 'localStorage', {
  value: {
    getItem: () => null,
    setItem: () => undefined,
    removeItem: () => undefined,
  },
  writable: true,
})

test('renders login entry', () => {
  render(<App />)
  expect(screen.getByText('LLM部署伦理评估仪表盘')).toBeInTheDocument()
})
