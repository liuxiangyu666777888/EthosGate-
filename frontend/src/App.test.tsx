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
  expect(screen.getByRole('heading', { name: 'EthosGate · 善治' })).toBeInTheDocument()
})
