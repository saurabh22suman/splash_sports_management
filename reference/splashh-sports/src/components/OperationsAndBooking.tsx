import { motion } from 'motion/react';
import { ArrowRight, Calendar } from 'lucide-react';

export default function OperationsAndBooking() {
  const steps = [
    { label: "CUSTOMER", sub: "Discovers & Books" },
    { label: "RECEPTION", sub: "Quick Check-in" },
    { label: "COACH", sub: "Marks Attendance" },
    { label: "SYSTEM", sub: "Processes Payment" },
    { label: "OWNER", sub: "Views Insights" }
  ];

  return (
    <div className="bg-charcoal-900 border-t border-charcoal-800">
      
      {/* Operations Flow */}
      <section className="py-24 max-w-7xl mx-auto px-6 lg:px-8">
        <h2 className="text-4xl md:text-5xl font-display font-bold leading-[0.9] mb-16 text-center">
          FROM FRONT DESK TO<br />
          <span className="text-volt">OWNER'S DASHBOARD.</span>
        </h2>
        
        <div className="flex flex-col md:flex-row items-center justify-between gap-4 w-full relative">
          <div className="hidden md:block absolute top-1/2 left-0 w-full h-0.5 bg-gradient-to-r from-transparent via-charcoal-700 to-transparent -translate-y-1/2 z-0"></div>
          
          {steps.map((step, idx) => (
            <motion.div 
              key={idx}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.1 }}
              viewport={{ once: true }}
              className="relative z-10 flex flex-col items-center gap-4 w-full md:w-auto"
            >
              <div className="w-16 h-16 rounded-full bg-charcoal-800 border border-charcoal-700 flex items-center justify-center shadow-lg relative group hover:border-volt transition-colors cursor-default">
                <span className="font-display text-xl text-gray-400 group-hover:text-volt">{idx + 1}</span>
              </div>
              <div className="text-center">
                <div className="font-display tracking-widest text-white">{step.label}</div>
                <div className="font-mono text-xs text-gray-500">{step.sub}</div>
              </div>
              {idx < steps.length - 1 && (
                <div className="md:hidden text-charcoal-700 my-2">
                  <ArrowRight size={20} className="rotate-90" />
                </div>
              )}
            </motion.div>
          ))}
        </div>
      </section>

      {/* Booking Experience */}
      <section className="py-24 bg-charcoal-950 border-t border-charcoal-800">
        <div className="max-w-7xl mx-auto px-6 lg:px-8 grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          
          <div className="order-2 lg:order-1 relative flex justify-center">
            {/* Phone Mockup */}
            <div className="w-[300px] h-[600px] bg-black rounded-[40px] border-[8px] border-charcoal-800 p-4 relative shadow-2xl overflow-hidden">
              <div className="absolute top-0 inset-x-0 h-6 bg-black z-20 flex justify-center rounded-t-3xl">
                <div className="w-20 h-4 bg-charcoal-900 rounded-b-xl mt-1"></div>
              </div>
              
              <div className="pt-6 h-full flex flex-col">
                <div className="flex justify-between items-center mb-6">
                  <div className="font-display text-lg tracking-wider">BADMINTON</div>
                  <Calendar size={18} className="text-volt" />
                </div>
                
                <div className="flex gap-2 mb-6 overflow-x-auto hide-scrollbar">
                  {['Today', 'Tomorrow', 'Wed 12', 'Thu 13'].map((day, i) => (
                    <div key={i} className={`px-4 py-2 rounded-full whitespace-nowrap text-xs font-bold ${i === 0 ? 'bg-volt text-black' : 'bg-charcoal-800 text-white'}`}>
                      {day}
                    </div>
                  ))}
                </div>

                <div className="space-y-3 flex-1 overflow-y-auto hide-scrollbar pb-10">
                  <div className="bg-charcoal-800 p-4 rounded-xl flex justify-between items-center opacity-50">
                    <span className="font-mono text-sm">5:00 PM</span>
                    <span className="font-display text-xs text-red-400">FULL</span>
                  </div>
                  <div className="bg-charcoal-800 border border-volt p-4 rounded-xl flex justify-between items-center relative overflow-hidden cursor-pointer">
                    <div className="absolute inset-0 bg-volt/5"></div>
                    <span className="font-mono text-sm relative z-10 text-white">6:00 PM</span>
                    <span className="font-display text-xs text-volt relative z-10">AVAILABLE</span>
                  </div>
                  <div className="bg-charcoal-800 p-4 rounded-xl flex justify-between items-center cursor-pointer">
                    <span className="font-mono text-sm text-gray-300">7:00 PM</span>
                    <span className="font-display text-xs text-green-400">AVAILABLE</span>
                  </div>
                  <div className="bg-charcoal-800 p-4 rounded-xl flex justify-between items-center cursor-pointer">
                    <span className="font-mono text-sm text-gray-300">8:00 PM</span>
                    <span className="font-display text-xs text-orange-400">2 SLOTS LEFT</span>
                  </div>
                </div>
                
                <button className="w-full bg-volt text-black font-bold uppercase tracking-wider py-4 rounded-xl mt-auto hover:bg-volt-hover transition-colors">
                  Confirm Booking
                </button>
              </div>
            </div>
          </div>

          <div className="order-1 lg:order-2">
            <h2 className="text-4xl md:text-6xl font-display font-bold leading-[0.9] mb-6">
              YOUR COURT.<br />
              <span className="text-gray-500">YOUR TIME.</span><br />
              <span className="text-volt">ONE TAP.</span>
            </h2>
            <p className="text-gray-400 font-medium max-w-md">
              A frictionless booking experience designed to keep your courts full and your customers happy. No calls, no waiting.
            </p>
          </div>
          
        </div>
      </section>

    </div>
  );
}
