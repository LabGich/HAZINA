import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import MainLayout from '../layouts/MainLayout/MainLayout'
import DashboardPage from '../pages/Dashboard/DashboardPage'
import FeaturePlaceholderPage from '../pages/FeaturePlaceholderPage'
import NotFoundPage from '../pages/NotFound/NotFoundPage'

const router = createBrowserRouter([
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
        element: <FeaturePlaceholderPage title="Pipeline runs" />,
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
      {
        path: '*',
        element: <NotFoundPage />,
      },
    ],
  },
])

function AppRouter() {
  return <RouterProvider router={router} />
}

export default AppRouter