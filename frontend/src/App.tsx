import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import Cp1WorkbenchPage from './pages/Cp1WorkbenchPage';

function WorkbenchRoute() {
  const location = useLocation();
  const segment = location.pathname.split('/').filter(Boolean)[1];
  return <Cp1WorkbenchPage tab={segment || 'home'} />;
}

export default function App() {
  return <BrowserRouter>
    <Routes>
      <Route path="/" element={<Navigate to="/vaultguard/home" replace />} />
      <Route path="/vaultguard/:tab" element={<WorkbenchRoute />} />
      <Route path="/cp1/:tab" element={<WorkbenchRoute />} />
      <Route path="*" element={<Navigate to="/vaultguard/home" replace />} />
    </Routes>
  </BrowserRouter>;
}
