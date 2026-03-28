import { Navigate, Route, Routes } from "react-router-dom";

import { ProblemListPage } from "./pages/ProblemListPage";
import { ProblemWorkspacePage } from "./pages/ProblemWorkspacePage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<ProblemListPage />} />
      <Route path="/problems/:slug" element={<ProblemWorkspacePage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
