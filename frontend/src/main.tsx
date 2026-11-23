import { StrictMode } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import App from './App.tsx'
import AuthGate from './components/AuthGate'
import { CustomerOrderPage, OrderTrackingPage, OrderCheckoutPage, OrderThankYouPage } from './components/OrderingPages'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10_000,
      refetchInterval: 15_000,
      retry: 1,
      refetchOnWindowFocus: true,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/order/:tableId" element={<CustomerOrderPage />} />
          <Route path="/track/:token" element={<OrderTrackingPage />} />
          <Route path="/checkout/:token" element={<OrderCheckoutPage />} />
          <Route path="/thank-you/:token" element={<OrderThankYouPage />} />
          <Route path="/*" element={<AuthGate><App /></AuthGate>} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
