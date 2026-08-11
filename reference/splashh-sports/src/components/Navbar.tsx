import { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import { Activity } from 'lucide-react';

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <motion.nav
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled 
          ? 'bg-charcoal-900/90 backdrop-blur-md border-b border-charcoal-800 py-4' 
          : 'bg-transparent py-6'
      }`}
    >
      <div className="max-w-7xl mx-auto px-6 lg:px-8 flex items-center justify-between">
        <div className="flex items-center gap-2 text-white">
          <Activity className="text-volt" size={28} />
          <span className="font-display text-2xl font-bold tracking-wider">SPLASHH</span>
        </div>
        
        <div className="hidden md:flex items-center gap-8 font-sans font-medium text-sm text-gray-300 uppercase tracking-wide">
          <a href="#platform" className="hover:text-white transition-colors">Platform</a>
          <a href="#sports" className="hover:text-white transition-colors">Sports</a>
          <a href="#features" className="hover:text-white transition-colors">Features</a>
          <a href="#pricing" className="hover:text-white transition-colors">Pricing</a>
        </div>
        
        <div className="flex items-center gap-4">
          <button className="hidden sm:block text-sm font-bold uppercase tracking-wide text-white hover:text-volt transition-colors">
            Login
          </button>
          <button className="bg-volt text-black text-sm font-bold uppercase tracking-wide px-6 py-2.5 hover:bg-volt-hover transition-colors">
            Book Demo
          </button>
        </div>
      </div>
    </motion.nav>
  );
}
