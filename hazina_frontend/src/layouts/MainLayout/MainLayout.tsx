import { useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'
import './MainLayout.css'

const pageTitles: Record<string, string> = {
  '/': 'Dashboard',
  '/ingestion': 'Data ingestion',
  '/pipeline-runs': 'Pipeline runs',
  '/mappings': 'Mappings',
  '/users': 'User management',
  '/settings': 'Settings',
}

function MainLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()

  const pageTitle = pageTitles[location.pathname] ?? 'Hazina'

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <div className="min-h-screen lg:pl-64">
        <Header
          pageTitle={pageTitle}
          onMenuClick={() => setSidebarOpen(true)}
        />

        <main className="main-layout-content mx-auto max-w-[1500px] p-5 sm:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default MainLayout