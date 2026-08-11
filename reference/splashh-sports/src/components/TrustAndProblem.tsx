import { motion } from 'motion/react';
import { FileText, Phone, MessageSquare, IndianRupee, PieChart, Users, CheckCircle, Activity } from 'lucide-react';

export default function TrustAndProblem() {
  const sports = [
    { name: "Swimming", icon: "🏊" },
    { name: "Badminton", icon: "🏸" },
    { name: "Tennis", icon: "🎾" },
    { name: "Gym", icon: "🏋️" },
    { name: "Football", icon: "⚽" },
    { name: "Cricket", icon: "🏏" }
  ];

  return (
    <div className="bg-charcoal-900 border-t border-charcoal-800">
      {/* Trust Section */}
      <section className="py-12 border-b border-charcoal-800">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <p className="text-center text-xs font-bold tracking-widest text-gray-500 uppercase mb-8">
            Built for the way sports clubs actually work
          </p>
          <div className="flex flex-wrap justify-center gap-4 md:gap-8">
            {sports.map((sport, idx) => (
              <div key={idx} className="flex items-center gap-2 px-4 py-2 bg-charcoal-800/50 border border-charcoal-700/50 grayscale opacity-70 hover:grayscale-0 hover:opacity-100 transition-all duration-300">
                <span className="text-xl">{sport.icon}</span>
                <span className="font-display uppercase text-sm tracking-wide text-gray-300">{sport.name}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Problem Section */}
      <section className="py-24 lg:py-32">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-20">
            <h2 className="text-5xl md:text-6xl font-display font-bold leading-[0.9] mb-6">
              YOUR CLUB IS BUSY.<br />
              <span className="text-gray-500">YOUR SOFTWARE SHOULDN'T BE.</span>
            </h2>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 lg:gap-24 items-center">
            {/* Chaos Visual */}
            <div className="relative h-[400px] w-full flex items-center justify-center">
              <div className="absolute inset-0 bg-red-950/10 blur-3xl rounded-full"></div>
              
              <motion.div initial={{ rotate: -5, x: -20 }} whileInView={{ rotate: -2, x: 0 }} className="absolute z-10 bg-charcoal-800 border border-red-900/30 p-4 shadow-xl flex items-center gap-3 top-20 left-10 opacity-70">
                <MessageSquare className="text-green-500" />
                <span className="font-mono text-xs text-gray-300">"Is court 2 free at 7?"</span>
              </motion.div>
              
              <motion.div initial={{ rotate: 8, x: 20 }} whileInView={{ rotate: 5, x: 0 }} className="absolute z-20 bg-white border border-gray-200 p-4 shadow-xl flex items-center gap-3 top-10 right-10 opacity-80 text-black">
                <FileText className="text-green-700" />
                <span className="font-mono text-xs">book_final_v3.xlsx</span>
              </motion.div>

              <motion.div initial={{ rotate: -15, y: 30 }} whileInView={{ rotate: -10, y: 0 }} className="absolute z-30 bg-charcoal-800 border border-charcoal-700 p-4 shadow-xl flex items-center gap-3 bottom-24 left-4">
                <Phone className="text-blue-400" />
                <span className="font-mono text-xs text-gray-300">Missed Call (3)</span>
              </motion.div>

              <motion.div initial={{ rotate: 10, y: 40 }} whileInView={{ rotate: 12, y: 0 }} className="absolute z-40 bg-charcoal-800 border border-charcoal-700 p-4 shadow-xl flex items-center gap-3 bottom-16 right-4 opacity-90">
                <IndianRupee className="text-yellow-500" />
                <span className="font-mono text-xs text-gray-300">Screenshot_Payment.jpg</span>
              </motion.div>

              <div className="z-50 font-display text-4xl text-gray-500 text-center uppercase tracking-widest bg-charcoal-900/80 backdrop-blur-sm p-4 border border-charcoal-800">
                The Old Way
              </div>
            </div>

            {/* Solution Visual */}
            <div className="relative h-[400px] w-full flex items-center justify-center">
              <div className="absolute inset-0 bg-volt/5 blur-3xl rounded-full"></div>
              
              <div className="grid grid-cols-2 gap-4 w-full max-w-md relative z-10">
                <div className="col-span-2 text-center mb-4">
                  <h3 className="font-display text-3xl text-volt uppercase tracking-wider mb-2">Splashh Brings It Together</h3>
                  <div className="h-px bg-gradient-to-r from-transparent via-volt/50 to-transparent w-full"></div>
                </div>

                {[
                  { icon: Users, label: "Members" },
                  { icon: CheckCircle, label: "Bookings" },
                  { icon: IndianRupee, label: "Payments" },
                  { icon: Activity, label: "Attendance" },
                  { icon: FileText, label: "Memberships" },
                  { icon: PieChart, label: "Analytics" },
                ].map((item, idx) => (
                  <motion.div 
                    key={idx}
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.1 }}
                    className="bg-charcoal-800 border border-charcoal-700 p-4 flex flex-col items-center justify-center gap-2 hover:border-volt/50 transition-colors"
                  >
                    <item.icon className="text-volt mb-1" size={20} />
                    <span className="font-display text-sm tracking-wider uppercase text-gray-300">{item.label}</span>
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
