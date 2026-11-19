
import { createBrowserRouter, RouterProvider } from 'react-router-dom'

import MainLayout from '../layouts/MainLayout/MainLayout'
import AuthLayout from '../layouts/AuthLayout/AuthLayout'

import DashboardPage from '../pages/Dashboard/DashboardPage'
import LoginPage from '../pages/Login/LoginPage'
import NotFoundPage from '../pages/NotFound/NotFoundPage'
import PipelineRunsPage from '../pages/PipelineRuns/PipelineRunsPage'
import PipelineRunDetailsPage from '../pages/PipelineRuns/PipelineRunDetailsPage'
import IngestionPage from '../pages/Ingestion/IngestionPage'
import MappingsPage from '../pages/Mappings/MappingsPage'
import UserManagementPage from '../pages/UserManagement/UserManagementPage'
import SettingsPage from '../pages/Settings/SettingsPage'

import ProtectedRoute from '../components/auth/ProtectedRoute'
import PublicRoute from '../components/auth/PublicRoute'

const router = createBrowserRouter([
  {
    element: <PublicRoute />,
    children: [
      {
        element: <AuthLayout />,
        children: [
          {
            path: '/login',
            element: <LoginPage />,
          },
        ],
      },
    ],
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        path: '/',
        element: <MainLayout />,
        children: [
          {
            index: true,
            element: <DashboardPage />,
          },
          {
            path: 'ingestion',
            element: <IngestionPage />,
          },
          {
            path: 'pipeline-runs',
            element: <PipelineRunsPage />,
          },
          {
            path: 'pipeline-runs/:runId',
            element: <PipelineRunDetailsPage />,
          },
          {
            path: 'mappings',
            element: <MappingsPage />,
          },
          {
            path: 'users',
            element: <UserManagementPage />,
          },
          {
            path: 'settings',
            element: <SettingsPage />,
          },
        ],
      },
    ],
  },
  {
    path: '*',
    element: <NotFoundPage />,
  },
])

function AppRouter() {
  return <RouterProvider router={router} />
}

export default AppRouter
