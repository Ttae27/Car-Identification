import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import CarList from './carList.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <CarList />
  </StrictMode>,
)
