import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { RequireAuth, useUser } from './context/UserContext';
import LoginPage from './pages/LoginPage';
import ExamListPage from './pages/ExamListPage';
import SubjectListPage from './pages/SubjectListPage';
import ChapterListPage from './pages/ChapterListPage';
import QuizPage from './pages/QuizPage';
import ResultPage from './pages/ResultPage';
import AnalyticsPage from './pages/AnalyticsPage';

function RootRedirect() {
  const { user } = useUser();
  return <Navigate to={user ? '/exams' : '/login'} replace />;
}

export default function App() {
  const location = useLocation();
  const isWide = location.pathname === '/analytics';

  return (
    <div className="app-backdrop">
      <div className={`phone-frame ${isWide ? 'phone-frame--wide' : ''}`}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          <Route
            path="/exams"
            element={
              <RequireAuth>
                <ExamListPage />
              </RequireAuth>
            }
          />
          <Route
            path="/exams/:examId/subjects"
            element={
              <RequireAuth>
                <SubjectListPage />
              </RequireAuth>
            }
          />
          <Route
            path="/subjects/:subjectId/chapters"
            element={
              <RequireAuth>
                <ChapterListPage />
              </RequireAuth>
            }
          />
          <Route
            path="/quiz/:attemptId"
            element={
              <RequireAuth>
                <QuizPage />
              </RequireAuth>
            }
          />
          <Route
            path="/quiz/:attemptId/result"
            element={
              <RequireAuth>
                <ResultPage />
              </RequireAuth>
            }
          />
          <Route
            path="/analytics"
            element={
              <RequireAuth>
                <AnalyticsPage />
              </RequireAuth>
            }
          />

          <Route path="/" element={<RootRedirect />} />
          <Route path="*" element={<RootRedirect />} />
        </Routes>
      </div>
    </div>
  );
}
