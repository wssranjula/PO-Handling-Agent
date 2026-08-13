import { ClipboardCheck, FileSearch, Inbox, ShieldCheck } from 'lucide-react'
import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { OrderDetailPage } from './pages/OrderDetailPage'
import { OrdersPage } from './pages/OrdersPage'
import { ReviewDetailPage } from './pages/ReviewDetailPage'
import { ReviewsPage } from './pages/ReviewsPage'

function Shell() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark"><ClipboardCheck size={22} /></span>
          <span><strong>PO Operations</strong><small>Intake control room</small></span>
        </div>
        <nav>
          <NavLink to="/orders"><ShieldCheck size={18} /> Processed POs</NavLink>
          <NavLink to="/reviews"><FileSearch size={18} /> Human review</NavLink>
        </nav>
        <div className="agent-status">
          <span className="status-dot" />
          <div><strong>Agent online</strong><small>Watching email intake</small></div>
        </div>
      </aside>
      <main className="main-content">
        <header className="topbar">
          <div className="workspace-pill"><Inbox size={15} /> Purchase order intake</div>
          <div className="avatar" title="Operations reviewer">OP</div>
        </header>
        <Routes>
          <Route path="/orders" element={<OrdersPage />} />
          <Route path="/orders/:orderId" element={<OrderDetailPage />} />
          <Route path="/reviews" element={<ReviewsPage />} />
          <Route path="/reviews/:reviewId" element={<ReviewDetailPage />} />
          <Route path="*" element={<Navigate to="/orders" replace />} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return <Shell />
}
