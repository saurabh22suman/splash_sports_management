import { motion } from 'motion/react';

export default function SportsFacilities() {
  return (
    <div className="bg-charcoal-950 py-24 lg:py-32 border-t border-charcoal-800">
      
      {/* One Platform Section */}
      <section className="max-w-7xl mx-auto px-6 lg:px-8 mb-32">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-5xl md:text-6xl font-display font-bold leading-[0.9] mb-6">
            ONE PLATFORM.<br />
            <span className="text-volt">EVERY PART OF YOUR CLUB.</span>
          </h2>
          <p className="text-gray-400 font-medium max-w-xl mx-auto">
            From the front desk to the back courts, manage your entire facility blueprint through a single unified system.
          </p>
        </div>

        {/* Abstract Facility Map */}
        <div className="relative w-full max-w-4xl mx-auto aspect-video bg-charcoal-900 border border-charcoal-800 p-4 md:p-8 grid grid-cols-4 grid-rows-3 gap-2 md:gap-4">
          <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-10 mix-blend-overlay"></div>
          
          <motion.div whileHover={{ scale: 0.98 }} className="col-span-2 row-span-2 bg-charcoal-800 border border-charcoal-700 p-4 flex flex-col justify-between relative overflow-hidden group">
            <div className="absolute inset-0 bg-blue-500/10 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <div className="font-display text-sm md:text-xl uppercase tracking-widest text-gray-500">Swimming Pool</div>
            <div className="flex justify-between items-end">
              <span className="font-mono text-xs text-volt">Active Sessions: 3</span>
              <span className="font-display text-2xl text-white">42/50</span>
            </div>
          </motion.div>
          
          <motion.div whileHover={{ scale: 0.98 }} className="col-span-1 row-span-2 bg-charcoal-800 border border-charcoal-700 p-4 flex flex-col justify-between relative overflow-hidden group">
            <div className="absolute inset-0 bg-green-500/10 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <div className="font-display text-sm md:text-xl uppercase tracking-widest text-gray-500">Badminton<br/>Courts</div>
            <div className="font-mono text-xs text-white">100% BOOKED</div>
          </motion.div>

          <motion.div whileHover={{ scale: 0.98 }} className="col-span-1 row-span-1 bg-charcoal-800 border border-charcoal-700 p-4 flex flex-col justify-between">
            <div className="font-display text-sm md:text-xl uppercase tracking-widest text-gray-500">Reception</div>
          </motion.div>

          <motion.div whileHover={{ scale: 0.98 }} className="col-span-1 row-span-1 bg-charcoal-800 border border-charcoal-700 p-4 flex flex-col justify-between relative overflow-hidden group">
            <div className="absolute inset-0 bg-orange-500/10 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <div className="font-display text-sm md:text-xl uppercase tracking-widest text-gray-500">Cafe POS</div>
          </motion.div>

          <motion.div whileHover={{ scale: 0.98 }} className="col-span-4 row-span-1 bg-charcoal-800 border border-charcoal-700 p-4 flex items-center justify-between relative overflow-hidden group">
            <div className="absolute inset-0 bg-purple-500/10 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <div className="font-display text-sm md:text-xl uppercase tracking-widest text-gray-500">Gym & Academy Floor</div>
            <div className="font-display text-xl text-volt">124 MEMBERS PRESENT</div>
          </motion.div>
        </div>
      </section>

      {/* Sports First Section */}
      <section className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="mb-16">
          <h2 className="text-4xl md:text-5xl font-display font-bold leading-[0.9] mb-4">
            BUILT FOR SPORT.<br />
            <span className="text-gray-500">READY FOR WHATEVER COMES NEXT.</span>
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          
          {/* Swimming Card */}
          <div className="group relative h-[400px] border border-charcoal-700 overflow-hidden bg-charcoal-900">
            <div className="absolute inset-0 z-0">
              <img src="https://images.unsplash.com/photo-1519315901367-f34f91d5743b?auto=format&fit=crop&w=800&q=80" alt="Swimming Pool" className="w-full h-full object-cover filter contrast-125 saturate-50 opacity-40 group-hover:opacity-60 transition-opacity duration-500 group-hover:scale-105" />
              <div className="absolute inset-0 bg-gradient-to-t from-charcoal-950 via-charcoal-900/50 to-transparent"></div>
            </div>
            <div className="relative z-10 p-8 h-full flex flex-col justify-end">
              <h3 className="font-display text-4xl font-bold mb-4">SWIMMING</h3>
              <ul className="space-y-2 font-mono text-sm text-gray-300">
                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 bg-volt rounded-full"></span> Session Capacity</li>
                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 bg-volt rounded-full"></span> Batch Attendance</li>
                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 bg-volt rounded-full"></span> Coach Assignment</li>
              </ul>
            </div>
          </div>

          {/* Badminton Card */}
          <div className="group relative h-[400px] border border-charcoal-700 overflow-hidden bg-charcoal-900">
            <div className="absolute inset-0 z-0">
              <img src="https://images.unsplash.com/photo-1626224583764-f87db24ac4ea?auto=format&fit=crop&w=800&q=80" alt="Badminton" className="w-full h-full object-cover filter contrast-125 saturate-50 opacity-40 group-hover:opacity-60 transition-opacity duration-500 group-hover:scale-105" />
              <div className="absolute inset-0 bg-gradient-to-t from-charcoal-950 via-charcoal-900/50 to-transparent"></div>
            </div>
            <div className="relative z-10 p-8 h-full flex flex-col justify-end">
              <h3 className="font-display text-4xl font-bold mb-4">BADMINTON</h3>
              <ul className="space-y-2 font-mono text-sm text-gray-300">
                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 bg-volt rounded-full"></span> Court Availability</li>
                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 bg-volt rounded-full"></span> Peak Hour Pricing</li>
                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 bg-volt rounded-full"></span> Quick Bookings</li>
              </ul>
            </div>
          </div>

          {/* Gym Card */}
          <div className="group relative h-[400px] border border-charcoal-700 overflow-hidden bg-charcoal-900">
            <div className="absolute inset-0 z-0">
              <img src="https://images.unsplash.com/photo-1534438327276-14e5300c3a48?auto=format&fit=crop&w=800&q=80" alt="Gym" className="w-full h-full object-cover filter contrast-125 saturate-50 opacity-40 group-hover:opacity-60 transition-opacity duration-500 group-hover:scale-105" />
              <div className="absolute inset-0 bg-gradient-to-t from-charcoal-950 via-charcoal-900/50 to-transparent"></div>
            </div>
            <div className="relative z-10 p-8 h-full flex flex-col justify-end">
              <h3 className="font-display text-4xl font-bold mb-4">GYM & ACADEMY</h3>
              <ul className="space-y-2 font-mono text-sm text-gray-300">
                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 bg-volt rounded-full"></span> Active Memberships</li>
                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 bg-volt rounded-full"></span> QR Check-ins</li>
                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 bg-volt rounded-full"></span> Automated Renewals</li>
              </ul>
            </div>
          </div>

        </div>
      </section>
    </div>
  );
}
