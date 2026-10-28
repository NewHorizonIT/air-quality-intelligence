import { Route, BrowserRouter as Router, Routes } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import Prediction from './pages/Prediction'

export default function App() {
  return (
    <Router>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="ml-52 flex-1 px-8 py-7 min-w-0">
          <Routes>
            <Route path="/"           element={<Dashboard />} />
            <Route path="/prediction" element={<Prediction />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}
