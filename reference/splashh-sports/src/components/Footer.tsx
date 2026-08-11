import { Activity } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="bg-charcoal-950 pt-20 pb-10 border-t border-charcoal-800">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-12 mb-16">
          <div className="col-span-1 md:col-span-2">
            <div className="flex items-center gap-2 text-white mb-6">
              <Activity className="text-volt" size={28} />
              <span className="font-display text-3xl font-bold tracking-wider">SPLASHH</span>
            </div>
            <p className="text-gray-400 max-w-sm font-medium">
              The operating system for modern sports clubs. Designed for the way sports actually work.
            </p>
          </div>
          
          <div>
            <h4 className="font-display uppercase tracking-widest text-sm text-gray-300 mb-6">Product</h4>
            <ul className="space-y-4 text-gray-500 font-medium text-sm">
              <li><a href="#" className="hover:text-volt transition-colors">Platform</a></li>
              <li><a href="#" className="hover:text-volt transition-colors">Features</a></li>
              <li><a href="#" className="hover:text-volt transition-colors">Sports</a></li>
              <li><a href="#" className="hover:text-volt transition-colors">Pricing</a></li>
            </ul>
          </div>
          
          <div>
            <h4 className="font-display uppercase tracking-widest text-sm text-gray-300 mb-6">Company</h4>
            <ul className="space-y-4 text-gray-500 font-medium text-sm">
              <li><a href="#" className="hover:text-white transition-colors">About</a></li>
              <li><a href="#" className="hover:text-white transition-colors">Contact</a></li>
              <li><a href="#" className="hover:text-white transition-colors">Privacy Policy</a></li>
              <li><a href="#" className="hover:text-white transition-colors">Terms of Service</a></li>
            </ul>
          </div>
        </div>
        
        <div className="border-t border-charcoal-800 pt-8 flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-gray-600 text-sm font-mono">
            &copy; {new Date().getFullYear()} Splashh Sports. All rights reserved.
          </p>
          <div className="flex gap-4">
            <a href="#" className="w-8 h-8 rounded-full bg-charcoal-800 flex items-center justify-center text-gray-500 hover:text-white hover:bg-charcoal-700 transition-colors">
              <span className="font-bold font-display text-xs">X</span>
            </a>
            <a href="#" className="w-8 h-8 rounded-full bg-charcoal-800 flex items-center justify-center text-gray-500 hover:text-white hover:bg-charcoal-700 transition-colors">
              <span className="font-bold font-display text-xs">IN</span>
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
