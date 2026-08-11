import { motion } from 'motion/react';
import { Activity, Clock } from 'lucide-react';

export default function Hero() {
  return (
    <section className="relative min-h-screen flex items-center pt-32 pb-16 overflow-hidden bg-charcoal-900">
      {/* Background elements */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-charcoal-800 via-charcoal-900 to-charcoal-950 -z-20"></div>
      
      <div className="max-w-7xl mx-auto px-6 lg:px-8 w-full grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
        {/* Left Content */}
        <motion.div 
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="z-10"
        >
          <div className="inline-flex items-center space-x-2 bg-charcoal-800 border border-charcoal-700 px-3 py-1.5 rounded-sm mb-8">
            <div className="w-2 h-2 rounded-full bg-volt animate-pulse"></div>
            <span className="text-xs font-bold tracking-wider text-gray-300 uppercase">Sports Club Management Platform</span>
          </div>
          
          <h1 className="text-6xl md:text-7xl lg:text-8xl font-display font-bold leading-[0.85] mb-8">
            RUN YOUR CLUB.<br />
            <span className="text-gray-500">NOT YOUR</span><br />
            <span className="text-volt">SPREADSHEET.</span>
          </h1>
          
          <p className="text-lg md:text-xl text-gray-400 mb-10 max-w-xl font-medium">
            Manage bookings, memberships, payments, attendance, and operations from one powerful platform built specifically for sports clubs.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4">
            <button className="bg-volt text-black font-bold uppercase tracking-wider px-8 py-4 text-sm md:text-base hover:bg-volt-hover transition-colors shadow-[0_0_20px_rgba(204,255,0,0.3)]">
              Book a Demo
            </button>
            <button className="bg-transparent text-white font-bold uppercase tracking-wider px-8 py-4 text-sm md:text-base border-2 border-charcoal-600 hover:border-gray-300 transition-colors">
              Explore Platform
            </button>
          </div>
        </motion.div>

        {/* Right Visual */}
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1, delay: 0.2, ease: "easeOut" }}
          className="relative w-full aspect-square md:aspect-[4/3] lg:aspect-square"
        >
          {/* Main Image */}
          <div className="absolute inset-0 overflow-hidden border border-charcoal-700">
            <div className="absolute inset-0 bg-charcoal-900/30 z-10 mix-blend-multiply"></div>
            <img 
              src="https://images.unsplash.com/photo-1626224583764-f87db24ac4ea?auto=format&fit=crop&w=1200&q=80" 
              alt="Badminton Player in action" 
              className="w-full h-full object-cover filter contrast-125 saturate-50"
            />
          </div>

          {/* Floating UI Elements */}
          <motion.div 
            animate={{ y: [0, -12, 0] }}
            transition={{ repeat: Infinity, duration: 5, ease: "easeInOut" }}
            className="absolute top-12 -left-4 md:-left-12 z-20 bg-charcoal-900/90 backdrop-blur-md border border-charcoal-700 p-4 shadow-2xl flex items-center gap-4"
          >
            <div className="w-12 h-12 bg-charcoal-800 flex items-center justify-center text-volt">
              <Activity size={24} />
            </div>
            <div>
              <div className="text-[10px] text-gray-400 font-bold uppercase tracking-widest">Court 02</div>
              <div className="font-display text-2xl text-white leading-none mt-1">87% OCCUPANCY</div>
            </div>
          </motion.div>

          <motion.div 
            animate={{ y: [0, 10, 0] }}
            transition={{ repeat: Infinity, duration: 6, ease: "easeInOut", delay: 1 }}
            className="absolute bottom-24 -right-4 md:-right-8 z-20 bg-white/95 backdrop-blur-md text-black p-4 shadow-2xl flex items-center gap-4"
          >
            <div className="w-12 h-12 bg-black flex items-center justify-center text-white">
              <Clock size={24} />
            </div>
            <div>
              <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">7:00 PM Slot</div>
              <div className="font-display text-2xl text-black leading-none mt-1">BOOKED</div>
            </div>
          </motion.div>
          
          <motion.div 
            animate={{ y: [0, -8, 0] }}
            transition={{ repeat: Infinity, duration: 4.5, ease: "easeInOut", delay: 0.5 }}
            className="absolute top-1/2 -translate-y-1/2 right-4 md:-right-4 z-20 bg-volt/95 backdrop-blur-md text-black p-4 shadow-2xl flex flex-col gap-1 border border-volt"
          >
            <div className="text-[10px] font-bold uppercase tracking-widest opacity-80">Revenue Today</div>
            <div className="font-display text-3xl leading-none">₹42,500</div>
          </motion.div>

        </motion.div>
      </div>
    </section>
  );
}
