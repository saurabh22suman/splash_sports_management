export default function AnalyticsAndCTA() {
  return (
    <div className="bg-charcoal-900 border-t border-charcoal-800">
      
      {/* Analytics Section */}
      <section className="py-24 max-w-7xl mx-auto px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-5xl md:text-6xl font-display font-bold leading-[0.9] mb-4">
            KNOW YOUR CLUB.<br />
            <span className="text-gray-500">GROW YOUR CLUB.</span>
          </h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          <div className="bg-charcoal-800 border border-charcoal-700 p-8 flex flex-col items-center justify-center text-center aspect-square md:aspect-auto md:h-64 rounded-full md:rounded-lg">
            <div className="font-display text-6xl text-volt mb-2">32%</div>
            <div className="text-sm font-bold tracking-widest text-gray-400 uppercase">Growth in Peak Revenue</div>
          </div>
          <div className="bg-charcoal-800 border border-charcoal-700 p-8 flex flex-col items-center justify-center text-center aspect-square md:aspect-auto md:h-64 rounded-full md:rounded-lg">
            <div className="font-display text-6xl text-white mb-2">14h</div>
            <div className="text-sm font-bold tracking-widest text-gray-400 uppercase">Admin Time Saved Weekly</div>
          </div>
          <div className="bg-charcoal-800 border border-charcoal-700 p-8 flex flex-col items-center justify-center text-center aspect-square md:aspect-auto md:h-64 rounded-full md:rounded-lg">
            <div className="font-display text-6xl text-volt mb-2">94%</div>
            <div className="text-sm font-bold tracking-widest text-gray-400 uppercase">Court Utilization Rate</div>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-32 relative overflow-hidden bg-charcoal-950 border-t border-charcoal-800">
        <div className="absolute inset-0 z-0">
          <img src="https://images.unsplash.com/photo-1595435934249-5df7ed86e1c0?auto=format&fit=crop&w=1600&q=80" alt="Tennis Court Background" className="w-full h-full object-cover filter contrast-125 saturate-0 opacity-20" />
          <div className="absolute inset-0 bg-gradient-to-t from-charcoal-950 via-charcoal-950/80 to-transparent"></div>
        </div>
        
        <div className="relative z-10 max-w-4xl mx-auto px-6 lg:px-8 text-center">
          <h2 className="text-5xl md:text-7xl font-display font-bold leading-[0.9] mb-8">
            READY TO RUN A<br />
            <span className="text-volt">BETTER CLUB?</span>
          </h2>
          <p className="text-xl text-gray-400 mb-12 font-medium max-w-2xl mx-auto">
            Bring bookings, memberships, payments and operations into one platform built specifically for sports.
          </p>
          
          <div className="flex flex-col sm:flex-row justify-center gap-4">
            <button className="bg-volt text-black font-bold uppercase tracking-wider px-10 py-5 text-lg hover:bg-volt-hover transition-colors shadow-[0_0_30px_rgba(204,255,0,0.2)]">
              Book a Demo
            </button>
            <button className="bg-transparent text-white font-bold uppercase tracking-wider px-10 py-5 text-lg border-2 border-charcoal-600 hover:border-gray-400 transition-colors bg-charcoal-900/50 backdrop-blur-sm">
              Talk to Us
            </button>
          </div>
        </div>
      </section>
      
    </div>
  );
}
