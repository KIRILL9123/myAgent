import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import MemoryPage from './pages/MemoryPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/memory" element={<MemoryPage />} />
        <Route path="*" element={<Navigate to="/memory" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
