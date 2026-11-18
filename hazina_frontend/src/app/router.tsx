
import { createBrowserRouter, RouterProvider } from 'react-router-dom'

import MainLayout from '../layouts/MainLayout/MainLayout'
import AuthLayout from '../layouts/AuthLayout/AuthLayout'

import DashboardPage from '../pages/Dashboard/DashboardPage'
import LoginPage from '../pages/Login/LoginPage'
import FeaturePlaceholderPage from '../pages/FeaturePlaceholderPage'
import NotFoundPage from '../pages/NotFound/NotFoundPage'
import PipelineRunsPage from '../pages/PipelineRuns/PipelineRunsPage'

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
            element: <FeaturePlaceholderPage title="Data ingestion" />,
          },
          {
            path: 'pipeline-runs',
            element: <PipelineRunsPage />,
          },
          {
            path: 'mappings',
            element: <FeaturePlaceholderPage title="Mappings" />,
          },
          {
            path: 'users',
            element: <FeaturePlaceholderPage title="User management" />,
          },
          {
            path: 'settings',
            element: <FeaturePlaceholderPage title="Settings" />,
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
