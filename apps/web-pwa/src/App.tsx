import { BrowserRouter } from "react-router-dom";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { NoIndexOnAdmin } from "./components/NoIndexOnAdmin";
import { OfflineBanner } from "./components/OfflineBanner";
import { PWAInstallPrompt } from "./components/PWAInstallPrompt";
import { UpdateBanner } from "./components/UpdateBanner";
import { AppRouter } from "./routes";

export default function App() {
  return (
    <BrowserRouter>
      <NoIndexOnAdmin />
      <UpdateBanner />
      <ErrorBoundary>
        <AppRouter />
      </ErrorBoundary>
      <PWAInstallPrompt />
      <OfflineBanner />
    </BrowserRouter>
  );
}
