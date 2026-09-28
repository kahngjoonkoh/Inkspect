import { Link, Route, Routes } from 'react-router-dom'
import Landing from './pages/Landing'
import TestRunner from './pages/TestRunner'
import ResultsPage from './pages/ResultsPage'
import AdminHome from './pages/AdminHome'
import AdminReview from './pages/AdminReview'
import RegionEditor from './pages/RegionEditor'

export default function App() {
  return (
    <div className="app">
      <header className="topbar">
        <Link to="/" className="brand">
          Inkspect
        </Link>
      </header>
      <main className="content">
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/test/:id" element={<TestRunner />} />
          <Route path="/results/:id" element={<ResultsPage />} />
          <Route path="/admin" element={<AdminHome />} />
          <Route path="/admin/review/:id" element={<AdminReview />} />
          <Route path="/admin/regions/:card" element={<RegionEditor />} />
          <Route
            path="*"
            element={
              <section className="panel">
                <h1>Not found</h1>
                <p>
                  <Link to="/">Back to the start</Link>
                </p>
              </section>
            }
          />
        </Routes>
      </main>
    </div>
  )
}
