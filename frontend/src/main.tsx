import React from 'react'
import { createRoot } from 'react-dom/client'
import { RootApp } from './App'
import './styles.css'

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <RootApp />
  </React.StrictMode>,
)
