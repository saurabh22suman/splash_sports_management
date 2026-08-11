import { Sparkles } from 'lucide-react';

export default function AIAndCustomer() {
  return (
    <div className="bg-charcoal-900 border-t border-charcoal-800">
      
      {/* AI Section */}
      <section className="py-24 max-w-7xl mx-auto px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl font-display font-bold leading-[0.9] mb-4">
            YOUR CLUB IS FULL OF DATA.<br />
            <span className="text-gray-500">NOW MAKE IT WORK FOR YOU.</span>
          </h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          <div className="bg-charcoal-800 border border-charcoal-700 p-6 rounded-lg relative overflow-hidden group hover:border-volt/50 transition-colors">
            <div className="absolute top-0 right-0 p-4">
              <Sparkles className="text-volt" size={20} />
            </div>
            <div className="text-xs font-bold tracking-widest text-gray-500 uppercase mb-4">AI Insight</div>
            <p className="font-mono text-sm text-gray-300 leading-relaxed">
              Saturday 6–8 PM is consistently over <span className="text-volt font-bold">90% occupied</span>.<br /><br />
              Consider adding another badminton court session or adjusting peak pricing.
            </p>
          </div>
          
          <div className="bg-charcoal-800 border border-charcoal-700 p-6 rounded-lg relative overflow-hidden group hover:border-volt/50 transition-colors">
            <div className="absolute top-0 right-0 p-4">
              <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></div>
            </div>
            <div className="text-xs font-bold tracking-widest text-gray-500 uppercase mb-4">Renewal Alert</div>
            <p className="font-mono text-sm text-gray-300 leading-relaxed">
              <span className="text-white font-bold">18 members</span> are showing reduced attendance this month and may be at risk of not renewing.<br /><br />
              <button className="text-volt underline decoration-volt/50 underline-offset-4 mt-2 hover:decoration-volt transition-colors cursor-pointer">Trigger automated re-engagement campaign</button>
            </p>
          </div>
        </div>
      </section>

      {/* Customer Experience */}
      <section className="py-24 bg-volt text-black overflow-hidden">
        <div className="max-w-7xl mx-auto px-6 lg:px-8 grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          <div>
            <h2 className="text-5xl md:text-6xl font-display font-bold leading-[0.9] mb-6">
              YOUR CLUB.<br />
              EVERYWHERE.
            </h2>
            <p className="font-medium text-black/70 mb-8 max-w-md">
              A premium, installable PWA for your customers. They can book, pay, check-in via QR, and manage memberships right from their phones.
            </p>
            
            <div className="space-y-4">
              {['Installable App (PWA)', 'QR Code Check-in', 'Instant Bookings', 'Digital ID'].map((feature, i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className="w-1.5 h-1.5 bg-black rounded-full"></div>
                  <span className="font-display uppercase tracking-wider font-bold">{feature}</span>
                </div>
              ))}
            </div>
          </div>
          
          <div className="flex justify-center relative">
            <div className="w-[280px] h-[580px] bg-white rounded-[32px] border-[6px] border-black p-4 relative shadow-2xl -rotate-3 transform hover:rotate-0 transition-transform duration-500">
              <div className="flex justify-between items-center mb-6">
                <span className="font-display font-bold text-lg">SPLASHH</span>
                <div className="w-8 h-8 rounded-full bg-gray-200"></div>
              </div>
              
              <div className="bg-black text-white p-4 rounded-xl mb-6">
                <div className="text-[10px] uppercase tracking-widest text-gray-400 mb-1">Digital Pass</div>
                <div className="font-display text-xl mb-4 text-volt">PRO MEMBERSHIP</div>
                <div className="w-full h-24 bg-white rounded-lg flex items-center justify-center relative overflow-hidden">
                  <div className="absolute inset-0 flex items-center justify-center opacity-20">
                    <div className="w-16 h-16 border-4 border-black border-dashed"></div>
                  </div>
                  <span className="font-mono text-black font-bold relative z-10 text-xs tracking-[0.2em]">SCAN TO ENTER</span>
                </div>
              </div>
              
              <div className="space-y-3">
                <div className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-2">Upcoming</div>
                <div className="bg-gray-100 p-4 rounded-xl flex justify-between items-center border border-gray-200">
                  <div>
                    <div className="font-bold text-sm">Badminton Court 2</div>
                    <div className="text-xs text-gray-500">Today, 7:00 PM</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

    </div>
  );
}
