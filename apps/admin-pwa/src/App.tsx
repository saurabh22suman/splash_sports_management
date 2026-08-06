import { BrowserRouter } from "react-router-dom";
import { UpdateBanner } from "./components/UpdateBanner";
import { PWAInstallPrompt } from "./components/PWAInstallPrompt";
import { AppRouter } from "./routes";

export default function App() {
  return (
    <BrowserRouter>
      <UpdateBanner />
      <AppRouter />
      <PWAInstallPrompt />
    </BrowserRouter>
  );
}
