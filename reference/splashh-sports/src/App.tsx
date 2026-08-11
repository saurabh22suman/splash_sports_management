import Navbar from './components/Navbar';
import Hero from './components/Hero';
import TrustAndProblem from './components/TrustAndProblem';
import SportsFacilities from './components/SportsFacilities';
import OperationsAndBooking from './components/OperationsAndBooking';
import MembershipsAndDashboard from './components/MembershipsAndDashboard';
import AIAndCustomer from './components/AIAndCustomer';
import AnalyticsAndCTA from './components/AnalyticsAndCTA';
import Footer from './components/Footer';

export default function App() {
  return (
    <div className="min-h-screen bg-charcoal-900 text-white font-sans selection:bg-volt selection:text-black">
      <Navbar />
      <Hero />
      <TrustAndProblem />
      <SportsFacilities />
      <OperationsAndBooking />
      <MembershipsAndDashboard />
      <AIAndCustomer />
      <AnalyticsAndCTA />
      <Footer />
    </div>
  );
}
