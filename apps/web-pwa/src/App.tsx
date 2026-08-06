import { BrowserRouter } from "react-router-dom";
import { NoIndexOnAdmin } from "./components/NoIndexOnAdmin";
import { UpdateBanner } from "./components/UpdateBanner";
import { PWAInstallPrompt } from "./components/PWAInstallPrompt";
import { AppRouter } from "./routes";

export default function App() {
  return (
    <BrowserRouter>
      <NoIndexOnAdmin />
      <UpdateBanner />
      <AppRouter />
      <PWAInstallPrompt />
    </BrowserRouter>
  );
}
